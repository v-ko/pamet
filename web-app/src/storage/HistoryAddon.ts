import { getLogger } from 'sivkit/logging';
import type { ProjectStorageManager, StorageAddon } from 'sivkit/storage/management/ProjectStorageManager';
import type { StorageAddonDescriptor } from 'sivkit/storage/management/StorageService';
import { IndexedDBVcsAdapter } from 'sivkit/storage/repository/IndexedDBVcsAdapter';
import type { DomainStoreAdapterArgs } from 'sivkit/storage/domain-store-adapter/DomainStoreAdapter';
import { buildRestApiAuthHeaders } from 'sivkit/storage/rest-api/Auth';
import { getVcsAdapter } from 'sivkit/storage/repository/Repository';
import type { VcsAdapter } from 'sivkit/storage/repository/VcsAdapter';
import { Commit, type CommitData } from 'sivkit/storage/version-control/Commit';
import { buildHashTree, updateHashTree } from 'sivkit/storage/version-control/HashTree';
import { InMemoryStore } from 'sivkit/storage/domain-store/InMemoryStore';
import { Delta } from 'sivkit/model/Delta';
import { dumpToDict } from 'sivkit/model/Entity';
import { createId } from 'sivkit/util/base';

const log = getLogger('HistoryAddon');

const BRANCH = 'main';
const REPLAY_BATCH = 500;
const RETRY_DELAY_MS = 3000;
const REQUEST_TIMEOUT_MS = 15000;

export type HistoryAddonConfig =
    | { check: 'backend' }
    | { check: 'local', vcsAdapter: 'IndexedDB' | 'InMemory' };

/** Desktop disconnects preserve backend history; offline removal erases its local copy. */
export function historyAddonDescriptor(config: HistoryAddonConfig): StorageAddonDescriptor {
    return {
        name: 'HistoryAddon',
        create: psm => new HistoryAddon(psm, config),
        eraseLocalStorage: config.check === 'local' && config.vcsAdapter === 'IndexedDB'
            ? async storageConfig => {
                // Delete directly: missing history must not be opened or seeded.
                await new IndexedDBVcsAdapter(`${storageConfig.projectId}-history`).eraseStorage();
            }
            : undefined,
    };
}

export interface ReconciliationResult {
    head_id: string;
    mismatches: number;
    hashes_disagree?: boolean;
}

/**
 * Copies every main-branch commit into a separate history store while
 * enabled. Records only while holding the `history-${projectId}` Web Lock.
 */
export class HistoryAddon implements StorageAddon {
    private _psm: ProjectStorageManager;
    private _config: HistoryAddonConfig;
    private _projectId: string;
    private _historyUrl = '';
    private _headers: HeadersInit = {};
    private _adapter: VcsAdapter | null = null;

    private _state: 'off' | 'checking' | 'recording' = 'off';
    // A re-enable requests the next session; it must not cancel the current drain.
    private _recordingRequested = false;
    private _draining = false;
    private _disposed = false;
    private _worker: Promise<void> | null = null;
    private _wakeWorker: (() => void) | null = null;
    private _retryTimer: ReturnType<typeof setTimeout> | null = null;
    private _failureReported = false;
    private _headId = '';
    private _queue: CommitData[] = [];

    constructor(psm: ProjectStorageManager, config: HistoryAddonConfig) {
        this._psm = psm;
        this._config = config;
        this._projectId = psm.config.projectId;
        if (config.check === 'backend') {
            const dsArgs = psm.config.domainStore?.args as DomainStoreAdapterArgs | undefined;
            if (!dsArgs) throw new Error('HistoryAddon backend check requires domainStore args');
            this._historyUrl = `${dsArgs.baseUrl}/desktop/projects/${encodeURIComponent(dsArgs.projectId)}/changes/history`;
            this._headers = { ...buildRestApiAuthHeaders(dsArgs.auth), 'Content-Type': 'application/json' };
        }
    }

    async onProjectLoaded(): Promise<void> { }

    async onProjectUnloading(): Promise<void> {
        this._disposed = true;
        await this._stop();
        // Keep the adapter across disable/re-enable, but never close it while
        // the worker is still acquiring or using it.
        this._adapter?.close();
        this._adapter = null;
    }

    onCommitted(commit: CommitData): void {
        if (!this._recordingRequested || this._disposed || this._draining || this._state === 'off') return;
        this._queue.push(structuredClone(commit));
        this._wakeWorker?.();
    }

    onMessage(message: unknown): unknown {
        const msg = message as { type?: string, enabled?: boolean };
        if (msg.type !== 'setEnabled') throw new Error(`Unknown HistoryAddon message: ${msg.type}`);
        if (this._disposed) return;
        if (!msg.enabled) return this._stop();
        this._recordingRequested = true;
        this._start();
        return undefined;
    }

    get state() {
        return this._state;
    }

    private _report(message: string) {
        log.error(message);
        this._psm.parentStorageService?.reportError(message);
    }

    private _stop(): Promise<void> {
        this._recordingRequested = false;
        this._draining = true;
        if (this._retryTimer !== null) clearTimeout(this._retryTimer);
        this._retryTimer = null;
        this._wakeWorker?.();
        return this._worker ?? Promise.resolve();
    }

