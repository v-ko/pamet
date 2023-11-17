import { Change } from "../Change";
import { Entity, EntityData } from "../libs/Entity";

// a searchFilter is a dict, where there can be an id, a parent_id, a type or any other property
export interface SearchFilter {
    id?: string;
    parentId?: string;
    type?: any;
    [key: string]: any;
}

export abstract class Repository {
    // _generatedChangesChannel: Channel | undefined;
    // _changeApplicationChannel: Channel | undefined;

    abstract insertOne(entity: Entity<EntityData>): Change;

    abstract find<T extends Entity<EntityData>>(filter: SearchFilter): Generator<T>;

    abstract findOne<T extends Entity<EntityData>>(filter: SearchFilter): T | undefined;

    abstract updateOne(entity: Entity<EntityData>): Change;

    abstract removeOne(entity: Entity<EntityData>): Change;

    // Batch operations (inefficient implementations)
    insert(entities: Entity<EntityData>[]): Change[] {
        return entities.map(entity => this.insertOne(entity))
    }
    remove(entities: Entity<EntityData>[]): Change[] {
        return entities.map(entity => this.removeOne(entity))
    }
    update(entities: Entity<EntityData>[]): Change[] {
        return entities.map(entity => this.updateOne(entity))
    }

    // // Change stream functionality
    // setGeneratedChangesChannel(channel: Channel) {
    //     this._generatedChangesChannel = channel;
    // }

    // setChangeApplicationChannel(channel: Channel) {
    //     this._changeApplicationChannel = channel;
    // }

}


