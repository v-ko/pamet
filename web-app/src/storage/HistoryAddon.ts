import { getLogger } from 'sivkit/logging';
import type { ProjectStorageManager, StorageAddon } from 'sivkit/storage/management/ProjectStorageManager';
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

export type HistoryAddonConfig =
    | { check: 'backend' }
    | { check: 'local', vcsAdapter: 'IndexedDB' | 'InMemory' };

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
    // Bumped on every enable/disable/re-check; stale results are dropped.
    private _generation = 0;
    private _headId = '';
    private _queue: CommitData[] = [];
    private _sending = false;
    private _releaseWriterLock: (() => void) | null = null;
    private _writerLock: Promise<unknown> = Promise.resolve();

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
        this._stop();
        this._adapter?.close();
        this._adapter = null;
    }

    onCommitted(commit: CommitData): void {
        if (this._state === 'off') return;
        this._queue.push(structuredClone(commit));
        if (this._state === 'recording') void this._flush();
    }

    onMessage(message: unknown): unknown {
        const msg = message as { type?: string, enabled?: boolean };
        if (msg.type !== 'setEnabled') throw new Error(`Unknown HistoryAddon message: ${msg.type}`);
        if (!msg.enabled) {
            this._stop();
        } else if (this._state === 'off') {
            void this._start();
        }
        return undefined;
    }

    get state() {
        return this._state;
    }

    private _report(message: string) {
        log.error(message);
        this._psm.parentStorageService?.reportError(message);
    }

    private _stop() {
        this._generation++;
        this._state = 'off';
        this._queue = [];
        this._releaseWriterLock?.();
        this._releaseWriterLock = null;
    }

    private async _start(): Promise<void> {
        const gen = ++this._generation;
        this._state = 'checking';
        // Let a previous enable release the lock first
        await this._writerLock;
        if (gen !== this._generation) return;

        let resolveAcquired!: (acquired: boolean) => void;
        const acquired = new Promise<boolean>(resolve => { resolveAcquired = resolve; });
        this._writerLock = navigator.locks.request(`history-${this._projectId}`, { ifAvailable: true }, lock => {
            resolveAcquired(lock !== null);
            if (!lock || gen !== this._generation) return;
            return new Promise<void>(release => { this._releaseWriterLock = release; });
        });
        if (!await acquired) {
            if (gen === this._generation) {
                this._state = 'off';
                this._report('Change history is being recorded by an older version of Pamet open in another tab. Reload all Pamet tabs to record here.');
            }
            return;
        }
        if (gen !== this._generation) return;
        await this._verifyAndReconcile(gen);
    }

    private async _verifyAndReconcile(gen: number): Promise<void> {
        try {
            const result = this._config.check === 'backend'
                ? await this._verifyAndReconcileBackend()
                : await this._verifyAndReconcileLocal();
            if (gen !== this._generation) return;
            this._headId = result.head_id;
            if (result.mismatches > 0) {
                this._report(`Change history: hash mismatch in ${result.mismatches} commits`);
            }
            if (result.hashes_disagree) {
                this._report('Change history: hash mismatch between the frontend and the backend');
            }
            this._state = 'recording';
            void this._flush();
        } catch (e) {
            if (gen !== this._generation) return;
            this._report(`Change history reconciliation failed, recording stopped: ${e}`);
            this._stop();
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
        const response = await fetch(`${this._historyUrl}/check`, {
            method: 'POST', headers: this._headers, body,
        });
        if (!response.ok) throw new Error(`reconciliation failed (${response.status} ${await response.text()})`);
        return await response.json() as ReconciliationResult;
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
        if (this._sending || this._state !== 'recording' || this._queue.length === 0) return;
        const gen = this._generation;
        this._sending = true;
        const commits = this._queue.splice(0);
        let parent = this._headId;
        for (const commit of commits) {
            commit.parent_id = parent;
            parent = commit.id;
        }
        try {
            if (this._config.check === 'backend') {
                const response = await fetch(`${this._historyUrl}/commits`, {
                    method: 'POST', headers: this._headers, body: JSON.stringify({ commits }),
                });
                if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
            } else {
                await this._appendLocal(commits.map(c => new Commit(c)));
            }
            if (gen === this._generation) this._headId = parent;
        } catch (e) {
            if (gen === this._generation) {
                this._report(`Change history append failed, reconciling: ${e}`);
                const reconciliationGeneration = ++this._generation;
                this._state = 'checking';
                this._queue = [];
                void this._verifyAndReconcile(reconciliationGeneration);
            }
        } finally {
            this._sending = false;
            void this._flush();
        }
    }
}
