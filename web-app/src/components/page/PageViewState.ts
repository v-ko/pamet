import { ObservableMap, ObservableSet, computed, makeObservable, observable, toJS } from 'mobx';
import { ARROW_ANCHOR_ON_NOTE_SUGGEST_RADIUS, ARROW_SELECTION_RADIUS, DEFAULT_EYE_HEIGHT, RESIZE_CIRCLE_RADIUS } from "@/core/constants";
import { Point2D } from 'fusion/primitives/Point2D';
import { Page, PageData } from "@/model/Page";
import { Viewport } from "@/components/page/Viewport";
import { Rectangle, RectangleData } from 'fusion/primitives/Rectangle';
import { NoteViewState } from "@/components/note/NoteViewState";
import { ArrowViewState } from "@/components/arrow/ArrowViewState";
import { pamet } from "@/core/facade";
import { getLogger } from 'fusion/logging';
import { Note } from "@/model/Note";
import { anchorIntersectsCircle, Arrow, arrowAnchorPosition, ArrowAnchorOnNoteType } from "@/model/Arrow";
import { ElementViewState as CanvasElementViewState } from "@/components/page/ElementViewState";
import { Size } from 'fusion/primitives/Size';
import { CanvasPageRenderer } from "@/components/page/DirectRenderer";
import { Change } from 'fusion/model/Change';
import React from 'react';
import { NoteEditViewState } from "@/components/note/NoteEditViewState";
import { mediaItemRoute } from '@/services/routing/route';
import { MediaItem } from 'fusion/model/MediaItem';

let log = getLogger('PageViewState');

export interface ViewportAutoNavAnimation {
    startCenter: Point2D;
    endCenter: Point2D;
    startHeight: number;
    endHeight: number;
    startTime: number;
    duration: number;
    lastUpdateTime?: number;
    timingFunctionName: string;
}


// Mode enumeration
export enum PageMode {
    None,
    DragNavigation,
    DragSelection,
    NoteResize,
    MoveElements,
    CreateArrow,
    ArrowControlPointDrag,
    AutoNavigation,
    DraggingEditWindow
}


export class PageViewState {
    _pageData!: PageData;
    _renderer: CanvasPageRenderer;

    // Elements
    noteViewStatesById: ObservableMap<string, NoteViewState>;
    arrowViewStatesById: ObservableMap<string, ArrowViewState>;

    // Viewport
    viewportCenter: Point2D = new Point2D([0, 0]);
    viewportHeight: number = DEFAULT_EYE_HEIGHT;
    viewportGeometry: [number, number, number, number] = [0, 0, 0, 0];

    // Common
    mode: PageMode = PageMode.None;
    viewportCenterOnModeStart: Point2D = new Point2D([0, 0]); // In real coords
    projectedMousePosition: Point2D | null = null;  // If null - not on screen
    // mouseButtons: number = 0;

    // Selection related
    selectedElementsVS: ObservableSet<CanvasElementViewState> = observable.set();
    mousePositionOnDragSelectionStart: Point2D | null = null;
    dragSelectionRectData: RectangleData | null = null;
    dragSelectedElementsVS: ObservableSet<CanvasElementViewState> = observable.set();

    // Auto navigation (out of order. Check if it's salvageable)
    autoNavAnimation: ViewportAutoNavAnimation | null = null;

    // Edit window
    noteEditWindowState: NoteEditViewState | null = null;

    // Note resize related
    noteResizeClickRealPos: Point2D = new Point2D([0, 0]);
    noteResizeInitialSize: Size = new Size([0, 0]);
    noteResizeCircleClickOffset: Point2D = new Point2D([0, 0]);
    notesBeingResized: NoteViewState[] = [];

    // Element move related
    realMousePosOnElementMoveStart: Point2D = new Point2D([0, 0]);
    movedNoteVSs: NoteViewState[] = [];  // Be explicit about it.
    movedArrowVSs: ArrowViewState[] = []; // Also marker for restoring state on abort

    // Arrow related
    // Creation
    newArrowViewState: ArrowViewState | null = null;
    // Editing
    draggedControlPointIndex: number | null = null;

    // Media items
    mediaUrlsByItemId: ObservableMap<string, string> = observable.map();

