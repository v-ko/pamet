import { computed, makeObservable, observable } from 'mobx';
import { Note } from "@/model/Note";
import { Point2D } from 'fusion/primitives/Point2D';
import { pamet } from "@/core/facade";

export class NoteEditViewState {
  targetNote: Note;
  center: Point2D;

  // Drag-by-title-bar related
  isBeingDragged: boolean = false;
  topLeftOnDragStart: Point2D = new Point2D([0, 0]);
  dragStartClickPos: Point2D = new Point2D([0, 0]);

  constructor(centerAt: Point2D, note: Note) {
    this.center = centerAt; // Pixel space
    this.targetNote = note;

    makeObservable(this, {
      center: observable,
      targetNote: observable,
      isBeingDragged: observable,
      creatingNote: computed,
    });
  }

  get creatingNote() {
    return pamet.note(this.targetNote.id) === undefined;
  }
}
