import { Entity, EntityData, entityType } from "../fusion/libs/Entity";

export interface PageChildData extends EntityData {
    page_id: string;
    own_id: string;
}

export class PageChild<T extends PageChildData> extends Entity<T> implements PageChildData {

    get id(): string {
        if (this._data.page_id === undefined || this._data.own_id === undefined){
            console.log(this)
            throw new Error('FUCK')
        }
        return `${this._data.page_id}-${this._data.own_id}`
    }
    get page_id(): string {
        return this._data.page_id;
    }
    get own_id(): string {
        return this._data.own_id;
    }
    get parentId(): string {
        return this._data.page_id;
    }
}
