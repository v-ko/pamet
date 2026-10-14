/** @jest-environment node */
import { Change } from 'sivkit/model/Change';
import { Delta } from 'sivkit/model/Delta';
import { InMemoryStore } from 'sivkit/storage/domain-store/InMemoryStore';
import type { ProjectStorageManager, ProjectStorageConfig } from 'sivkit/storage/management/ProjectStorageManager';
import { StorageService } from 'sivkit/storage/management/StorageService';
import { IndexedDBVcsAdapter } from 'sivkit/storage/repository/IndexedDBVcsAdapter';
import { clearInMemoryAdapterInstances } from 'sivkit/storage/repository/Repository';
import { clearChannels } from 'sivkit/registries/Channel';
import type { CommitData } from 'sivkit/storage/version-control/Commit';
import { buildHashTree, updateHashTree, type HashTree } from 'sivkit/storage/version-control/HashTree';
import { DummyPage } from 'sivkit/storage/test-utils';
import { createId } from 'sivkit/util/base';
import { HistoryAddon, historyAddonDescriptor } from '@/storage/HistoryAddon';
import { DesktopStorageAddon } from '@/storage/DesktopStorageAddon';

// FIFO exclusive locks, including the history writer's nonblocking acquisition.
{
    type LockCallback = (lock: Lock | null) => unknown;
    const queues = new Map<string, Promise<void>>();
    const locks = {
        request: async (
            name: string,
            optionsOrCallback: LockOptions | LockCallback,
            callback?: LockCallback,
        ) => {
            const onAcquired = typeof optionsOrCallback === 'function' ? optionsOrCallback : callback!;
            const previous = queues.get(name);
            if (previous && typeof optionsOrCallback !== 'function' && optionsOrCallback.ifAvailable) {
                return onAcquired(null);
            }
            let release!: () => void;
            const current = new Promise<void>(resolve => { release = resolve; });
            queues.set(name, current);
            await previous;
            try {
                return await onAcquired({ name, mode: 'exclusive' });
            } finally {
                if (queues.get(name) === current) queues.delete(name);
                release();
            }
        },
    };
    if (typeof globalThis.navigator === 'undefined') {
        (globalThis as any).navigator = { locks };
    } else {
        Object.defineProperty(globalThis.navigator, 'locks', { value: locks, configurable: true });
    }
}

async function waitFor(cond: () => boolean) {
    for (let i = 0; i < 500 && !cond(); i++) await new Promise(r => setTimeout(r, 0));
    expect(cond()).toBe(true);
}

function page(name: string) {
    return new DummyPage({ id: createId(), parent_id: '', name });
}

function signal() {
    let resolve!: () => void;
    const promise = new Promise<void>(r => { resolve = r; });
    return { promise, resolve };
}

afterEach(() => {
    jest.restoreAllMocks();
    clearChannels();
    clearInMemoryAdapterInstances();
});

test('HistoryAddon seeds history, copies commits and patches edits missed while disabled', async () => {
    const headStore = new InMemoryStore();
    headStore.insertOne(page('first'));
    const repo: { headStore: InMemoryStore, hashTree: HashTree } = {
        headStore, hashTree: await buildHashTree(headStore),
    };
    const reportError = jest.fn();
    const psm = {
        config: { projectId: 'p1' },
        onDeviceRepo: repo,
        parentStorageService: { reportError },
    } as unknown as ProjectStorageManager;
    const addon = new HistoryAddon(psm, { check: 'local', vcsAdapter: 'InMemory' });
    const history = async () => {
        const adapter = addon['_adapter']!;
        const ids = (await adapter.getCommitGraph()).branchCommits('main').map(c => c.id);
        return await adapter.getCommits(ids);
    };
    const idle = () => waitFor(() =>
        addon.state === 'recording' && addon['_wakeWorker'] !== null && addon['_queue'].length === 0
    );

    // Advance the project as a normal save would, then return its commit.
    async function commit(name: string): Promise<CommitData> {
        const delta = headStore.applyDelta(Delta.fromChanges([Change.create(page(name))]));
        await updateHashTree(repo.hashTree, headStore, delta);
        return {
            id: createId(), parent_id: 'main-parent', message: name, timestamp: 0,
            snapshot_hash: repo.hashTree.rootHash(), delta_data: delta.data,
        };
    }

    // Empty history: patched to the main state
    addon.onMessage({ type: 'setEnabled', enabled: true });
    await idle();
    let commits = await history();
    expect(commits.map(c => c.message)).toEqual(['History patch']);
    expect(commits[0].snapshotHash).toBe(repo.hashTree.rootHash());

    // Copy a saved commit onto the history chain, leaving its original parent alone.
    const saved = await commit('second');
    addon.onCommitted(saved);
    await idle();
    commits = await history();
    expect(commits.map(c => c.parentId)).toEqual(['', commits[0].id]);
    expect(commits[1].data()).toEqual({ ...saved, parent_id: commits[0].id });
    expect(saved.parent_id).toBe('main-parent');

    // An edit made while disabled is recovered as a patch on re-enable.
    addon.onMessage({ type: 'setEnabled', enabled: false });
    const missed = await commit('missed');
    addon.onCommitted(missed);
    expect(await history()).toHaveLength(2);
    addon.onMessage({ type: 'setEnabled', enabled: true });
    await idle();
    commits = await history();
    expect(commits).toHaveLength(3);
    expect(commits[2].message).toBe('History patch');
    expect(Object.keys(commits[2].deltaData)).toEqual(Object.keys(missed.delta_data));
    expect(commits[2].snapshotHash).toBe(repo.hashTree.rootHash());
    expect(reportError).not.toHaveBeenCalled();

    await addon.onProjectUnloading();
});

