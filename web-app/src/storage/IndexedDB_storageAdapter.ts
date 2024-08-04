import { getLogger } from "fusion/logging";
import { BaseAsyncRepository, BranchMetadata } from "fusion/storage/BaseRepository";
import { Commit, CommitData } from "fusion/storage/Commit";
import { openDB, DBSchema, IDBPDatabase } from 'idb';
import { DeltaData } from "fusion/storage/Delta";
import { inferRepoChangesFromGraphUpdate } from "fusion/storage/SyncUtils";
import { CommitGraph } from "fusion/storage/CommitGraph";


let log = getLogger('IndexedDB_storageAdapter');


interface RepoDB extends DBSchema {
    branches: {
        key: string;
        value: BranchMetadata;
        indexes: { 'by-name': string };
    };
    commits: {
        key: string;
        value: CommitData;
        indexes: { 'by-id': string };
    };
    deltas: {
        key: string;
        value: { commitId: string, delta: DeltaData };
        indexes: { 'by-commitId': string };
    };
}

export class IndexedDBRepository extends BaseAsyncRepository {
    private _db: IDBPDatabase<RepoDB> | null = null;
    private _currentBranch: string | null = null;
    private _localBranchName: string;

    constructor(localBranchName: string) {
        super();
        this._localBranchName = localBranchName;
        log.info('Creating IndexedDBRepository for branch:', localBranchName)
    }

    async init(localBranchName: string) {
        if (!this._db) {
            await this._initDB();
        } else {
            throw new Error('IndexedDB already initialized');
        }

        this._currentBranch = localBranchName;
        // Pull the commit graph. If the branch does not exist - create it
        let commitGraph = await this.getCommitGraph();
        let currentBranch = commitGraph.branch(localBranchName);
        if (!currentBranch) {
            // Create the branch
            log.info('Creating a new branch', localBranchName)
            await this.createBranch(localBranchName);
        }
    }

    get db(): IDBPDatabase<RepoDB> {
        if (!this._db) {
            throw new Error('IndexedDB not open');
        }
        return this._db;
    }

    async _initDB() {
        let dbName = 'repoStore-' + this._localBranchName;
        this._db = await openDB<RepoDB>(dbName, 1, {
            upgrade(db) {
                let branchesStore = db.createObjectStore('branches', { keyPath: 'name' });
                let commitsStore = db.createObjectStore('commits', { keyPath: 'id' });
                let deltasStore = db.createObjectStore('deltas', { keyPath: 'commitId' });

                branchesStore.createIndex('by-name', 'name');
                commitsStore.createIndex('by-id', 'id');
                deltasStore.createIndex('by-commitId', 'commitId');
            },
        });

        if (!this._db) {
            log.error('Failed to open IndexedDB');
        }
    }

    get currentBranch() {
        if (!this._currentBranch) {
            throw new Error("Current branch is null. Repo not initialized")
        }
        return this._currentBranch
    }
    async getCommitGraph(): Promise<CommitGraph> {
        try {
            const tx = this.db.transaction(['branches', 'commits'], 'readonly');
            const branchesStore = tx.objectStore('branches');
            const commitsStore = tx.objectStore('commits');

            // Retrieve all branches and commits, handle each request potentially failing
            const branchesPromise = branchesStore.getAll();
            const commitsPromise = commitsStore.getAll();

            const [branches, commits] = await Promise.all([branchesPromise, commitsPromise]);

            // Await transaction completion to catch any errors post data fetching
            await tx.done;

            return CommitGraph.fromData({
                branches: branches,
                commits: commits
            });
        } catch (error: any) { // Typing as DOMException if you're specifically handling those types of errors
            log.error('Failed to retrieve commit graph: ' + error.message);
            throw new Error('Failed to retrieve commit graph due to database error');
        }
    }


    // async getCommits(ids?: string[]): Promise<Commit[]> {
    //     if (!ids || ids.length === 0) {
    //         return []
    //     }

    //     const tx = this.db.transaction(['commits', 'deltas'], 'readonly');
    //     const commitsStore = tx.objectStore('commits');
    //     const deltasStore = tx.objectStore('deltas');

    //     const commits = [];

