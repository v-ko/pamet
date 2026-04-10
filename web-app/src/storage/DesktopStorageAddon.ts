import { getLogger } from 'fusion/logging';
import type { ProjectStorageManager, StorageAddon } from 'fusion/storage/management/ProjectStorageManager';
import { Delta, type DeltaData } from 'fusion/model/Delta';
import { Change } from 'fusion/model/Change';
import { stemFromPath } from '@/model/Page';
import {
    linkUpdatesForPageRename,
    linkUpdatesForPageDelete,
    imageReassignmentUpdatesForPageDelete,
} from '@/model/correctness';
import { buildRestApiAuthHeaders } from 'fusion/storage/rest-api/Auth';
import type { DomainStoreAdapterArgs } from 'fusion/storage/domain-store-adapter/DomainStoreAdapter';

const log = getLogger('DesktopStorageAddon');

/**
 * Desktop-specific addon for PSM.
 *
 * Handles:
 * - Bridge lifecycle (PUT/DELETE to backend)
 * - FS-change polling (fetches /changes/pending)
 * - Reference enrichment before committing polled deltas
 */
export class DesktopStorageAddon implements StorageAddon {
    private _psm: ProjectStorageManager;
    private _polling = false;
    private _baseUrl: string;
    private _projectId: string;
    private _headers: HeadersInit;

    private static readonly POLL_TIMEOUT_MS = 30_000;

    constructor(psm: ProjectStorageManager) {
        this._psm = psm;
        const dsArgs = psm.config.domainStore?.args as DomainStoreAdapterArgs | undefined;
        if (!dsArgs) {
            throw new Error('DesktopStorageAddon requires domainStore config with args');
        }
        this._projectId = dsArgs.projectId;
        this._baseUrl = dsArgs.baseUrl;
        this._headers = buildRestApiAuthHeaders(dsArgs.auth);
    }

    private _projectUrl(path: string): string {
        return `${this._baseUrl}/desktop/projects/${encodeURIComponent(this._projectId)}${path}`;
    }

    // -- Bridge lifecycle --------------------------------------------------

    async onProjectLoading(): Promise<void> {
        const projectUri = this._psm.projectUri;
        if (!projectUri) {
            throw new Error('DesktopStorageAddon requires a project URI (from tracked projects)');
        }
        const response = await fetch(this._projectUrl('/bridge'), {
            method: 'PUT',
            headers: { ...this._headers, 'Content-Type': 'application/json' },
            body: JSON.stringify({ uri: projectUri }),
        });
        if (!response.ok) {
            throw new Error(`Failed to setup bridge (${response.status} ${response.statusText})`);
        }
        log.info('Bridge established for project', this._projectId);
    }

    async onProjectLoaded(): Promise<void> {
        // Check for unexpected pending FS changes from before load
        const pendingDelta = await this._fetchPendingDelta(0);
        if (pendingDelta && Object.keys(pendingDelta).length > 0) {
            log.warning('Unexpected pending FS changes on project load — committing them');
            const enriched = this._updateReferences(pendingDelta);
            const ss = this._psm.parentStorageService;
            if (ss) {
                await ss.commit(this._psm.config.projectId, enriched, 'pending fs changes on load');
            }
        }

        log.info('DesktopStorageAddon: project loaded, starting poll loop');
        this._polling = true;
        void this._pollLoop();
    }

    async onProjectUnloading(): Promise<void> {
        log.info('DesktopStorageAddon: stopping poll loop');
        this._polling = false;

        // Tear down bridge
        const response = await fetch(this._projectUrl('/bridge'), {
            method: 'DELETE',
            headers: this._headers,
        });
        if (!response.ok) {
            log.error(`Failed to discard bridge (${response.status} ${response.statusText})`);
        } else {
            log.info('Bridge discarded for project', this._projectId);
        }
    }

    // -- FS-change polling ------------------------------------------------

    private async _fetchPendingDelta(timeoutMs: number): Promise<DeltaData | null> {
        const url = new URL(this._projectUrl('/changes/pending'));
        url.searchParams.set('timeout_ms', String(timeoutMs));
        const response = await fetch(url, {
            method: 'GET',
            headers: this._headers,
            cache: 'no-store',
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch pending delta (${response.status} ${response.statusText})`);
        }
        const payload = await response.json() as { pendingDelta?: DeltaData | null };
        return payload.pendingDelta ?? null;
    }

    private async _pollLoop(): Promise<void> {
        while (this._polling) {
            try {
                const delta = await this._fetchPendingDelta(
                    DesktopStorageAddon.POLL_TIMEOUT_MS
                );
                if (!this._polling) break;

                if (delta && Object.keys(delta).length > 0) {
                    const enriched = this._updateReferences(delta);
                    const ss = this._psm.parentStorageService;
                    if (!ss) break;
                    await ss.commit(
                        this._psm.config.projectId,
                        enriched,
                        'external filesystem change',
                    );
                }
            } catch (e) {
                if (!this._polling) break;
                log.error('Poll loop error', e);
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
        }
    }

    /**
     * Enrich a raw FS delta with reference updates for page renames/deletes.
     *
     * The TS headStore still holds the pre-delta state, so we can query it
     * to find CardNotes and ImageItems that need updating.
     */
    private _updateReferences(deltaData: DeltaData): DeltaData {
        const delta = new Delta(structuredClone(deltaData));
        const headStore = this._psm.onDeviceRepo.headStore;
        const extraChanges: Change[] = [];

        for (const change of delta.changes()) {
            const fwd = change.forwardComponent as Record<string, any>;
            const rev = change.reverseComponent as Record<string, any>;
            const typeName = fwd.type_name || rev.type_name;

            if (typeName !== 'Page') continue;

            if (change.isUpdate() && 'path' in fwd && 'path' in rev) {
                // Page renamed — update link text and page_ref on matching notes
                const newPath = fwd.path as string;
                const newName = stemFromPath(newPath);
                extraChanges.push(
                    ...linkUpdatesForPageRename(headStore, change.entityId, newName, newPath)
                        .map(u => Change.update(u.original, u.updated))
                );
            } else if (change.isDelete()) {
                // Page deleted — mark linking notes and reassign images
                const pageName = stemFromPath(rev.path as string);
                extraChanges.push(
                    ...linkUpdatesForPageDelete(headStore, change.entityId, pageName)
                        .map(u => Change.update(u.original, u.updated))
                );
                extraChanges.push(
                    ...imageReassignmentUpdatesForPageDelete(headStore, change.entityId)
                        .map(u => Change.update(u.original, u.updated))
                );
            }
        }

        // Merge extra changes into the delta
        for (const c of extraChanges) {
            delta.addChangeFromData(c.data);
        }

        return delta.data;
    }


}
