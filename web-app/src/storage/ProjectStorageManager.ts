import { BaseAsyncRepository } from "fusion/storage/BaseRepository";
import { IndexedDBRepository } from "./IndexedDB_storageAdapter";
import { StorageServiceActual } from "./StorageService";
import { AsyncInMemoryRepository } from "fusion/storage/AsyncInMemoryRepo";
import { getLogger } from "fusion/logging";
import { autoMergeForSync } from "fusion/storage/SyncUtils";
import { DesktopServerRepository } from "./DesktopServerRepository";
import { ApiClient } from "./ApiClient";

let log = getLogger('ProjectStorageManager');

export interface ProjectStorageConfig {
    currentBranchName: string;
    localRepoConfig: StorageAdapterConfig;
    // WebRTC repo config
    // Cloud repo config
}

export type StorageAdapterNames = "IndexedDB" | "InMemory" | "DesktopServer";

export interface StorageAdapterArgs {
    projectId: string;
    defaultBranchName: string;
}

export interface StorageAdapterConfig {
    name: StorageAdapterNames
    args: StorageAdapterArgs;
}

async function initStorageAdapter(config: StorageAdapterConfig): Promise<BaseAsyncRepository> {
    let repo: BaseAsyncRepository;

    switch (config.name) {
        case "IndexedDB": {
            let idbRepoArgs = config.args;
            let indexedDB_repo = new IndexedDBRepository(idbRepoArgs.projectId, idbRepoArgs.defaultBranchName);
            await indexedDB_repo.connectOrInit()
            repo = indexedDB_repo  // For TS type annotation purposes
            break;
        }
        case "InMemory": { // For testing purposes
            let inMemRepo = new AsyncInMemoryRepository();
            await inMemRepo.init(config.args.defaultBranchName)
            repo = inMemRepo
            break;
        }
        case "DesktopServer": {
            let apiClient = new ApiClient("http://localhost", 11352);
            let desktopRepo = new DesktopServerRepository(apiClient);
            await desktopRepo.init();
            repo = desktopRepo
            break;
        }
        default: {
            throw new Error(`Unknown storage adapter name: ${config.name}`)
        }
    }

    return repo
}


export class ProjectStorageManager {
    /**
     * A class to manage the storage adapters and sync graph operations for a
     * repository (of a project).
     *
     * Each project needs storage. A client will always have a local storage
     * adapter to keep offline state (indexdb or device (desktop/mobile)).
     *
     * To allow for inter-device-sync or collab/sharing we apply new commits from
     * each device to their own branch (like in git). The resulting graph is the
     * "sync graph" (since it's used for state synchronization).
     * The synchronization process consists of communicating sync graph changes -
     * e.g. through yjs/webrtc or other means we convey changes in a CRDT-like
     * manner, where the order of update arrival does not matter.
     * The other operations on the graph (squishing, merging) are applied by
     * each client to their own branch, which allows for the above properties of
     * sync graph updates (arrival order irrelevance, ..?). Merge-conflicts
     * (where two clients commit at the same time on the same data) are resolved
     * deterministically by seniority. I.e. the junior node always adapts first,
     * and the senior node adopts only commits made on top of its own branch head.
     */
    private _storageService: StorageServiceActual; // Parent
    private _config: ProjectStorageConfig;
    private _inMemRepo: AsyncInMemoryRepository | null = null;
    _localStorageRepo: BaseAsyncRepository | null = null;

    constructor(storageService: StorageServiceActual, config: ProjectStorageConfig) {
        this._storageService = storageService
        this._config = config
    }
    get inMemoryRepo() {
        if (!this._inMemRepo) {
            throw new Error("In-mem repo not set. Have you called init?")
        }
        return this._inMemRepo
    }
    get localStorageRepo() {
        if (!this._localStorageRepo) {
            throw new Error("Local storage repo not set. Have you called init?")
        }
        return this._localStorageRepo
    }
    get storageService() {
        return this._storageService
    }
    get config(): ProjectStorageConfig {
        return this._config
    }
    get currentBranchName() {
        return this.config.currentBranchName
    }
    async init() {
        log.info('Initializing project storage manager for branch', this.currentBranchName)
        // Setup the in-mem storage
        const branchName = this.config.currentBranchName

        // Setup the local storage adapter
        try {
            this._localStorageRepo = await initStorageAdapter(this.config.localRepoConfig)

        } catch (e) {
            console.error("Error in initializing storage adapter", e)
        }
        // Check that there's a device branch with the id supplied in the config
        // and create one if not
        let localGraph = await this.localStorageRepo.getCommitGraph()

        if (!localGraph.branch(branchName)) {
            // If the branch does not exist -
            // create branch in local adapter, pull, merge, push
            log.info('Device branch missing in the local storage. Creating it:', branchName)
            await this.localStorageRepo.createBranch(branchName)
        }
        this._inMemRepo = await AsyncInMemoryRepository.initFromRemote(this.localStorageRepo, branchName)
        await autoMergeForSync(this.inMemoryRepo, branchName)
        await this.localStorageRepo.pull(this.inMemoryRepo)

        // Populate the in-mem repo with the local storage data
        await this._inMemRepo.pull(this.localStorageRepo)
    }

    shutdown() {
        // Close the storage manager
        log.info('Closing project storage manager')
        if (this._localStorageRepo) {
            this._localStorageRepo.shutdown()
        }
    }

    async eraseLocalStorage() {
        // Erase the local storage
        if (this._localStorageRepo) {
            await this._localStorageRepo.eraseStorage()
        } else {
            log.warning('Local storage not initialized. Nothing to erase.')
        }
    }
}