    //     for (const id of ids) {
    //         const commitData = await commitsStore.get(id);
    //         if (commitData) {
    //             const delta = await deltasStore.get(commitData.id);
    //             if (delta) {
    //                 commitData.deltaData = delta.delta;
    //                 commits.push(new Commit(commitData));
    //             } else {
    //                 log.error('Delta not found for commit ' + commitData.id);  // Handle the case where no delta is found
    //             }
    //         } else {
    //             log.error('Commit not found for ID ' + id);  // Handle the case where no commit is found
    //         }
    //     }

    //     await tx.done;  // Ensure the transaction completes

    //     if (commits.length === 0) {
    //         throw new Error('No commits found for the provided IDs');
    //     }

    //     return commits;
    // }

    async getCommits(ids?: string[]): Promise<Commit[]> {
        if (!ids || ids.length === 0) {
            return [];
        }

        try {
            const tx = this.db.transaction(['commits', 'deltas'], 'readonly');
            const commitsStore = tx.objectStore('commits');
            const deltasStore = tx.objectStore('deltas');

            const commits: Commit[] = [];

            for (const id of ids) {
                try {
                    const commitData = await commitsStore.get(id);
                    if (commitData) {
                        const delta = await deltasStore.get(commitData.id);
                        if (delta) {
                            commitData.deltaData = delta.delta;
                            commits.push(new Commit(commitData));
                        } else {
                            log.error('Delta not found for commit ' + commitData.id);
                        }
                    } else {
                        log.error('Commit not found for ID ' + id);
                    }
                } catch (requestError: any) { // You can use 'any' or 'unknown' here, then narrow with an instanceof check if necessary
                    log.error('Error handling commit or delta request: ' + requestError.message);
                    // Optionally check if (requestError instanceof DOMException) for more specific handling
                }
            }

            await tx.done;
            if (commits.length === 0) {
                throw new Error('No commits found for the provided IDs');
            }

            return commits;
        } catch (txError: any) {
            log.error('Transaction failed: ' + txError.message);
            throw txError; // Rethrow or handle transaction error as per application need
        }
    }



    async commit(deltaData: any, message: string): Promise<Commit> {
        throw new Error('IndexedDB adapter can\'t produce commits.');
    }

    async createBranch(branchName: string): Promise<void> {
        // Check that it's not already there
        const tx = this.db.transaction('branches', 'readwrite');
        const branchesStore = tx.objectStore('branches');

        const branch = await branchesStore.get(branchName);
        if (branch) {
            throw new Error('Branch already exists');
        }

        await branchesStore.add({
            name: branchName,
            headCommitId: null
        });

        await tx.done;
    }

    async reset(filter: { relativeToHead: number }): Promise<void> {
        throw new Error('Indexeddb repo does not implement the `reset` method.');
    }

    async _checkAndApplyUpdate(remoteGraph: CommitGraph, newCommits: Commit[]) {
        // Since we'll update the commit graph to the received one - we need to
        // ensure that the changes are rational, remove unneeded commits, and
        // fetch the new ones
        const localGraph = await this.getCommitGraph()

        let repoChanges = inferRepoChangesFromGraphUpdate(localGraph, remoteGraph, newCommits)
        let {
            addedCommits,
            removedCommits,
            addedBranches,
            updatedBranches,
            removedBranches
        } = repoChanges

        // Start applying the changes
        const tx = this.db.transaction(['branches', 'commits', 'deltas'], 'readwrite');
        const branchesStore = tx.objectStore('branches');
        const commitsStore = tx.objectStore('commits');
        const deltasStore = tx.objectStore('deltas');

        // Remove redundant commits
        for (let commit of removedCommits) {
            await commitsStore.delete(commit.id);
            await deltasStore.delete(commit.id);
        }

        // Add new commits
        for (let commit of addedCommits) {
            log.info('Adding commit', commit)
            await commitsStore.add(commit);
            if (!commit.deltaData) {
                throw new Error('Delta data missing for commit ' + commit.id);
            }
            await deltasStore.add({ commitId: commit.id, delta: commit.deltaData });
        }

        // Update branches
        for (let branch of updatedBranches) {
            await branchesStore.put(branch);
        }

        // Add new branches
        for (let branch of addedBranches) {
            await branchesStore.add(branch);
        }

        // Remove branches
        for (let branch of removedBranches) {
            await branchesStore.delete(branch.name);
        }

        await tx.done;
    }
}