    private _start(): void {
        if (this._worker || this._retryTimer !== null || !this._recordingRequested || this._disposed) return;
        this._draining = false;
        let retry = false;
        this._worker = Promise.resolve().then(async () => {
            retry = (await this._runSession()) === 'busy';
        }).catch(error => {
            // An append may have succeeded despite a failed response. Reconcile
            // on the next attempt instead of replaying an uncertain batch.
            this._queue = [];
            retry = true;
            if (!this._failureReported) this._report(`Change history failed: ${error}`);
            this._failureReported = true;
        }).finally(() => {
            this._state = 'off';
            this._worker = null;
            this._wakeWorker = null;
            if (!this._recordingRequested || this._disposed) return;
            if (retry) {
                this._retryTimer = setTimeout(() => {
                    this._retryTimer = null;
                    this._start();
                }, RETRY_DELAY_MS);
            } else {
                // A re-enable received during draining starts only after release.
                this._start();
            }
        });
    }

    private async _runSession(): Promise<'busy' | 'stopped'> {
        // The lock covers reconciliation, recording and the final drain.
        return navigator.locks.request(`history-${this._projectId}`, { ifAvailable: true }, async lock => {
            if (!lock) return 'busy';
            if (this._draining || this._disposed) return 'stopped';

            this._state = 'checking';
            const result = this._config.check === 'backend'
                ? await this._verifyAndReconcileBackend()
                : await this._verifyAndReconcileLocal();
            this._headId = result.head_id;
            if (result.mismatches > 0) {
                this._report(`Change history: hash mismatch in ${result.mismatches} commits`);
            }
            if (result.hashes_disagree) {
                this._report('Change history: hash mismatch between the frontend and the backend');
            }

            this._state = 'recording';
            await this._recordUntilStopped();
            return 'stopped';
        });
    }

    private async _recordUntilStopped(): Promise<void> {
        // Stop accepting commits on disable, but finish those already queued.
        while (this._queue.length || (!this._draining && !this._disposed)) {
            if (this._queue.length) {
                await this._flush();
                continue;
            }

            if (this._failureReported) log.info('Change history recording recovered');
            this._failureReported = false;
            await new Promise<void>(resolve => { this._wakeWorker = resolve; });
            this._wakeWorker = null;
        }
    }

    private async _post<T>(path: string, body: string): Promise<T> {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
        try {
            const response = await fetch(`${this._historyUrl}/${path}`, {
                method: 'POST', headers: this._headers, body, signal: controller.signal,
            });
            if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
            return await response.json() as T;
        } finally {
            clearTimeout(timeout);
        }
    }

    private _underCommitLock<T>(fn: () => Promise<T>): Promise<T> {
        return navigator.locks.request(`storage-commit-${this._projectId}`, fn);
    }

    private async _verifyAndReconcileBackend(): Promise<ReconciliationResult> {
        const repo = this._psm.onDeviceRepo;
        const body = await this._underCommitLock(async () => {
            this._queue = [];
            return JSON.stringify({
                entities: [...repo.headStore.find()].map(e => dumpToDict(e)),
                snapshot_hash: repo.hashTree.rootHash(),
            });
        });
        return this._post<ReconciliationResult>('check', body);
    }

    private async _localAdapter(): Promise<VcsAdapter> {
        if (this._config.check !== 'local') throw new Error('No local history storage');
        this._adapter ??= await getVcsAdapter({
            name: this._config.vcsAdapter,
            args: { projectId: `${this._projectId}-history`, localBranchName: BRANCH },
        });
        return this._adapter;
    }

    private async _verifyAndReconcileLocal(): Promise<ReconciliationResult> {
        const adapter = await this._localAdapter();
        const graph = await adapter.getCommitGraph();
        const metadata = graph.branch(BRANCH) ? graph.branchCommits(BRANCH) : [];

        const store = new InMemoryStore();
        const tree = await buildHashTree(store);
        let mismatches = 0;
        for (let i = 0; i < metadata.length; i += REPLAY_BATCH) {
            const commits = await adapter.getCommits(metadata.slice(i, i + REPLAY_BATCH).map(c => c.id));
            for (const commit of commits) {
                const applied = store.applyDelta(commit.delta);
                await updateHashTree(tree, store, applied);
                if (tree.rootHash() !== commit.snapshotHash) mismatches++;
            }
        }
        const headId = metadata.at(-1)?.id ?? '';

        const repo = this._psm.onDeviceRepo;
        const patch = await this._underCommitLock(async () => {
            this._queue = [];
            const delta = Delta.fromEntities(store.find()).reversed();
            delta.mergeWithPriority(Delta.fromEntities(repo.headStore.find()));
            if (delta.isEmpty()) return null;
            return new Commit({
                id: createId(),
                parent_id: headId,
                snapshot_hash: repo.hashTree.rootHash(),
                timestamp: Date.now(),
                message: 'History patch',
                delta_data: delta.data,
            });
        });
        if (!patch) return { head_id: headId, mismatches };
        await this._appendLocal([patch]);
        log.info('Patched change history with', patch.id);
        return { head_id: patch.id, mismatches };
    }

    private async _appendLocal(commits: Commit[]): Promise<void> {
        const adapter = await this._localAdapter();
        await adapter.applyUpdate({
            addedCommits: commits,
            removedCommits: [],
            updatedCommits: [],
            addedBranches: [],
            updatedBranches: [{ name: BRANCH, head_commit_id: commits.at(-1)!.id }],
            removedBranches: [],
        });
    }

    private async _flush(): Promise<void> {
        const commits = this._queue.splice(0);
        let parent = this._headId;
        for (const commit of commits) {
            commit.parent_id = parent;
            parent = commit.id;
        }
        if (this._config.check === 'backend') {
            await this._post('commits', JSON.stringify({ commits }));
        } else {
            await this._appendLocal(commits.map(c => new Commit(c)));
        }
        this._headId = parent;
    }
}
