import { Entity, EntityData } from "./libs/Entity"
import { currentTime, get_new_id } from "./util"

export enum ChangeTypes {
    EMPTY = 0,
    CREATE = 1,
    UPDATE = 2,
    DELETE = 3
}


interface ChangeData {
    id: string
    old_state: Entity<EntityData>
    new_state: Entity<EntityData>
    time: Date
}


export class Change {
    public id?: string
    public old_state?: Entity<EntityData>
    public new_state?: Entity<EntityData>
    public time?: Date


    constructor(id?: string, old_state?: Entity<EntityData>, new_state?: Entity<EntityData>, time?: Date) {
        this.id = id ?? get_new_id()
        this.old_state = old_state
        this.new_state = new_state
        this.time = time ?? currentTime()
    }

    changeType() {
        if (this.old_state && this.new_state) {
            return ChangeTypes.UPDATE
        } else if (this.old_state) {
            return ChangeTypes.DELETE
        } else if (this.new_state) {
            return ChangeTypes.CREATE
        } else {
            return ChangeTypes.EMPTY
        }
    }

    asdict() {
        /**
         * Return a dictionary representation of the change.
         */
        return {
            id: this.id,
            old_state: this.old_state,
            new_state: this.new_state,
            time: this.time
        } as ChangeData
    }

    static fromDict(props: ChangeData): Change {
        //     if 'delta' in change_dict:
        //         return cls.from_safe_delta_dict(change_dict)
        return new Change(
            props.id, props.old_state, props.new_state, props.time);
    }

    static create(entity: Entity<EntityData>): Change {
        return new Change(undefined, undefined, entity)
    }

    static delete(entity: Entity<EntityData>): Change {
        return new Change(undefined, entity, undefined)
    }

    static update(old_state: Entity<EntityData>, new_state: Entity<EntityData>): Change {
        return new Change(undefined, old_state, new_state)
    }

    isCreate(): boolean {
        return this.changeType() === ChangeTypes.CREATE
    }

    isDelete(): boolean {
        return this.changeType() === ChangeTypes.DELETE
    }

    isUpdate(): boolean {
        return this.changeType() === ChangeTypes.UPDATE
    }

    isEmpty(): boolean {
        return this.changeType() === ChangeTypes.EMPTY
    }

    lastState(): Entity<EntityData> | undefined {
        /**
         * Return the latest available state.
         */
        if (this.new_state !== undefined) {
            return this.new_state
        }
        return this.old_state
    }

    reversed(): Change {
        /**
         * Return a reversed change.
         */
        if (this.isCreate()) {
            return Change.delete(this.new_state!)
        } else if (this.isDelete()) {
            return Change.create(this.old_state!)
        } else if (this.isUpdate()) {
            return Change.update(this.new_state!, this.old_state!)
        } else {
            // raise exeption
            throw new Error("Cannot reverse empty change")
        }
    }
}
