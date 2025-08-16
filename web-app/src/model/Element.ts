import { Entity, EntityData } from "fusion/model/Entity";

export interface PametElementData extends EntityData {
}


export class PametElement<T extends PametElementData> extends Entity<T> {
    get page_id(): string {
        return this._data.parent_id
    }
}
