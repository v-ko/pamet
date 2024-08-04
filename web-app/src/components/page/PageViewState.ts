import { ObservableMap, ObservableSet, computed, makeObservable, observable, reaction } from 'mobx';
import { ARROW_SELECTION_RADIUS, DEFAULT_EYE_HEIGHT } from '../../core/constants';
import { Point2D } from '../../util/Point2D';
import { Page, PageData } from '../../model/Page';
import { Viewport } from './Viewport';
import { RectangleData } from '../../util/Rectangle';
import { NoteViewState } from '../note/NoteViewState';
import { ArrowViewState } from '../arrow/ArrowViewState';
import { pamet } from '../../core/facade';
import { getLogger } from 'fusion/logging';
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
    _pageData!: PageData;

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
    realMousePositionOnCanvas: Point2D | null = null;
    // mouseButtons: number = 0;

    // Drag navigation
    dragNavigationStartPosition: Point2D | null = null;

    // Selection related
    selectedElementsVS: ObservableSet<CanvasElementViewState> = observable.set();
    mousePositionOnDragSelectionStart: Point2D | null = null;
    dragSelectionRectData: RectangleData | null = null;
    dragSelectedElementsVS: ObservableSet<CanvasElementViewState> = observable.set();

    // Auto navigation (out of order. Check if it's salvageable)
    autoNavAnimation: ViewportAutoNavAnimation | null = null;

    // Edit window
    noteEditWindowState: EditComponentState | null = null;

    constructor(page: Page) {
        this.updateFromPage(page);


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
            realMousePositionOnCanvas: observable,

            dragNavigationStartPosition: observable,
            selectedElementsVS: observable,
            mousePositionOnDragSelectionStart: observable,
            dragSelectionRectData: observable,
            dragSelectedElementsVS: observable,
            autoNavAnimation: observable,

            noteEditWindowState: observable,

            viewport: computed
        });

    }

    updateFromPage(page: Page) {
        this._pageData = page.data();
    }

    createElementViewStates() {
        const notes = Array.from(pamet.notes({ parentId: this.page.id }))
        this._updateNoteViewStates(notes);
        const arrows = Array.from(pamet.arrows({ parentId: this.page.id }))
        this._updateArrowViewStates(arrows);
    }

    addViewStateForElement(element: Note | Arrow) {
        if (element instanceof Note) {
            if (this.noteViewStatesByOwnId.has(element.own_id)) {
                log.error('Note already exists in page view state', element)
                return;
            }
            let nvs = new NoteViewState(element);
            this.noteViewStatesByOwnId.set(element.own_id, nvs);

        } else if (element instanceof Arrow) {
            if (this.arrowViewStatesByOwnId.has(element.own_id)) {
                log.error('Arrow already exists in page view state', element)
                return;
            }
            let missingAnchorVS = false;
            let headNVS: NoteViewState | null = null;
            if (element.head_note_id) {
                headNVS = this.noteViewStatesByOwnId.get(element.head_note_id) || null
                if (!headNVS) {
                    missingAnchorVS = true;
                    log.error('HEAD NOTE NOT FOUND', element.head_note_id)
                }
            }

            let tailNVS: NoteViewState | null = null;
            if (element.tail_note_id) {
                tailNVS = this.noteViewStatesByOwnId.get(element.tail_note_id) || null
                if (!tailNVS) {
                    missingAnchorVS = true;
                    log.error('TAIL NOTE NOT FOUND', element.tail_note_id)
                }
            }

            if (missingAnchorVS) {
                log.error('Arrow not added due to missing anchor view state')
                return;
            }

            this.arrowViewStatesByOwnId.set(element.own_id, new ArrowViewState(element, headNVS, tailNVS));
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

        let headNVS: NoteViewState | null = null;
        if (arrow.head_note_id) {
            headNVS = this.noteViewStatesByOwnId.get(arrow.head_note_id) || null
            if (!headNVS) {
                throw Error('Head note not found ' + arrow.head_note_id)
            }
        }

        let tailNVS: NoteViewState | null = null;
        if (arrow.tail_note_id) {
            tailNVS = this.noteViewStatesByOwnId.get(arrow.tail_note_id) || null
            if (!tailNVS) {
                throw Error('Tail note not found ' + arrow.tail_note_id)
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
        let page = pamet.findOne({ id: this._pageData.id });
        if (page === null) {
            throw new Error(`Page with id ${this._pageData.id} not found`);
        }
        return page as Page;
        // return new Page(this._pageData);  the wrapped (observable) pageData causes problems
    }

    clearMode() {
        log.info('Clearing page mode')
        this.mode = PageMode.None;

        this.dragNavigationStartPosition = null;

        // Drag select related
        this.mousePositionOnDragSelectionStart = null;
        this.dragSelectionRectData = null;
        this.dragSelectedElementsVS.clear();

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
        let viewport = Viewport.fromProjectedGeometry(this.viewportGeometry, this.viewportHeight);
        viewport.setDevicePixelRatio(window.devicePixelRatio) // was not used
        viewport.moveRealCenterTo(this.viewportCenter);
        return viewport;
    }

    *noteViewsAt(position: Point2D, radius: number = 0): Generator<NoteViewState> {
        for (let noteViewState of this.noteViewStatesByOwnId.values()) {
            let note = noteViewState.note();
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
