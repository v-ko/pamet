import { ObservableMap, ObservableSet, computed, makeObservable, observable, reaction, toJS } from 'mobx';
import { ARROW_ANCHOR_ON_NOTE_SUGGEST_RADIUS, ARROW_SELECTION_RADIUS, DEFAULT_EYE_HEIGHT, RESIZE_CIRCLE_RADIUS } from '../../core/constants';
import { Point2D } from '../../util/Point2D';
import { Page, PageData } from '../../model/Page';
import { Viewport } from './Viewport';
import { RectangleData } from '../../util/Rectangle';
import { NoteViewState } from '../note/NoteViewState';
import { ArrowViewState } from '../arrow/ArrowViewState';
import { pamet } from '../../core/facade';
import { getLogger } from 'fusion/logging';
import { Note } from '../../model/Note';
import { anchorIntersectsCircle, Arrow, arrowAnchorPosition, ArrowAnchorOnNoteType } from '../../model/Arrow';
import { ElementViewState as CanvasElementViewState } from './ElementViewState';
import { EditComponentState } from '../note/EditComponent';
import { Size } from '../../util/Size';
import { CanvasPageRenderer } from './DirectRenderer';

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
    ChildMove,
    CreateArrow,
    ArrowControlPointDrag,
    AutoNavigation,
    DraggingEditWindow
}


export class PageViewState {
    _pageData!: PageData;
    _renderer: CanvasPageRenderer;

    // Elements
    noteViewStatesByOwnId: ObservableMap<string, NoteViewState>;
    arrowViewStatesByOwnId: ObservableMap<string, ArrowViewState>;

    // Viewport
    viewportCenter: Point2D = new Point2D(0, 0);
    viewportHeight: number = DEFAULT_EYE_HEIGHT;
    viewportGeometry: [number, number, number, number] = [0, 0, 0, 0];

    // Common
    mode: PageMode = PageMode.None;
    viewportCenterOnModeStart: Point2D = new Point2D(0, 0); // In real coords
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
    noteEditWindowState: EditComponentState | null = null;

    // Note resize related
    noteResizeClickRealPos: Point2D = new Point2D(0, 0);
    noteResizeInitialSize: Size = new Size(0, 0);
    noteResizeCircleClickOffset: Point2D = new Point2D(0, 0);
    notesBeingResized: NoteViewState[] = [];

    // Arrow related
    // Arrow creation
    newArrowViewState: ArrowViewState | null = null;
    // Arrow editing
    draggedControlPointIndex: number | null = null;

