import { ObservableMap, ObservableSet, computed, makeObservable, observable, reaction } from 'mobx';
import { ARROW_SELECTION_RADIUS, DEFAULT_EYE_HEIGHT } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { Page, PageData } from '../../model/Page';
import { Viewport } from './Viewport';
import { RectangleData } from '../../util/Rectangle';
import { NoteViewState } from '../note/NoteViewState';
import { ArrowViewState } from '../arrow/ArrowViewState';
import { pamet } from '../../facade';
import { getLogger } from 'pyfusion/logging';
import { Note } from '../../model/Note';
import { Arrow } from '../../model/Arrow';
import { ElementViewState as CanvasElementViewState } from './ElementViewState';
import { EditComponentState } from '../note/EditComponent';
import { Size } from '../../util/Size';

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
    ArrowEdgeDrag,
    AutoNavigation,
    DraggingEditWindow
}


export class PageViewState {
    _pageData: PageData;
    _notesStore: ObservableMap<string, Note>;

    // Elements
    noteViewStatesByOwnId: ObservableMap<string, NoteViewState>;
    arrowViewStatesByOwnId: ObservableMap<string, ArrowViewState>;

    // Viewport
    viewportCenter: Point2D = new Point2D(0, 0);
    viewportHeight: number = DEFAULT_EYE_HEIGHT;
    viewportGeometry: [number, number, number, number] = [0, 0, 0, 0];

    // Common
    mode: PageMode = PageMode.None;
    viewportCenterOnModeStart: Point2D = new Point2D(0, 0);
    realMousePositionOnCanvas: Point2D | null = null;
    // mouseButtons: number = 0;

    // Drag navigation
    dragNavigationStartPosition: Point2D | null = null;

    // Selection related
    selectedElements: ObservableSet<CanvasElementViewState> = observable.set();
    mousePositionOnDragSelectionStart: Point2D | null = null;
    dragSelectionRectData: RectangleData | null = null;
    dragSelectedElements: ObservableSet<CanvasElementViewState> = observable.set();

    // Auto navigation (out of order. Check if it's salvageable)
    autoNavAnimation: ViewportAutoNavAnimation | null = null;

    // Edit window
    noteEditWindowState: EditComponentState | null = null;

