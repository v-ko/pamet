import { Delta } from 'sivkit/model/Delta';
import { Change } from 'sivkit/model/Change';
import { InMemoryStore } from 'sivkit/storage/domain-store/InMemoryStore';
import type { StorageServiceProxy } from 'sivkit/storage/management/StorageServiceProxy';
import { DummyPage } from 'sivkit/storage/test-utils';
import { OptimisticProjectSyncService } from './OptimisticProjectSyncService';
import { pamet } from '@/app/facade';
import { appActions } from '@/actions/app';

jest.mock('@/app/facade', () => ({
    pamet: { appViewState: {}, trackedProjects: jest.fn() },
}));
jest.mock('@/actions/app', () => ({
    appActions: { setSaveStatus: jest.fn() },
}));

test('only lifecycle-rejected saves for removed projects stop retries and unload warnings', async () => {
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
                new InMemoryStore(), { commit } as unknown as StorageServiceProxy, 'p1', 'main',
            );
            const delta = Delta.fromChanges([
                Change.create(new DummyPage({ id: 'page', parent_id: '', name: 'Page' })),
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
                    expect(jest.getTimerCount()).toBe(0);
                    service.trackDelta(delta);
                    expect(service.saveUncommittedChanges('late edit')).toBe(false);
                    await jest.advanceTimersByTimeAsync(10000);
                    expect(commit).toHaveBeenCalledTimes(1);
                } else {
                    expect(appActions.setSaveStatus).toHaveBeenCalledWith(pamet.appViewState, 'error');
                    await jest.advanceTimersByTimeAsync(100);
                    expect(commit).toHaveBeenCalledTimes(2);
                }
            } finally {
                // General detach disposal belongs to the prepare-to-close work.
                const handler = service['_beforeUnloadHandler'];
                if (handler) window.removeEventListener('beforeunload', handler);
                jest.clearAllTimers();
            }
        }
    } finally {
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
    const storage = {
        commit,
        getCommitGraph: jest.fn().mockResolvedValue(emptyGraph),
        getCommits: jest.fn().mockResolvedValue([]),
    } as unknown as StorageServiceProxy;
    const store = new InMemoryStore();
    const service = new OptimisticProjectSyncService(store, storage, 'p1', 'main');
    const firstDelta = Delta.fromChanges([
        Change.create(new DummyPage({ id: 'first', parent_id: '', name: 'First' })),
    ]);
    const secondDelta = Delta.fromChanges([
        Change.create(new DummyPage({ id: 'second', parent_id: '', name: 'Second' })),
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
        expect(commit).toHaveBeenCalledTimes(2);
        expect(commit.mock.calls[1][2]).toBe('second edit');

        resolveFirst({ commit: firstCommit });
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
        await Promise.resolve();

        expect(store.findOne({ id: 'first' })).toBeDefined();
        expect(store.findOne({ id: 'second' })).toBeDefined();
        expect(appActions.setSaveStatus).toHaveBeenLastCalledWith(pamet.appViewState, 'saved');
    } finally {
        const handler = service['_beforeUnloadHandler'];
        if (handler) window.removeEventListener('beforeunload', handler);
        jest.clearAllTimers();
        jest.useRealTimers();
    }
});