    constructor(page: Page, notes: Note[], arrows: Arrow[]) {
        this._pageData = page.data();
        this._renderer = new CanvasPageRenderer();

        this.noteViewStatesById = new ObservableMap<string, NoteViewState>();
        this.arrowViewStatesById = new ObservableMap<string, ArrowViewState>();

        // Create element view states
        for (let note of notes) {
            this.addViewStateForElement(note);

            if (note.content.image_id) {
                let mediaItem = pamet.mediaItem(note.content.image_id);
                if (!mediaItem) {
                    log.error('Media item not found for note', note.id);
                    continue;
                }
                this.addUrlForMediaItem(mediaItem);
            }
        }
        for (let arrow of arrows) {
            this.addViewStateForElement(arrow);
        }

        makeObservable(this, {
            _pageData: observable,
            // page: computed, This returns instances with the same data object (and entities arer expected to be generally immutable )

            noteViewStatesById: observable,
            arrowViewStatesById: observable,

            viewportCenter: observable,
            viewportHeight: observable,
            viewportGeometry: observable,

            mode: observable,
            viewportCenterOnModeStart: observable,
            projectedMousePosition: observable,

            selectedElementsVS: observable,
            mousePositionOnDragSelectionStart: observable,
            dragSelectionRectData: observable,
            dragSelectedElementsVS: observable,
            autoNavAnimation: observable,

            noteEditWindowState: observable,

            viewport: computed
        });
    }

    updateFromChange(change: Change) {
        if (!change.isUpdate()) {
            throw new Error('Page view state can only be updated from an update type change');
        }
        let update = change.forwardComponent as Partial<PageData>;
        this._pageData = { ...this._pageData, ...update };
    }

    get renderer() {
        return this._renderer;
    }

    _addViewStateForNote(element: Note) {
        if (this.noteViewStatesById.has(element.id)) {
            log.error('Note already exists in page view state', element)
            return;
        }
        let nvs = new NoteViewState(element);
        this.noteViewStatesById.set(element.id, nvs);
    }

    _addViewStateForArrow(element: Arrow) {
        if (this.arrowViewStatesById.has(element.id)) {
            log.error('Arrow already exists in page view state', element)
            return;
        }

        this.arrowViewStatesById.set(element.id, new ArrowViewState(element));
    }

    addViewStateForElement(element: Note | Arrow) {
        if (element instanceof Note) {
            try {
                this._addViewStateForNote(element);
            } catch (e) {
                log.error('Error adding note view state for note', element, e)
            }
        } else if (element instanceof Arrow) {
            try {
                this._addViewStateForArrow(element);
            } catch (e) {
                log.error('Error adding arrow view state for arrow', element, e)
            }
        }
    }

    removeViewStateForElement(element: Note | Arrow) {
        if (element instanceof Note) {
            this.noteViewStatesById.delete(element.id);
        } else if (element instanceof Arrow) {
            this.arrowViewStatesById.delete(element.id);
        }
    }

    addUrlForMediaItem(mediaItem: MediaItem) {
        /* Adds a media item URL to the page view state.
         * If the media item already exists, it will be overwritten.
         */
        const userId = pamet.appViewState.userId;
        const pametProjectId = pamet.appViewState.currentProjectId;
        if (!userId || !pametProjectId) {
            log.error('Cannot add media item URL without userId or projectId');
            return;
        }
        const mediaRoute = mediaItemRoute(mediaItem, userId, pametProjectId);
        this.mediaUrlsByItemId.set(mediaItem.id, mediaRoute.toRelativeReference());
    }

    noteVS_anchorsForArrow(arrow: Arrow) {
        /* Get the NoteViewStates for the arrow's head and tail notes */
        let headNVS: NoteViewState | null = null;
        if (arrow.headNoteId) {
            headNVS = this.noteViewStatesById.get(arrow.headNoteId) || null
            if (!headNVS) {
                throw Error('Head note not found ' + arrow.headNoteId)
            }
        }

        let tailNVS: NoteViewState | null = null;
        if (arrow.tailNoteId) {
            tailNVS = this.noteViewStatesById.get(arrow.tailNoteId) || null
            if (!tailNVS) {
                throw Error('Tail note not found ' + arrow.tailNoteId)
            }
        }

        return { headNVS, tailNVS }
    }

    getViewStateForElement(elementId: string): NoteViewState | ArrowViewState | null {
        return this.noteViewStatesById.get(elementId) || this.arrowViewStatesById.get(elementId) || null;
    }
    viewStateForElementId(id: string): NoteViewState | ArrowViewState | null {
        try {
            return this.getViewStateForElement(id);
        } catch {
            return null;
        }
    }

    page() {
        let pageData = toJS(this._pageData);
        return new Page(pageData)
    }

