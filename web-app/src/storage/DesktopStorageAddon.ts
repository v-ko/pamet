import { getLogger } from 'fusion/logging';
import type { ProjectStorageManager, StorageAddon } from 'fusion/storage/management/ProjectStorageManager';
import { Delta, type DeltaData } from 'fusion/model/Delta';
import { Change } from 'fusion/model/Change';
import { stemFromPath } from '@/model/Page';
import {
    linkUpdatesForPageRename,
    linkUpdatesForPageDelete,
} from '@/model/correctness';
import { buildRestApiAuthHeaders } from 'fusion/storage/rest-api/Auth';
import type { DomainStoreAdapterArgs } from 'fusion/storage/domain-store-adapter/DomainStoreAdapter';

const log = getLogger('DesktopStorageAddon');

/**
 * Desktop-specific addon for PSM.
 *
 * Handles:
 * - Bridge lifecycle (PUT/DELETE to backend)
 * - FS-change streaming via SSE (fetches /changes/stream)
 * - Reference enrichment before committing streamed deltas
 */
export class DesktopStorageAddon implements StorageAddon {
    private _psm: ProjectStorageManager;
    private _baseUrl: string;
    private _projectId: string;
    private _headers: HeadersInit;
    private _abortController: AbortController | null = null;

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
        log.info('DesktopStorageAddon: project loaded, starting SSE stream');
        this._abortController = new AbortController();
        void this._connectStream();
    }

    async onProjectUnloading(): Promise<void> {
        log.info('DesktopStorageAddon: stopping SSE stream');
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }

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

    // -- FS-change SSE stream ----------------------------------------------

    private async _connectStream(): Promise<void> {
        while (this._abortController && !this._abortController.signal.aborted) {
            try {
                await this._streamOnce();
            } catch (e) {
                if (!this._abortController || this._abortController.signal.aborted) break;
                log.error('DesktopStorageAddon: stream error', e);
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
        }
    }

    private async _streamOnce(): Promise<void> {
        const response = await fetch(this._projectUrl('/changes/stream'), {
            method: 'GET',
            headers: this._headers,
            cache: 'no-store',
            signal: this._abortController!.signal,
        });

        if (!response.ok) {
            throw new Error(`SSE connect failed (${response.status} ${response.statusText})`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop()!;

                for (const part of parts) {
                    if (!part.trim()) continue;
                    const data = this._parseSSEData(part);
                    if (!data) continue;

                    const deltaData = JSON.parse(data) as DeltaData;
                    if (deltaData && Object.keys(deltaData).length > 0) {
                        const enriched = this._updateReferences(deltaData);
                        const ss = this._psm.parentStorageService;
                        if (!ss) return;
                        await ss.commit(
                            this._psm.config.projectId,
                            enriched,
                            'external filesystem change',
                        );
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    private _parseSSEData(raw: string): string | null {
        let data = '';
        for (const line of raw.split('\n')) {
            if (line.startsWith('data: ')) data += line.slice(6);
        }
        return data || null;
    }

    /**
     * Enrich a raw FS delta with reference updates for page renames/deletes.
     *
     * The TS headStore still holds the pre-delta state, so we can query it
     * to find CardNotes that need updating.
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
                // Page deleted — mark linking notes
                const pageName = stemFromPath(rev.path as string);
                extraChanges.push(
                    ...linkUpdatesForPageDelete(headStore, change.entityId, pageName)
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
