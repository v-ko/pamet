/** @jest-environment node */
import { Change } from 'sivkit/model/Change';
import { Delta } from 'sivkit/model/Delta';
import { InMemoryStore } from 'sivkit/storage/domain-store/InMemoryStore';
import type { ProjectStorageManager } from 'sivkit/storage/management/ProjectStorageManager';
import type { CommitData } from 'sivkit/storage/version-control/Commit';
import { buildHashTree, updateHashTree, type HashTree } from 'sivkit/storage/version-control/HashTree';
import { DummyPage } from 'sivkit/storage/test-utils';
import { createId } from 'sivkit/util/base';
import { HistoryAddon } from '@/storage/HistoryAddon';

// This scenario has no contention: grant each lock and await its callback.
{
    const locks = {
        request: async (
            name: string,
            optionsOrCallback: LockOptions | LockGrantedCallback,
            callback?: LockGrantedCallback,
        ) => {
            const onAcquired = typeof optionsOrCallback === 'function' ? optionsOrCallback : callback!;
            return await onAcquired({ name, mode: 'exclusive' });
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
    const idle = () => waitFor(() => addon.state === 'recording' && !addon['_sending']);

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
