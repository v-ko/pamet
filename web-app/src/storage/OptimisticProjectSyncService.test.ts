import { AppViewState } from '@/views/AppViewState';
import { Delta } from 'sivkit/model/Delta';
import { Change } from 'sivkit/model/Change';
import { InMemoryStore } from 'sivkit/storage/domain-store/InMemoryStore';
import { StorageServiceProxy } from 'sivkit/storage/management/StorageServiceProxy';
import { Page } from '@/model/Page';
import { OptimisticProjectSyncService } from './OptimisticProjectSyncService';
import { pamet } from '@/app/facade';
import { appActions } from '@/actions/app';

jest.mock('@/app/facade', () => ({
    pamet: { appViewState: {}, trackedProjects: jest.fn(), projectStorageState: jest.fn() },
}));
jest.mock('@/actions/app', () => ({
    appActions: {
        setSaveStatus: jest.fn((state, status) => { state.storageState.saveStatus = status; }),
        setSaveError: jest.fn((state, message) => { state.storageState.saveError = message; }),
    },
}));

// jsdom lacks structuredClone; delta data is plain JSON.
globalThis.structuredClone ??= value => JSON.parse(JSON.stringify(value));

const pageEntity = (id: string) => new Page({
    id, parent_id: '', path: `${id}.canvas.html`, created: '', modified: '',
});

beforeEach(() => {
    Object.assign(pamet, { appViewState: new AppViewState({ userId: 'test' }) });
    (pamet.projectStorageState as jest.Mock).mockReturnValue(null);
    jest.clearAllMocks();
});

const proxies: StorageServiceProxy[] = [];
function storageProxy(methods: object): StorageServiceProxy {
    const proxy = Object.assign(new StorageServiceProxy(), methods);
    proxies.push(proxy);
    return proxy;
}
afterEach(() => {
    for (const proxy of proxies.splice(0)) proxy.disconnect();
});

test('save failures do not retry and retain unload warnings unless the project was removed', async () => {
    jest.useFakeTimers();
    try {
        for (const scenario of [
            { removed: false, name: 'ProjectStorageLifecycleError', discard: false },
            { removed: true, name: 'Error', discard: false },
            { removed: true, name: 'ProjectStorageLifecycleError', discard: true },
        ]) {
            jest.clearAllMocks();
            (pamet.trackedProjects as jest.Mock).mockReturnValue(scenario.removed ? [] : [{ id: 'p1' }]);
            const error = Object.assign(new Error('save failed'), { name: scenario.name });
            const commit = jest.fn().mockRejectedValue(error);
            const service = new OptimisticProjectSyncService(
                new InMemoryStore(), storageProxy({ commit }), 'p1', 'main',
            );
            const delta = Delta.fromChanges([
                Change.create(pageEntity('page')),
            ]);
            try {
                service.trackDelta(delta);
                service.saveUncommittedChanges('edit');
                await jest.advanceTimersByTimeAsync(100);
                expect(commit).toHaveBeenCalledTimes(1);
                const beforeUnload = new Event('beforeunload', { cancelable: true });
                window.dispatchEvent(beforeUnload);
                expect(beforeUnload.defaultPrevented).toBe(!scenario.discard);

                if (scenario.discard) {
                    expect(appActions.setSaveStatus).not.toHaveBeenCalledWith(pamet.appViewState, 'error');
                    service.trackDelta(delta);
                    expect(service.saveUncommittedChanges('late edit')).toBe(false);
                    await jest.advanceTimersByTimeAsync(10000);
                    expect(commit).toHaveBeenCalledTimes(1);
                } else {
                    expect(appActions.setSaveStatus).toHaveBeenCalledWith(pamet.appViewState, 'error');
                    await jest.advanceTimersByTimeAsync(20000);
                    expect(commit).toHaveBeenCalledTimes(1);
                    expect(await service.flushAndDispose()).toBe('failed');
                }
            } finally {
                await service.flushAndDispose();
                jest.clearAllTimers();
            }
        }
    } finally {
        jest.useRealTimers();
    }
});

