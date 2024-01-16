import { ObservableMap, computed, makeObservable, observable } from 'mobx';
import { DEFAULT_EYE_HEIGHT } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { Page, PageData } from '../../model/Page';
import { Viewport } from '../Viewport';
import { NoteViewState } from '../note/NoteViewState';
import { ArrowViewState } from '../ArrowViewState';
import { pamet } from '../../facade';
import { getLogger } from '../../fusion/logging';

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


export class PageViewState extends Page {
    noteViewStates: ObservableMap<string, NoteViewState>;
    arrowViewStates: ObservableMap<string, ArrowViewState>;
    mode: PageMode = PageMode.None;

    viewportCenter: Point2D = new Point2D(0, 0);
    viewportHeight: number = DEFAULT_EYE_HEIGHT;
    viewportGeometry: [number, number, number, number] = [0, 0, 0, 0];

    // Helper props
    viewportCenterOnModeStart: Point2D | null = null;

    // Drag navigation
    dragNavigationStartPosition: Point2D | null = null;

    //
    selection: Array<string> = [];

    autoNavAnimation: ViewportAutoNavAnimation | null = null;

    constructor(page: PageData) {
        super(page);
        this.noteViewStates = new ObservableMap<string, NoteViewState>();
        this.arrowViewStates = new ObservableMap<string, ArrowViewState>();

        this.populateChildViewStates();

        makeObservable(this, {
            _data: observable,
            name: computed,
            tour_segments: computed,
            noteViewStates: observable,
            arrowViewStates: observable,
            mode: observable,
            viewportCenter: observable,
            viewportHeight: observable,
            viewportGeometry: observable,
            viewportCenterOnModeStart: observable,
            dragNavigationStartPosition: observable,
            selection: observable,
            autoNavAnimation: observable,
            viewport: computed
        });

        // Subscribe to page updates and child note add/remove changes
        pamet.rawChagesByIdChannel.subscribe(this.handlePageChange, this.id);
        pamet.rawChagesByParentIdChannel.subscribe(this.handleChildChange, this.id);
    }

    populateChildViewStates() {
        // Get the entities
        const notes = Array.from(pamet.notes({ parentId: this.id }))
        const arrows = Array.from(pamet.arrows({ parentId: this.id }))

        // Create view states for each entity ()
        notes.forEach((note) => {
            this.noteViewStates.set(note.own_id, new NoteViewState(note))
        })
        arrows.forEach((arrow) => {
            let headNVS: NoteViewState | null = null;
            // = this.noteViewStates.get(arrow.head_note_id) || null
            if (arrow.head_note_id) {
                headNVS = this.noteViewStates.get(arrow.head_note_id) || null
            }

            // let tailNVS = this.noteViewStates.get(arrow.tail_note_id) || null
            let tailNVS: NoteViewState | null = null;
            if (arrow.tail_note_id) {
                tailNVS = this.noteViewStates.get(arrow.tail_note_id) || null
            }

            let pathCalcPrecision = this.viewport.heightScaleFactor();
            this.arrowViewStates.set(arrow.own_id, new ArrowViewState(arrow, headNVS, tailNVS, pathCalcPrecision))
        })
        log.info(`Populated page ${this.id} with ${notes.length} notes and ${arrows.length} arrows`)
    }

    handlePageChange = (change: any) => {
        if (change.isUpdate()) {
            console.log('Page update', change);
        }
    }

    handleChildChange = (change: any) => {
        if (change.isUpdate()) {
            console.log('Child update', change);
        }
    }

    clearMode() {
        this.mode = PageMode.None;

        this.dragNavigationStartPosition = null;
        this.viewportCenterOnModeStart = null;
    }

    setMode(mode: PageMode) {
        if (this.mode !== PageMode.None) {
            this.clearMode();
        }
        this.mode = mode;
    }

    get viewport() {  // Todo: make this a computed property?
        return new Viewport(this.viewportCenter, this.viewportHeight, this.viewportGeometry);
    }
}
