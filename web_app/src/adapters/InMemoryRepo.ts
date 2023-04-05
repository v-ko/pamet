import { Change } from "../fusion_js/Change"

export class InMemoryRepository {
    private entity_cache: { [key: string]: any }
    constructor () {
        this.entity_cache = {}
    }
    insertOne(entity: any) {
        if (entity.id in this.entity_cache) {
            throw new Error(`Entity with id ${entity.id} already exists`)
        }
        this.entity_cache[entity.id] = entity
        return Change
    }
}
