import { Entity, EntityData } from "pyfusion/libs/Entity";

export interface PametElementData extends EntityData {
    // page_id: string;
    // own_id: string;
}

export function elementId(page_id: string, own_id: string): string {
    return `${page_id}-${own_id}`
}

export function elementPageId(id: string): string {
    return id.split('-')[0]
}

export function elementOwnId(id: string): string {
    return id.split('-')[1]
}


export class PametElement<T extends PametElementData> extends Entity<T> implements PametElementData {


    get page_id(): string {
        return elementPageId(this.id);
    }
    get own_id(): string {
        return elementOwnId(this.id);
    }
    get parentId(): string {
        return this.page_id
    }
}
