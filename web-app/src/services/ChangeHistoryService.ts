/**
 * Frontend service that streams user-action deltas to the backend
 * FullChangeHistoryService via a WebSocketSyncService.
 *
 * The frontend acts as **authority** (owns the live store snapshot).
 * The backend acts as **receiver** and commits each delta to a SQLite
 * repository.
 *
 * All communication is fire-and-forget: pushDelta() promises are
 * intentionally not awaited so the UI is never blocked by history
 * persistence.
 */

import { getLogger } from "fusion/logging";
import { Delta } from "fusion/model/Delta";
import { InMemoryStore } from "fusion/storage/domain-store/InMemoryStore";
import { WebSocketSyncService } from "fusion/storage/sync/WebSocketSyncService";

const log = getLogger('ChangeHistoryService');

export class ChangeHistoryService {
    private _syncService: WebSocketSyncService | null = null;
    private _enabled = false;

    get enabled(): boolean {
        return this._enabled;
    }

    /**
     * Enable change history: connect to the backend WS and begin
     * streaming deltas from the given store.
     */
    async enable(store: InMemoryStore, wsUrl: string): Promise<void> {
        if (this._enabled) {
            log.info('ChangeHistoryService already enabled, skipping');
            return;
        }

        const syncService = new WebSocketSyncService({
            role: 'authority',
            url: wsUrl,
        });
        syncService.setStore(store);

        try {
            await syncService.initialize();
            this._syncService = syncService;
            this._enabled = true;
            log.info('ChangeHistoryService enabled');
        } catch (e) {
            log.error('ChangeHistoryService failed to connect', e);
            syncService.dispose();
        }
    }

    /**
     * Disable change history: close the WS connection.
     */
    disable(): void {
        if (!this._enabled) {
            return;
        }
        this._syncService?.dispose();
        this._syncService = null;
        this._enabled = false;
        log.info('ChangeHistoryService disabled');
    }

    /**
     * Push a delta to the backend for commit.  Fire-and-forget — the
     * returned promise is caught internally so the caller is never blocked.
     */
    pushDelta(delta: Delta): void {
        if (!this._enabled || !this._syncService) {
            // TODO: make this check in a proper place
            return;
        }
        if (delta.isEmpty()) {
            return;
        }
        this._syncService.pushDelta(delta).catch((err) => {
            log.error('ChangeHistoryService: failed to push delta', err);
        });
    }
}
