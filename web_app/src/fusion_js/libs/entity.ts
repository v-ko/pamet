import { reproducible_ids } from "..";
import { get_logger } from "../logging";
import { get_new_id } from "../util";


const log = get_logger('entity.ts');
const entity_library = {}


let _last_entity_id: number = 0


function get_entity_id(): string {
    if (reproducible_ids()) {
      _last_entity_id += 1;
      return _last_entity_id.toString().padStart(8, '0');
    } else {
      return get_new_id();
    }
  }


export function reset_entity_id_counter() {
    _last_entity_id = 0
}

export function entity_type(entity_class){
    if (entity_class.type_name) {
        throw new Error('The type_name identifier is used in the serialization and is prohibited.')
    }

    entity_class.type_name = entity_class.name

    entity_library[entity_class.type_name] = entity_class
    return entity_class
}


export function get_entity_class_by_name(entity_class_name: string) {
    return entity_library[entity_class_name]
}


export function dump_to_dict(entity: any) {
    const entity_dict = entity.asdict()

    if (entity_dict.type_name) {
        throw new Error('The type_name identifier is used in the serialization and is prohibited.')
    }

    entity_dict.type_name = entity.type_name
    return entity_dict
}


export function dump_as_json(entity: any, ensure_ascii=false, dump_kwargs: any) {
    const entity_dict = dump_to_dict(entity)
    const json_str = JSON.stringify(entity_dict, null, 2)
    return json_str
}

export function load_from_json(json_str: string) {
    const entity_dict = JSON.parse(json_str)
    return load_from_dict(entity_dict)
}


export function load_from_dict<T extends Entity>(entity_dict: any): T {
    const type_name = entity_dict.type_name
    const cls = get_entity_class_by_name(type_name)
    let instance: T

    if (entity_dict.id) {
        let id = entity_dict.id
        instance = new cls(id) as T
    } else {
        instance = new cls() as T
    }

    throw new Error('Not implemented')
    // const leftovers = instance.replace_silent(entity_dict)
    // if (leftovers) {
    //     log.error(`Leftovers while loading entity (id=${entity_dict.id}): ${leftovers}`)
    // }
    return instance
}

export class Entity {
    id: string = get_entity_id()
    // immutability_error_message: string = ''

    constructor(id?: string) {
        this.id = id ?? get_entity_id()
        // this.immutability_error_message = ''
    }

}
