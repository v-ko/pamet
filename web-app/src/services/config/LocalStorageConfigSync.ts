import { isServiceStateId } from '@/model/config/ServiceState';
import { getLogger } from "sivkit/logging";
import { Delta } from "sivkit/model/Delta";
import { Change, ChangeType } from "sivkit/model/Change";
import { Entity, EntityData, SerializedEntityData, dumpToDict, loadFromDict } from "sivkit/model/Entity";
import { StoreSyncServiceBase } from "sivkit/storage/sync/StoreSyncServiceBase";

// Import config entity types to ensure they're registered in the entity library
import "@/model/config/UserSettings";
import "@/model/config/DeviceState";
import "@/model/config/ProjectProperties";

const log = getLogger('LocalStorageConfigSync');

const CONFIG_KEY_PREFIX = 'pamet-config:';

export class LocalStorageConfigSync extends StoreSyncServiceBase {
    private _storageListener: ((event: StorageEvent) => void) | null = null;

    async initialize(): Promise<void> {
        const entities: Entity<EntityData>[] = [];

        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (!key || !key.startsWith(CONFIG_KEY_PREFIX)) continue;
            if (isServiceStateId(key.slice(CONFIG_KEY_PREFIX.length))) continue;

            const raw = localStorage.getItem(key);
            if (!raw) continue;

            try {
                const dict = JSON.parse(raw) as SerializedEntityData;
                entities.push(loadFromDict(dict));
            } catch (e) {
                log.warning(`Failed to load config entity from localStorage key '${key}':`, e);
            }
        }

        if (entities.length > 0) {
            this.store.loadData(entities, 'remote');
        }

        // Listen for cross-tab updates
        this._storageListener = (event: StorageEvent) => {
            if (event.storageArea !== localStorage) return;
            if (!event.key || !event.key.startsWith(CONFIG_KEY_PREFIX)) return;

            const entityId = event.key.slice(CONFIG_KEY_PREFIX.length);
            if (isServiceStateId(entityId)) return;

            if (event.newValue === null) {
                // Key was removed — delete entity from store if it exists
                const existing = this.store.findOne({ id: entityId });
                if (existing) {
                    this.applyRemoteDelta(
                        Delta.fromChanges([Change.delete(existing)])
                    );
                }
            } else {
                try {
                    const dict = JSON.parse(event.newValue) as SerializedEntityData;
                    const entity = loadFromDict(dict);
                    const existing = this.store.findOne({ id: entity.id });
                    const change = existing
                        ? entity.changeFrom(existing)
                        : Change.create(entity);
                    if (!change.isEmpty()) {
                        this.applyRemoteDelta(
                            Delta.fromChanges([change])
                        );
                    }
                } catch (e) {
                    log.warning(`Failed to apply cross-tab config update for key '${event.key}':`, e);
                }
            }
        };
        window.addEventListener('storage', this._storageListener);
    }

    async pushDelta(delta: Delta): Promise<void> {
        for (const change of delta.changes()) {
            if (isServiceStateId(change.entityId)) continue;
            const type = change.type();
            if (type === ChangeType.DELETE) {
                // Reconstruct entity from reverse component to get the id
                const entityId = change.entityId;
                localStorage.removeItem(CONFIG_KEY_PREFIX + entityId);
            } else {
                // CREATE or UPDATE — get the current entity from the store and persist
                const entity = this.store.findOne({ id: change.entityId });
                if (entity) {
                    const dict = dumpToDict(entity);
                    localStorage.setItem(CONFIG_KEY_PREFIX + entity.id, JSON.stringify(dict));
                }
            }
        }
    }

    dispose(): void {
        if (this._storageListener) {
            window.removeEventListener('storage', this._storageListener);
            this._storageListener = null;
        }
    }
}
