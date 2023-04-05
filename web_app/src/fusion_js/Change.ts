import { Entity } from "./libs/entity"
import { current_time, get_new_id } from "./util"

export enum ChangeTypes {
    EMPTY = 0,
    CREATE = 1,
    UPDATE = 2,
    DELETE = 3
}


interface ChangeData {
    id: string
    old_state: Entity
    new_state: Entity
    time: Date
}


export class Change {
    // id: string | null
    // old_state: Entity

    public id?: string
    public old_state?: Entity
    public new_state?: Entity
    public time?: Date


    constructor(id?: string, old_state?: Entity, new_state?: Entity, time?: Date) {
        this.id = id ?? get_new_id()
        this.old_state = old_state
        this.new_state = new_state
        this.time = time ?? current_time()
    }

    change_type() {
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

    props() {
        // return a changeData object via ts casting
        return {
            id: this.id,
            old_state: this.old_state,
            new_state: this.new_state,
            time: this.time
        } as ChangeData
    }

    // @classmethod
    // def from_dict(cls, change_dict: dict) -> Change:
    //     if 'delta' in change_dict:
    //         return cls.from_safe_delta_dict(change_dict)
    //     return cls(**change_dict)

    from_props(props: ChangeData) {
        this.id = props.id
        this.old_state = props.old_state
        this.new_state = props.new_state
        this.time = props.time
    }


    // @classmethod
    // def from_safe_delta_dict(cls, change_dict: dict):
    //     old_state_dict = change_dict.get('old_state', None)
    //     new_state_dict = change_dict.get('new_state', None)
    //     delta = change_dict.get('delta', None)

    //     # Get the delta and use it to generate the new_state
    //     delta = change_dict.pop('delta', None)
    //     if delta is not None:
    //         new_state_dict = copy(old_state_dict)
    //         new_state_dict.update(**delta)

    //     if old_state_dict:
    //         change_dict['old_state'] = load_from_dict(old_state_dict)
    //     if new_state_dict:
    //         change_dict['new_state'] = load_from_dict(new_state_dict)

    //     return cls(**change_dict)

}