    clearMode() {
        log.info('Clearing page mode')

        // Drag select related
        this.mousePositionOnDragSelectionStart = null;
        this.dragSelectionRectData = null;
        this.dragSelectedElementsVS.clear();

        // Edit window related
        let editWS = this.noteEditWindowState!;
        if (editWS !== null) {
            editWS.isBeingDragged = false;
        }

        // Note resize related
        // If note resize was aborted (notesBeingResized is not empty) - restore
        // the geometries from the entities
        if (this.notesBeingResized.length > 0) {
            for (let noteVS of this.notesBeingResized) {
                let note = pamet.note(noteVS.note().id);
                if (note === undefined) {
                    log.error('Note not found for note view state being resized', noteVS.note().id)
                    continue;
                }
                noteVS.updateFromNote(note);
            }
        }
        this.notesBeingResized = [];

        // Element move related
        // If element move was aborted - restore the geometries from the entities
        if (this.movedNoteVSs.length > 0) {
            for (let noteVS of this.movedNoteVSs) {
                let note = pamet.findOne({ id: noteVS.note().id });
                if (!(note instanceof Note)) {
                    log.error('Note not found for note view state being moved', noteVS.note().id)
                    continue;
                }
                noteVS.updateFromNote(note);
            }
            for (let arrowVS of this.movedArrowVSs) {
                let arrow = pamet.findOne({ id: arrowVS.arrow().id });
                if (!(arrow instanceof Arrow)) {
                    log.error('Arrow not found for arrow view state being moved', arrowVS.arrow().id)
                    continue;
                }
                arrowVS.updateFromArrow(arrow);
            }
        }

        // Arrow editing related
        if (this.newArrowViewState !== null) {
            this.newArrowViewState = null;
        }
        // If arrow control point was being dragged - restore the arrow view state
        // Since we make direct changes to it in the drag mode
        if (this.mode === PageMode.ArrowControlPointDrag) {
            let editedArrowVS = this.arrowVS_withVisibleControlPoints();
            if (editedArrowVS === null) {
                log.error('Arrow control point drag mode but no arrow view state with control points visible')
                return;
            }
            let arrow = pamet.findOne({ id: editedArrowVS!.arrow().id });
            if (!(arrow instanceof Arrow)) {
                log.error('Arrow not found for cp-dragged arrow with id', editedArrowVS.arrow().id)
                return;
            }
            editedArrowVS.updateFromArrow(arrow);
        }

        this.mode = PageMode.None;
    }

    setMode(mode: PageMode) {
        if (this.mode !== PageMode.None) {
            this.clearMode();
        }
        if (mode === this.mode) {
            return;
        }
        log.info('Setting page mode', mode, 'from ', this.mode)
        this.mode = mode;
    }

    get viewport() {
        let viewport = Viewport.fromProjectedGeometry(this.viewportGeometry, this.viewportHeight);
        viewport.setDevicePixelRatio(window.devicePixelRatio) // was not used
        viewport.moveRealCenterTo(this.viewportCenter);
        return viewport;
    }

    *noteViewsAt(position: Point2D, radius: number = 0): Generator<NoteViewState> {
        for (let noteViewState of this.noteViewStatesById.values()) {
            let intersectRect = new Rectangle([...noteViewState._noteData.geometry])
            if (radius > 0) {
                intersectRect.setSize(intersectRect.size().add(new Size([radius * 2, radius * 2])))
                intersectRect.setTopLeft(intersectRect.topLeft().subtract(new Point2D([radius, radius])))
            }
            if (intersectRect.contains(position)) {
                yield noteViewState;
            }
        }
    }
    noteViewStateAt(position: Point2D): NoteViewState | null {
        for (let noteViewState of this.noteViewsAt(position)) {
            return noteViewState;
        }
        return null;
    }

    *arrowsViewsAt(position: Point2D): Generator<ArrowViewState> {
        for (let arrowVS of this.arrowViewStatesById.values()) {
            if (arrowVS.intersectsCircle(position, ARROW_SELECTION_RADIUS)) {
                yield arrowVS;
            }
        }
    }

    arrowViewStateAt(position: Point2D): ArrowViewState | null {
        for (let arrowViewState of this.arrowsViewsAt(position)) {
            return arrowViewState;
        }
        return null;
    }