test('desktop history drains an accepted append before the bridge disconnects', async () => {
    const appending = signal(), finish = signal();
    const order: string[] = [];
    let copied: CommitData[] = [];
    const fetchMock = jest.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
        const path = String(url);
        if (path.endsWith('/changes/stream')) {
            return new Promise<Response>((_, reject) => {
                init!.signal!.addEventListener('abort', () => reject(new Error('stream aborted')), { once: true });
            });
        }
        if (path.endsWith('/bridge')) {
            order.push(init!.method === 'DELETE' ? 'bridge closed' : 'bridge opened');
        } else if (path.endsWith('/entities')) {
            return new Response(JSON.stringify({ entities: [] }));
        } else if (path.endsWith('/history/check')) {
            return new Response(JSON.stringify({ head_id: '', mismatches: 0 }));
        } else if (path.endsWith('/history/commits')) {
            copied = JSON.parse(init!.body as string).commits;
            appending.resolve();
            await finish.promise;
            order.push('history appended');
        } else if (!path.endsWith('/changes')) {
            throw new Error(`Unexpected request ${path}`);
        }
        return new Response('{}');
    });
    const config: ProjectStorageConfig = {
        projectId: 'desktop-lifecycle', deviceBranchName: 'main',
        onDeviceVcsAdapter: { name: 'InMemorySingletonForTesting', args: { projectId: 'desktop-lifecycle', localBranchName: 'main' } },
        onDeviceFileStore: { name: 'InMemory', args: { projectId: 'desktop-lifecycle' } },
        domainStore: { name: 'RestApi', args: {
            projectId: 'desktop-lifecycle', baseUrl: 'http://desktop.test', auth: { type: 'Bearer', token: 'test' },
        } },
    };
    let addon!: HistoryAddon;
    const service = new StorageService([
        { name: 'DesktopStorageAddon', create: psm => new DesktopStorageAddon(psm) },
        { name: 'HistoryAddon', create: psm => (addon = new HistoryAddon(psm, { check: 'backend' })) },
    ]);
    try {
        await service.loadProject(config.projectId, config, 'file:///test-project');
        await service.sendToAddon(config.projectId, 'HistoryAddon', { type: 'setEnabled', enabled: true });
        await waitFor(() => addon.state === 'recording' && addon['_wakeWorker'] !== null);
        const saved = await service.commit(config.projectId, Delta.fromChanges([Change.create(page('saved'))]).data, 'save');
        await appending.promise;
        const unloading = service.unloadProject(config.projectId);
        await waitFor(() => addon['_disposed']);
        expect(order).toEqual(['bridge opened']);
        finish.resolve();
        await unloading;
        expect(order).toEqual(['bridge opened', 'history appended', 'bridge closed']);
        expect(copied).toEqual([{ ...saved.commit, parent_id: '' }]);
        expect(addon.state).toBe('off');
    } finally {
        finish.resolve();
        await service.unloadProject(config.projectId);
        service.disconnect();
        fetchMock.mockRestore();
    }
});

test('local history erasure targets its IndexedDB store without opening it; backend history is preserved', async () => {
    const config: ProjectStorageConfig = {
        projectId: 'local-lifecycle', deviceBranchName: 'main',
        onDeviceVcsAdapter: { name: 'InMemorySingletonForTesting', args: { projectId: 'local-lifecycle', localBranchName: 'main' } },
        onDeviceFileStore: { name: 'InMemory', args: { projectId: 'local-lifecycle' } },
    };
    const initialize = jest.spyOn(IndexedDBVcsAdapter.prototype, 'initialize');
    const erase = jest.spyOn(IndexedDBVcsAdapter.prototype, 'eraseStorage').mockImplementation(async function () {
        return;
    });
    const descriptor = historyAddonDescriptor({ check: 'local', vcsAdapter: 'IndexedDB' });
    await descriptor.eraseLocalStorage!(config);
    expect(erase).toHaveBeenCalledTimes(1);
    expect(erase.mock.instances[0]).toMatchObject({ _projectId: 'local-lifecycle-history' });
    expect(initialize).not.toHaveBeenCalled();
    expect(historyAddonDescriptor({ check: 'backend' }).eraseLocalStorage).toBeUndefined();
});
