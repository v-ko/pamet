import { ObservableMap, ObservableSet, computed, makeObservable, observable, reaction } from 'mobx';
import { ARROW_SELECTION_RADIUS, DEFAULT_EYE_HEIGHT } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { Page, PageData } from '../../model/Page';
import { Viewport } from '../Viewport';
import { RectangleData } from '../../util/Rectangle';
import { NoteViewState } from '../note/NoteViewState';
import { ArrowViewState } from '../ArrowViewState';
import { pamet } from '../../facade';
import { getLogger } from '../../fusion/logging';
import { Note } from '../../model/Note';
import { Arrow } from '../../model/Arrow';
import { InternalLinkNoteViewState } from '../note/InternalLinkNVS';
import { InternalLinkNote } from '../../model/InternalLinkNote';
import { PageChildViewState } from './PageChildViewState';
import { Rectangle } from '../../util/Rectangle';

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
    AutoNavigation
}


export class PageViewState {
    _pageData: PageData;

    noteViewStatesByOwnId: ObservableMap<string, NoteViewState>;
    arrowViewStatesByOwnId: ObservableMap<string, ArrowViewState>;
    mode: PageMode = PageMode.None;

    viewportCenter: Point2D = new Point2D(0, 0);
    viewportHeight: number = DEFAULT_EYE_HEIGHT;
    viewportGeometry: [number, number, number, number] = [0, 0, 0, 0];

    //
    viewportCenterOnModeStart: Point2D | null = null;

    // Drag navigation
    dragNavigationStartPosition: Point2D | null = null;

    // Selection related
    selectedChildren: ObservableSet<PageChildViewState> = observable.set();
    mousePositionOnDragSelectionStart: Point2D | null = null;
    dragSelectionRectData: RectangleData | null = null;
    dragSelectedChildren: ObservableSet<PageChildViewState> = observable.set();

    autoNavAnimation: ViewportAutoNavAnimation | null = null;

    constructor(page: Page) {
        console.log('PageViewState page', page)

        this._pageData = page.data();
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
            mode: observable,
            viewportCenter: observable,
            viewportHeight: observable,
            viewportGeometry: observable,
            viewportCenterOnModeStart: observable,
            dragNavigationStartPosition: observable,
            selectedChildren: observable,
            mousePositionOnDragSelectionStart: observable,
            dragSelectionRectData: observable,
            dragSelectedChildren: observable,
            autoNavAnimation: observable,
            viewport: computed
        });

        // // Subscribe to page updates and child note add/remove changes
        // pamet.rawChagesByIdChannel.subscribe(this.handlePageChange, this.id);
        // pamet.rawChagesByParentIdChannel.subscribe(this.handleChildChange, this.id);

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
            () => pamet.find({ parentId: this.page.id, type: Note }) as Generator<Note>,
            notes => {
                this._updateNoteViewStatesFromNotes(notes)
            }
        );

        // Update arrowViewStates when arrows are added or removed
        reaction(
            () => pamet.find({ parentId: this.page.id, type: Arrow }) as Generator<Arrow>,
            arrows => {
                this._updateArrowViewStatesFromStore(arrows)
            }
        );

        // Test selectedChildren updates TMP
        reaction(
            () => this.selectedChildren.values(),
            selectedChildren => {
                    console.log('selectedChildren TEST', Array.from(selectedChildren))
            }
        );
    }

    _updateNoteViewStatesFromNotes(notes: Iterable<Note>) {
        //map encoding enumeration
        // enum EntryMarker {
        //     NotePresent = 0,
        //     NoteRemoved = 1,
        //     NoteAdded = 2,
        //     NoteTypeUpdated = 3,
        // }
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
                this.noteViewStatesByOwnId.set(note.own_id, this._newNVS_forNote(note));
            }
        }
    }

    _newNVS_forNote(note: Note): NoteViewState {
        // console.log('newNVS_forNote', note)
        if (note instanceof InternalLinkNote) {
            return new InternalLinkNoteViewState(note);
        } else {
            return new NoteViewState(note);
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

    viewStateForPageChild(childOwnId: string): NoteViewState | ArrowViewState | null {
        return this.noteViewStatesByOwnId.get(childOwnId) || this.arrowViewStatesByOwnId.get(childOwnId) || null;
    }

    get page() {
        return new Page(this._pageData);
    }

    handlePageChange = (change: any) => {
        if (change.isUpdate()) {
            console.log('Page update', change);
        }
    }

    // handleChildChange = (change: any) => {
    //     if (change.isUpdate()) {
    //         console.log('Child update', change);
    //     }
    // }

    clearMode() {
        this.mode = PageMode.None;

        this.dragNavigationStartPosition = null;
        this.viewportCenterOnModeStart = null;

        // Drag select related
        this.mousePositionOnDragSelectionStart = null;
        this.dragSelectionRectData = null;
        this.dragSelectedChildren.clear();
    }

    setMode(mode: PageMode) {
        log.info('Setting page mode', mode)
        if (this.mode !== PageMode.None) {
            this.clearMode();
        }
        this.mode = mode;
    }

    get viewport() {  // Todo: make this a computed property?
        return new Viewport(this.viewportCenter, this.viewportHeight, this.viewportGeometry);
    }

    *noteViewsAt(position: Point2D, radius: number = 0): Generator<NoteViewState> {
        for (let noteViewState of this.noteViewStatesByOwnId.values()) {
            if (radius > 0) {
                let intersectRect = noteViewState.note.rect()
                intersectRect.setSize(intersectRect.size().add(new Point2D(radius, radius)))
                intersectRect.setTopLeft(intersectRect.topLeft().subtract(new Point2D(radius, radius)))
            }
            if (noteViewState.note.rect().contains(position)) {
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