test('closing delivers the pending save, or gives up and disposes', async () => {
    jest.useFakeTimers();
    const page = (id: string) => Delta.fromChanges([
        Change.create(pageEntity(id)),
    ]);
    const saved = (delta: Delta) => ({ commit: { delta_data: delta.data } });
    const logError = jest.spyOn(console, 'error').mockImplementation(() => {});
    try {
        for (const outcome of ['completed', 'failed', 'timed out'] as const) {
            jest.clearAllMocks();
            (pamet.trackedProjects as jest.Mock).mockReturnValue([{ id: 'p1' }]);
            const first = page('first'), second = page('second');
            let finishFirst!: (value: unknown) => void;
            const secondResult = {
                'completed': () => Promise.resolve(saved(second)),
                'failed': () => Promise.reject(new Error('save failed')),
                'timed out': () => new Promise(() => {}),
            }[outcome];
            const commit = jest.fn()
                .mockImplementationOnce(() => new Promise(resolve => { finishFirst = resolve; }))
                .mockImplementationOnce(secondResult);
            const service = new OptimisticProjectSyncService(
                new InMemoryStore(), storageProxy({ commit }), 'p1', 'main',
            );

            // A save is in flight and a newer edit is not staged yet.
            service.trackDelta(first);
            service.saveUncommittedChanges('first');
            await jest.advanceTimersByTimeAsync(100);
            service.trackDelta(second);
            let settled = false;
            const closing = service.flushAndDispose().finally(() => { settled = true; });
            service.trackDelta(page('ignored'));
            await jest.advanceTimersByTimeAsync(0);
            expect(commit).toHaveBeenCalledTimes(1);
            expect(settled).toBe(false);

            // The edit is sent once the earlier request ends, without a repo update.
            finishFirst(saved(first));
            await jest.advanceTimersByTimeAsync(5000);
            expect(await closing).toBe(outcome);
            expect(commit).toHaveBeenCalledTimes(2);
            expect(commit.mock.calls[1][1]).toEqual(second.data);
            expect(appActions.setSaveStatus).toHaveBeenLastCalledWith(
                pamet.appViewState, outcome === 'completed' ? 'saved' : 'error',
            );

            // Disposed either way: no retry and no unload warning.
            const beforeUnload = new Event('beforeunload', { cancelable: true });
            window.dispatchEvent(beforeUnload);
            expect(beforeUnload.defaultPrevented).toBe(false);
        }
    } finally {
        logError.mockRestore();
        jest.useRealTimers();
    }
});

test('serializes commits and preserves newer local edits during reconciliation', async () => {
    jest.useFakeTimers();
    const emptyGraph = { branches: [{ name: 'main', head_commit_id: null }], commits: [] };
    let resolveFirst!: (value: any) => void;
    let resolveSecond!: (value: any) => void;
    const commit = jest.fn()
        .mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve; }))
        .mockImplementationOnce(() => new Promise(resolve => { resolveSecond = resolve; }));
    const storage = storageProxy({
        commit,
        getCommitGraph: jest.fn().mockResolvedValue(emptyGraph),
        getCommits: jest.fn().mockResolvedValue([]),
    });
    const store = new InMemoryStore();
    const service = new OptimisticProjectSyncService(store, storage, 'p1', 'main');
    const firstDelta = Delta.fromChanges([
        Change.create(pageEntity('first')),
    ]);
    const secondDelta = Delta.fromChanges([
        Change.create(pageEntity('second')),
    ]);

    try {
        await service.initialize();
        store.applyDelta(firstDelta, 'local');
        service.trackDelta(firstDelta);
        service.saveUncommittedChanges('first edit');
        await jest.advanceTimersByTimeAsync(100);
        expect(commit).toHaveBeenCalledTimes(1);

        store.applyDelta(secondDelta, 'local');
        service.trackDelta(secondDelta);
        service.saveUncommittedChanges('second edit');
        await jest.advanceTimersByTimeAsync(100);
        expect(commit).toHaveBeenCalledTimes(1);

        const firstCommit = {
            id: 'c1', parent_id: '', message: 'first edit', timestamp: 1,
            snapshot_hash: 'h1', delta_data: firstDelta.data,
        };
        service.receiveRepoUpdate({
            commitGraph: {
                branches: [{ name: 'main', head_commit_id: 'c1' }],
                commits: [{ id: 'c1', parent_id: '', message: 'first edit', timestamp: 1, snapshot_hash: 'h1' }],
            },
            upsertedCommits: [firstCommit],
        });
        expect(commit).toHaveBeenCalledTimes(1);
        expect(appActions.setSaveStatus).not.toHaveBeenLastCalledWith(pamet.appViewState, 'saved');
        await jest.advanceTimersByTimeAsync(10000);
        expect(commit).toHaveBeenCalledTimes(1);
        expect(appActions.setSaveStatus).toHaveBeenLastCalledWith(pamet.appViewState, 'saving');

        resolveFirst({ commit: firstCommit });
        await jest.advanceTimersByTimeAsync(0);
        expect(commit).toHaveBeenCalledTimes(2);
        expect(commit.mock.calls[1][2]).toBe('second edit');
        resolveSecond({ commit: {
            id: 'c2', parent_id: 'c1', message: 'second edit', timestamp: 2,
            snapshot_hash: 'h2', delta_data: secondDelta.data,
        } });
        service.receiveRepoUpdate({
            commitGraph: {
                branches: [{ name: 'main', head_commit_id: 'c2' }],
                commits: [
                    { id: 'c1', parent_id: '', message: 'first edit', timestamp: 1, snapshot_hash: 'h1' },
                    { id: 'c2', parent_id: 'c1', message: 'second edit', timestamp: 2, snapshot_hash: 'h2' },
                ],
            },
            upsertedCommits: [{
                id: 'c2', parent_id: 'c1', message: 'second edit', timestamp: 2,
                snapshot_hash: 'h2', delta_data: secondDelta.data,
            }],
        });
        await jest.advanceTimersByTimeAsync(0);

        expect(store.findOne({ id: 'first' })).toBeDefined();
        expect(store.findOne({ id: 'second' })).toBeDefined();
        expect(appActions.setSaveStatus).toHaveBeenLastCalledWith(pamet.appViewState, 'saved');
    } finally {
        await service.flushAndDispose();
        jest.clearAllTimers();
        jest.useRealTimers();
    }
});