    constructor(page: Page) {
        this._pageData = page.data();

        let notesStore = pamet.noteStoresByParentId.get(page.id);
        if (notesStore === undefined) {
            throw new Error('No notes store found for page ' + page.id)
        }
        this._notesStore = notesStore;

        this.noteViewStatesByOwnId = new ObservableMap<string, NoteViewState>();
        this.arrowViewStatesByOwnId = new ObservableMap<string, ArrowViewState>();

        // Do an initial update of the note and arrow view states
        const notes = Array.from(pamet.notes({ parentId: this.page.id }))
        this._updateNoteViewStatesFromNotes(notes);
        const arrows = Array.from(pamet.arrows({ parentId: this.page.id }))
        this._updateArrowViewStatesFromStore(arrows);

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
            realMousePositionOnCanvas: observable,

            dragNavigationStartPosition: observable,
            selectedElements: observable,
            mousePositionOnDragSelectionStart: observable,
            dragSelectionRectData: observable,
            dragSelectedElements: observable,
            autoNavAnimation: observable,

            noteEditWindowState: observable,

            viewport: computed
        });

        // React on page changes
        reaction(
            () => pamet.page(this.page.id),
            (page) => {
                if (page) {
                    this._pageData = page.data();
                }
            }
        );

        // Update noteViewStates when notes are added or removed
        reaction(
            () => this._notesStore.values(),
            notes => {
                console.log('Notes changed', notes)
                this._updateNoteViewStatesFromNotes(notes)
            }
        );

        // Update arrowViewStates when arrows are added or removed
        reaction(
            () => pamet.find({ parentId: this.page.id, type: Arrow }) as Generator<Arrow>,
            arrows => {
                console.log('Arrows changed', arrows)
                this._updateArrowViewStatesFromStore(arrows)
            }
        );
    }

    notesStore(): ObservableMap<string, Note> {
        let store = pamet.noteStoresByParentId.get(this.page.id);
        if (!store) {
            throw new Error('[PageViewState] Notes store not found for page ' + this.page.id)
        }
        return store;
    }

    // get leftButtonPressed() {
    //     return (this.mouseButtons & 1) !== 0;
    // }

    // get rightButtonPressed() {
    //     return (this.mouseButtons & 2) !== 0;
    // }

    _updateNoteViewStatesFromNotes(notes: Iterable<Note>) {
        console.log('Updating note view states from notes', notes)

        let nvsHasNoteMap = new Map<string, boolean>();
        for (let note of notes) {
            nvsHasNoteMap.set(note.own_id, true);
        }

        // Remove NoteViewStates for notes that have been removed
        for (let noteOwnId of this.noteViewStatesByOwnId.keys()) {
            if (!nvsHasNoteMap.has(noteOwnId)) {
                // console.log('REMOVING note', noteOwnId)
                this.noteViewStatesByOwnId.delete(noteOwnId);
            }
        }

        // Add NoteViewStates for new notes
        for (let note of notes) {
            if (!this.noteViewStatesByOwnId.has(note.own_id)) {
                // console.log('ADDING note', note.own_id)
                this.noteViewStatesByOwnId.set(note.own_id, new NoteViewState(note));
            }
        }
    }

    _updateArrowViewStatesFromStore(arrows: Iterable<Arrow>) {
        let arrowavsHasArrowMap = new Map<string, boolean>();
        for (let arrow of arrows) {
            arrowavsHasArrowMap.set(arrow.own_id, true);
        }

        // Remove ArrowViewStates for arrows that have been removed
        for (let arrowOwnId of this.arrowViewStatesByOwnId.keys()) {
            if (!arrowavsHasArrowMap.has(arrowOwnId)) {
                // console.log('REMOVING arrow', arrowOwnId)
                this.arrowViewStatesByOwnId.delete(arrowOwnId);
            }
        }

        // Add ArrowViewStates for new arrows
        for (let arrow of arrows) {
            if (!this.arrowViewStatesByOwnId.has(arrow.own_id)) {
                // console.log('ADDING arrow', arrow.own_id)
                let missingAnchorVS = false;

                let headNVS: NoteViewState | null = null;
                if (arrow.head_note_id) {
                    headNVS = this.noteViewStatesByOwnId.get(arrow.head_note_id) || null
                    if (!headNVS) {
                        missingAnchorVS = true;
                        log.error('HEAD NOTE NOT FOUND', arrow.head_note_id)
                    }
                }

                let tailNVS: NoteViewState | null = null;
                if (arrow.tail_note_id) {
                    tailNVS = this.noteViewStatesByOwnId.get(arrow.tail_note_id) || null
                    if (!tailNVS) {
                        missingAnchorVS = true;
                        log.error('TAIL NOTE NOT FOUND', arrow.tail_note_id)
                    }
                }

                if (missingAnchorVS) {
                    log.error('Arrow not added due to missing anchor view state')
                    continue;
                }

                let pathCalcPrecision = this.viewport.heightScaleFactor();
                this.arrowViewStatesByOwnId.set(arrow.own_id, new ArrowViewState(arrow, headNVS, tailNVS, pathCalcPrecision));
            }
        }

    }

    viewStateForElement(elementOwnId: string): NoteViewState | ArrowViewState | null {
        return this.noteViewStatesByOwnId.get(elementOwnId) || this.arrowViewStatesByOwnId.get(elementOwnId) || null;
    }

    get page() {
        return new Page(this._pageData);
    }

    clearMode() {
        log.info('Clearing page mode')
        this.mode = PageMode.None;

        this.dragNavigationStartPosition = null;

        // Drag select related
        this.mousePositionOnDragSelectionStart = null;
        this.dragSelectionRectData = null;
        this.dragSelectedElements.clear();

        // Edit window related
        let editWS = this.noteEditWindowState!;
        if (editWS !== null) {
            editWS.isBeingDragged = false;
        }
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
        let viewport = new Viewport(new Point2D(0, 0), this.viewportHeight, this.viewportGeometry);
        viewport.setDevicePixelRatio(window.devicePixelRatio)
        viewport.moveRealCenterTo(this.viewportCenter);
        return viewport;
    }

    *noteViewsAt(position: Point2D, radius: number = 0): Generator<NoteViewState> {
        for (let noteViewState of this.noteViewStatesByOwnId.values()) {
            let note = noteViewState.note;
            if (radius > 0) {
                let intersectRect = note.rect()
                intersectRect.setSize(intersectRect.size().add(new Size(radius, radius)))
                intersectRect.setTopLeft(intersectRect.topLeft().subtract(new Point2D(radius, radius)))
            }
            if (note.rect().contains(position)) {
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
}
