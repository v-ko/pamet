import { Repository, SearchFilter } from "./BaseRepository"
import { Entity, EntityData } from "../libs/Entity"
import { Change } from "../Change"
import { getLogger } from "../logging"

const log = getLogger('InMemoryRepository')


export class InMemoryRepository extends Repository {
    private entity_cache: { [key: string]: any }

    constructor () {
        super()
        this.entity_cache = {}
    }
    upsertToCache(entity: Entity<EntityData>) {
        this.entity_cache[entity.id] = entity
    }
    popFromCache(id: string): Entity<EntityData> | undefined {
        let entity = this.entity_cache[id]
        delete this.entity_cache[id]
        return entity
    }
    insertOne(entity: Entity<EntityData>): Change {
        if (entity.id in this.entity_cache) {
            throw new Error(`Entity with id ${entity.id} already exists`)
        }
        this.entity_cache[entity.id] = entity
        return Change.create(entity)
    }
    updateOne(entity: Entity<EntityData>): Change {
        let oldEntity = this.popFromCache(entity.id)
        if (!oldEntity) {
            throw new Error(`Entity with id ${entity.id} does not exist`)
    }
        this.entity_cache[entity.id] = entity
        return Change.update(oldEntity, entity)
    }
    removeOne(entity: Entity<EntityData>): Change {
        let oldEntity = this.popFromCache(entity.id)
        if (!oldEntity) {
            throw new Error(`Entity with id ${entity.id} does not exist`)
        }
        return Change.delete(oldEntity)
    }

    *find<T extends Entity<EntityData>>(filter: SearchFilter = {}): Generator<T> {
        // TODO: Optimize this
        for (let entity_id in this.entity_cache) {
            let entity = this.entity_cache[entity_id]
            if (filter.id && entity.id !== filter.id) {
                continue
            }
            if (filter.type && entity.constructor !== filter.type) {
                continue
            }
            if (filter.parentId && entity.parentId !== filter.parentId) {
                continue
            }
            if (filter) {
                let match = true
                for (let key in filter) {
                    if (key === 'type') continue; // Skip the 'type' property
                    if (key === 'id') continue; // Skip the 'id' property
                    if (key === 'parentId') continue; // Skip the 'parentId' property
                    if (entity[key] !== filter[key]) {
                        match = false
                        break
                    }
                }
                if (!match) {
                    continue
                }
            }
            yield entity
        }
    }
    findOne<T extends Entity<EntityData>>(filter: SearchFilter): T | undefined {
        let generator = this.find<T>(filter);
        let result = generator.next();
        if (result.done) {
            return undefined;
        }
        return result.value;
    }
}