    constructor(page: Page) {
        this.updateFromPage(page);
        this._renderer = new CanvasPageRenderer();

        this.noteViewStatesByOwnId = new ObservableMap<string, NoteViewState>();
        this.arrowViewStatesByOwnId = new ObservableMap<string, ArrowViewState>();

        makeObservable(this, {
            _pageData: observable,
            page: computed,

            noteViewStatesByOwnId: observable,
            arrowViewStatesByOwnId: observable,

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

        // test note updat reaction
        reaction(() => Array.from(this.noteViewStatesByOwnId.values()).map((noteVS) => noteVS._noteData), (values) => {
            log.info('Note view states changed', values);
        });
    }

    updateFromPage(page: Page) {
        this._pageData = page.data();
    }

    get renderer() {
        return this._renderer;
    }

    createElementViewStates() {
        const notes = Array.from(pamet.notes({ parentId: this.page.id }))
        this._updateNoteViewStates(notes);
        const arrows = Array.from(pamet.arrows({ parentId: this.page.id }))
        this._updateArrowViewStates(arrows);
    }

    _addViewStateForNote(element: Note) {
        if (this.noteViewStatesByOwnId.has(element.own_id)) {
            log.error('Note already exists in page view state', element)
            return;
        }
        let nvs = new NoteViewState(element);
        this.noteViewStatesByOwnId.set(element.own_id, nvs);
    }

    _addViewStateForArrow(element: Arrow){
        if (this.arrowViewStatesByOwnId.has(element.own_id)) {
            log.error('Arrow already exists in page view state', element)
            return;
        }
        let headNVS: NoteViewState | null = null;
        if (element.headNoteId) {
            headNVS = this.noteViewStatesByOwnId.get(element.headNoteId) || null
            if (!headNVS) {
                log.error('Arrow head note not found', element.headNoteId, 'setting head to (0, 0)')
                element.setHead(new Point2D(0, 0), null, ArrowAnchorOnNoteType.none)
            }
        } else if(element.headAnchorType !== ArrowAnchorOnNoteType.none) {
            log.error('No headd note id, but anchor is not fixed. Overwriting in view state.')
            element.setHead(new Point2D(0, 0), null, ArrowAnchorOnNoteType.none)
        }

        let tailNVS: NoteViewState | null = null;
        if (element.tailNoteId) {
            tailNVS = this.noteViewStatesByOwnId.get(element.tailNoteId) || null
            if (!tailNVS) {
                log.error('Arrow tail note not found', element.tailNoteId, 'setting tail to (0, 0)')
                element.setTail(new Point2D(0, 0), null, ArrowAnchorOnNoteType.none)
            }
        } else if(element.tailAnchorType !== ArrowAnchorOnNoteType.none) {
            log.error('No tail note id, but anchor is not fixed. Overwriting in view state.')
            element.setTail(new Point2D(0, 0), null, ArrowAnchorOnNoteType.none)
        }

        this.arrowViewStatesByOwnId.set(element.own_id, new ArrowViewState(element, headNVS, tailNVS));
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
            this.noteViewStatesByOwnId.delete(element.own_id);
        } else if (element instanceof Arrow) {
            this.arrowViewStatesByOwnId.delete(element.own_id);
        }
    }

    updateEVS_fromElement(element: Note | Arrow) {
        if (element instanceof Note) {
            let nvs = this.noteViewStatesByOwnId.get(element.own_id);
            if (nvs === undefined) {
                log.error('Note view state not found for note', element)
                return;
            }
            nvs.updateFromNote(element);
        } else if (element instanceof Arrow) {
            let avs = this.arrowViewStatesByOwnId.get(element.own_id);
            if (avs === undefined) {
                log.error('Arrow view state not found for arrow', element)
                return;
            }

            // Get anchors if any
            let headNVS_: NoteViewState | null;
            let tailNVS_: NoteViewState | null;
            try {
                let { headNVS, tailNVS } = this.noteVS_anchorsForArrow(element);
                headNVS_ = headNVS;
                tailNVS_ = tailNVS;
            } catch (e) {
                log.error('Error getting anchors for arrow', element)
                return;
            }
            avs.updateFromArrow(element, headNVS_, tailNVS_);
        }
    }

    noteVS_anchorsForArrow(arrow: Arrow) {
        /* Get the NoteViewStates for the arrow's head and tail notes */
        let headNVS: NoteViewState | null = null;
        if (arrow.headNoteId) {
            headNVS = this.noteViewStatesByOwnId.get(arrow.headNoteId) || null
            if (!headNVS) {
                throw Error('Head note not found ' + arrow.headNoteId)
            }
        }

        let tailNVS: NoteViewState | null = null;
        if (arrow.tailNoteId) {
            tailNVS = this.noteViewStatesByOwnId.get(arrow.tailNoteId) || null
            if (!tailNVS) {
                throw Error('Tail note not found ' + arrow.tailNoteId)
            }
        }

        return { headNVS, tailNVS }
    }

    _updateNoteViewStates(notes: Iterable<Note>) {
        console.log('Updating note view states from notes', notes)

        let nvsHasNoteMap = new Map<string, boolean>();
        for (let note of notes) {
            nvsHasNoteMap.set(note.own_id, true);
        }

        // Remove NoteViewStates for notes that have been removed
        for (let noteOwnId of this.noteViewStatesByOwnId.keys()) {
            if (!nvsHasNoteMap.has(noteOwnId)) {
                // console.log('REMOVING note', noteOwnId)
                this.removeViewStateForElement(this.noteViewStatesByOwnId.get(noteOwnId)!.note());
            }
        }

        // Add NoteViewStates for new notes
        for (let note of notes) {
            if (!this.noteViewStatesByOwnId.has(note.own_id)) {
                // console.log('ADDING note', note.own_id)
                this.addViewStateForElement(note);
            }
        }
    }

    _updateArrowViewStates(arrows: Iterable<Arrow>) {
        let arrowavsHasArrowMap = new Map<string, boolean>();
        for (let arrow of arrows) {
            arrowavsHasArrowMap.set(arrow.own_id, true);
        }

        // Remove ArrowViewStates for arrows that have been removed
        for (let arrowOwnId of this.arrowViewStatesByOwnId.keys()) {
            if (!arrowavsHasArrowMap.has(arrowOwnId)) {
                // console.log('REMOVING arrow', arrowOwnId)
                this.removeViewStateForElement(this.arrowViewStatesByOwnId.get(arrowOwnId)!.arrow());
            }
        }

        // Add ArrowViewStates for new arrows
        for (let arrow of arrows) {
            if (!this.arrowViewStatesByOwnId.has(arrow.own_id)) {
                this.addViewStateForElement(arrow);
            }
        }
    }

    viewStateForElement(elementOwnId: string): NoteViewState | ArrowViewState | null {
        return this.noteViewStatesByOwnId.get(elementOwnId) || this.arrowViewStatesByOwnId.get(elementOwnId) || null;
    }

    get page() {
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
            let arrow = pamet.findOne({id: editedArrowVS!.arrow().id});
            if (!(arrow instanceof Arrow)) {
                log.error('Arrow not found for cp-dragged arrow with id', editedArrowVS.arrow().id)
                return;
            }
            this.updateEVS_fromElement(arrow);
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
        for (let noteViewState of this.noteViewStatesByOwnId.values()) {
            let note = noteViewState.note();
            let intersectRect = note.rect()
            if (radius > 0) {
                intersectRect.setSize(intersectRect.size().add(new Size(radius * 2, radius * 2)))
                intersectRect.setTopLeft(intersectRect.topLeft().subtract(new Point2D(radius, radius)))
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
        for (let arrowVS of this.arrowViewStatesByOwnId.values()) {
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
        for (let noteVS of this.noteViewStatesByOwnId.values()) {
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