    noteAnchorSuggestionAt(realPosition: Point2D): AnchorOnNoteSuggestion {
        /* Returns the closest anchor suggestion for the given position
        * If the hit is on an anchor - returns the params of the anchor
        * If the hit is on a note - returns the noteViewState and sets the
        * anchor position to the mouse position. The anchor tppe is set to auto.
        * If there is no hit - anchorType is set to none, anchor position
        * is set to the mouse position and noteViewState is null.
        */

        let closestAnchorType: ArrowAnchorOnNoteType = ArrowAnchorOnNoteType.none;
        let closestNoteVS: NoteViewState | null = null;
        let closestAnchorPosition: Point2D = realPosition

        // Check note view states under the mouse (with margin for anchor)
        let closestDistance = Number.MAX_VALUE;
        for (let noteVS of this.noteViewsAt(realPosition, ARROW_ANCHOR_ON_NOTE_SUGGEST_RADIUS)) {
            let note = noteVS.note();

            // Check if the click is on a note anchor
            let anchorUnderMouse = anchorIntersectsCircle(note, realPosition, ARROW_ANCHOR_ON_NOTE_SUGGEST_RADIUS);
            if (anchorUnderMouse !== ArrowAnchorOnNoteType.none) {
                // Click is on a note anchor
                let anchorPosition = arrowAnchorPosition(note, anchorUnderMouse);
                let distance = anchorPosition.distanceTo(realPosition);
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closestAnchorType = anchorUnderMouse;
                    closestNoteVS = noteVS;
                    closestAnchorPosition = anchorPosition;
                }
            } else if (note.rect().contains(realPosition)) {
                // If the click is inside the note, set anchor to auto
                anchorUnderMouse = ArrowAnchorOnNoteType.auto;
                if (closestNoteVS === null) {
                    closestNoteVS = noteVS;
                }
            }
        }

        if (closestAnchorType === ArrowAnchorOnNoteType.none && closestNoteVS !== null) {
            closestAnchorType = ArrowAnchorOnNoteType.auto;
        }

        let suggestion = new AnchorOnNoteSuggestion(
            closestAnchorType, closestNoteVS, closestAnchorPosition);
        return suggestion;
    }

    arrowVS_withVisibleControlPoints(): ArrowViewState | null {
        // If there's only one element selected and it's an arrow - then the
        // control points should be visible
        if (this.selectedElementsVS.size === 1) {
            let selectedElement = this.selectedElementsVS.values().next().value;
            if (selectedElement instanceof ArrowViewState) {
                return selectedElement;
            }
        }
        return null;
    }

    resizeCircleAt(realPosition: Point2D): NoteViewState | null {
        // Iterate through all notes and get the one where the bottom right corner
        // is closest to the mouse position (if within RESIZE_CIRCLE_RADIUS)
        let closestNoteVS: NoteViewState | null = null;
        let closestDistance = Number.MAX_VALUE;
        for (let noteVS of this.noteViewStatesById.values()) {
            let note = noteVS.note();
            let bottomRight = note.rect().bottomRight();
            let distance = bottomRight.distanceTo(realPosition);
            if (distance < closestDistance) {
                closestDistance = distance;
                closestNoteVS = noteVS;
            }
        }
        if (closestDistance < RESIZE_CIRCLE_RADIUS) {
            return closestNoteVS;
        }
        return null;
    }
}

export class AnchorOnNoteSuggestion {
    public anchorType: ArrowAnchorOnNoteType;
    public _noteViewState: NoteViewState | null;
    public position: Point2D;

    constructor(anchorType: ArrowAnchorOnNoteType, noteViewState: NoteViewState | null, position: Point2D) {
        this.anchorType = anchorType;
        this._noteViewState = noteViewState;
        this.position = position
    }

    get noteViewState(): NoteViewState {
        if (this._noteViewState === null) {
            throw new Error('Note view state not set in anchor suggestion');
        }
        return this._noteViewState;
    }

    get onAnchor(): boolean {
        return this.anchorType !== ArrowAnchorOnNoteType.none && this.anchorType !== ArrowAnchorOnNoteType.auto;
    }

    get onNote(): boolean {
        return this._noteViewState !== null;
    }
}

export class MouseState {
    buttons: number = 0;
    position: Point2D = new Point2D([0, 0]);
    positionOnPress: Point2D = new Point2D([0, 0]);
    buttonsOnLeave: number = 0;

    get rightIsPressed() {
        return (this.buttons & 2) !== 0;
    }
    get leftIsPressed() {
        return (this.buttons & 1) !== 0;
    }
    applyPressEvent(event: React.MouseEvent) {
        this.positionOnPress = new Point2D([event.clientX, event.clientY]);
        this.buttons = event.buttons;
    }
    applyMoveEvent(event: React.MouseEvent) {
        this.position = new Point2D([event.clientX, event.clientY]);
    }
    applyReleaseEvent(event: React.MouseEvent) {
        this.buttons = event.buttons;
    }
}
