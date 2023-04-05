import { Entity } from "../fusion_js/libs/entity";
import { NoteData } from "../types/Note";
import { Rectangle } from "../util/Rectangle";

export class Note extends Entity{
    private data: NoteData;

    constructor(data: NoteData) {
        super()
        this.data = data;
    }
    get rect(): Rectangle {
        let x = this.data.geometry[0];
        let y = this.data.geometry[1];
        let w = this.data.geometry[2];
        let h = this.data.geometry[3];
        return new Rectangle(x, y, w, h);
    }
}
