import { reproducible_ids as reproducibleIds } from "..";
import { getLogger } from "../logging";
import { get_new_id as getNewId } from "../util";

const log = getLogger('entity.ts');

// Library related variables and functions
const entityLibrary = {}
let _lastEntityId: number = 0


// type EntityId = string | string[];

function getEntityId(): string {
    if (reproducibleIds()) {
        _lastEntityId += 1;
        return _lastEntityId.toString().padStart(8, '0');
    } else {
        return getNewId();
    }
}


export function resetEntityIdCounter() {
    _lastEntityId = 0
}


export function entityType(entity_class: any): any {
    if (entity_class.type_name) {
        throw new Error('The type_name identifier is used in the serialization and is prohibited.')
    }

    let entityClassName = entity_class.constructor.name

    entityLibrary[entityClassName] = entity_class
    return entity_class
}


export function getEntityClassByName(entity_class_name: string) {
    return entityLibrary[entity_class_name]
}


// Serialization related functions
export function dumpToDict<T extends Entity<EntityData>>(entity: T): EntityData {
    const entity_dict: EntityData = entity.toObject()

    if (entity_dict.typeName !== undefined) {
        throw new Error('The typeName identifier is used in the serialization and is prohibited.')
    }

    entity_dict.typeName = entity.constructor.name
    return entity_dict
}


export function dumpAsJson(entity: any, ensure_ascii = false, dump_kwargs: any) {
    const entity_dict = dumpToDict(entity)
    const json_str = JSON.stringify(entity_dict, null, 2)
    return json_str
}


export function loadFromDict(entity_dict: any): any {
    const typeName = entity_dict.typeName
    const cls = getEntityClassByName(typeName)
    let instance: any

    if (cls === undefined) {
        throw new Error(`Entity class ${typeName} not found.`)
    } else {
        instance = cls(entity_dict)
    }
    return instance
}


export function loadFromJson(json_str: string): any {
    const entity_dict = JSON.parse(json_str)
    return loadFromDict(entity_dict)
}


// Entity definition
export interface EntityData {
    id: string;  // Allows for composite ids
    typeName?: string;
}


export abstract class Entity<T extends EntityData> {
    _data: T;

    constructor(data: T) {
        this._data = { ...data };

        // Assign an id if it is not provided
        if (this._data.id === undefined) {
            this._data.id = getEntityId()
        }

    }

    get data(): T {
        return this._data;
    }

    get id(): string {
        return this._data.id;
    }

    abstract get parentId(): string;
    get parent_id(): string {
        log.warning('parent_id is deprecated. Use parentId instead.');
        return this.parentId;
    }

    withId<S extends typeof this>(new_id: string): S {
        const newData = { ...this._data, id: new_id };
        return new (this.constructor as { new(data: T): S })(newData);
    }
    copy<S extends typeof this>(): S {
        // We're copying the data object in the constructor, so no need to do it here
        return new (this.constructor as { new(data: T): S })(this._data);
    }

    toObject(): T {
        return this._data;
    };

    replace(new_data: Partial<T>) {
        if (new_data.id !== undefined) {
            throw new Error(
                'The id of an entity is immutable. Use the withId method to create an object with the new id.');
        }
        const newData = { ...this._data, ...new_data };
        this._data = newData;
    }

    replace_silent(new_data: Record<string, any>): Record<string, any> {
        const newData: Partial<T> = {};
        const leftovers: Record<string, any> = {};

        for (const key in new_data) {
            if ((key as keyof T) in this._data || typeof (this._data as any)[key] !== 'undefined') {
                newData[key as keyof T] = new_data[key];
            } else {
                leftovers[key] = new_data[key];
            }
        }

        this.replace(newData);

        return leftovers;
    }


}

