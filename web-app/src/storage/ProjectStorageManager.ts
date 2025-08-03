import { BaseAsyncRepository } from "fusion/storage/BaseRepository";
import { IndexedDBRepository } from "./IndexedDB_storageAdapter";
import { StorageServiceActual } from "./StorageService";
import { AsyncInMemoryRepository } from "fusion/storage/AsyncInMemoryRepo";
import { getLogger } from "fusion/logging";
import { autoMergeForSync } from "fusion/storage/SyncUtils";
import { DesktopServerRepository } from "./DesktopServerRepository";
import { ApiClient } from "./ApiClient";
import { MediaStoreAdapter } from "./MediaStoreAdapter";
import { InMemoryMediaStoreAdapter } from "./InMemoryMediaStoreAdapter";
import { CacheMediaStoreAdapter } from "./CacheMediaStoreAdapter";

let log = getLogger('ProjectStorageManager');

export interface ProjectStorageConfig {
    currentBranchName: string;
    localRepo: StorageAdapterConfig;  // IndexedDB, DesktopServer, Cloud (for thin clients), InMemory for testing
    localMediaStore: MediaStoreConfig;  // CacheAPI, DesktopServer, Cloud (for thin clients), InMemory for testing
    // remoteRepo: StorageAdapterConfig; // WebRTC, Cloud (for full clients)
    // remoteMediaStore: MediaStoreConfig; // WebRTC, Cloud (for full clients)
}

export type StorageAdapterNames = "InMemory" | "IndexedDB" | "DesktopServer";

export interface StorageAdapterArgs {
    projectId: string;
    localBranchName: string;
}

export interface StorageAdapterConfig {
    name: StorageAdapterNames
    args: StorageAdapterArgs;
}

export interface MediaStoreConfig {
    name: MediaStoreAdapterNames;
    args: MediaStoreAdapterArgs;
}

export interface MediaStoreAdapterArgs {
    projectId: string;
}

export type MediaStoreAdapterNames = "InMemory" | "CacheAPI" | "DesktopServer";

async function initStorageAdapter(config: StorageAdapterConfig): Promise<BaseAsyncRepository> {
    let repo: BaseAsyncRepository;

    switch (config.name) {
        case "IndexedDB": {
            let idbRepoArgs = config.args;
            let indexedDB_repo = new IndexedDBRepository(idbRepoArgs.projectId, idbRepoArgs.localBranchName);
            await indexedDB_repo.connectOrInit()
            repo = indexedDB_repo  // For TS type annotation purposes
            break;
        }
        case "InMemory": { // For testing purposes
            let inMemRepo = new AsyncInMemoryRepository();
            await inMemRepo.init(config.args.localBranchName)
            repo = inMemRepo
            break;
        }
        case "DesktopServer": {
            let desktopApiClient = new ApiClient("http://localhost", 11352);
            let desktopRepo = new DesktopServerRepository(desktopApiClient);
            await desktopRepo.init(config.args.localBranchName);
            repo = desktopRepo
            break;
        }
        default: {
            throw new Error(`Unknown storage adapter name: ${config.name}`)
        }
    }

    return repo
}

async function initMediaStore(config: MediaStoreConfig): Promise<MediaStoreAdapter> {
    let mediaStore: MediaStoreAdapter;

    switch (config.name) {
        case "InMemory": {
            let inMemMediaStore = new InMemoryMediaStoreAdapter();
            mediaStore = inMemMediaStore
            break;
        }
        case "CacheAPI": {
            let cacheMediaStore = new CacheMediaStoreAdapter(config.args.projectId);
            await cacheMediaStore.init();
            log.info('Initialized CacheMediaStoreAdapter for project', config.args.projectId);
            mediaStore = cacheMediaStore
            break;
        }
        case "DesktopServer": {
            throw new Error("DesktopServer not implemented yet")
        }
        default: {
            throw new Error(`Unknown media store name: ${config.name}`)
        }
    }

    return mediaStore
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
    _localRepo: BaseAsyncRepository | null = null;
    private _localMediaStore: MediaStoreAdapter | null = null;

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
        if (!this._localRepo) {
            throw new Error("Local storage repo not set. Have you called init?")
        }
        return this._localRepo
    }
    get mediaStore() {
        if (!this._localMediaStore) {
            throw new Error("Media store not set. Have you called init?")
        }
        return this._localMediaStore
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
            log.info('Initializing storage adapter:', this.config.localRepo.name)
            this._localRepo = await initStorageAdapter(this.config.localRepo)
            log.info('Storage adapter initialized successfully')

        } catch (e) {
            log.error("Error in initializing storage adapter", e)
            throw e; // Re-throw to prevent partial initialization
        }

        try {
            // Check that there's a device branch with the id supplied in the config
            // and create one if not
            log.info('Getting commit graph from local storage')
            let localGraph = await this.localStorageRepo.getCommitGraph()

            if (!localGraph.branch(branchName)) {
                // If the branch does not exist -
                // create branch in local adapter, pull, merge, push
                log.info('Device branch missing in the local storage. Creating it:', branchName)
                await this.localStorageRepo.createBranch(branchName)
            }

            log.info('Initializing in-memory repository from remote')
            this._inMemRepo = await AsyncInMemoryRepository.initFromRemote(this.localStorageRepo, branchName)
            log.info('In-memory repository initialized successfully')

            log.info('Performing auto-merge for sync')
            await autoMergeForSync(this.inMemoryRepo, branchName)

            log.info('Pulling from in-memory repo to local storage')
            await this.localStorageRepo.pull(this.inMemoryRepo)

            // Populate the in-mem repo with the local storage data
            log.info('Pulling from local storage to in-memory repo')
            await this._inMemRepo.pull(this.localStorageRepo)

            // Initialize the media store
            log.info('Initializing media store:', this.config.localMediaStore.name)
            this._localMediaStore = await initMediaStore(this.config.localMediaStore)
            log.info('Media store initialized successfully')

            log.info('Project storage manager initialization completed successfully')
        } catch (e) {
            log.error("Error during project storage manager initialization", e)
            // Clean up partial state
            this._inMemRepo = null;
            this._localRepo = null;
            this._localMediaStore = null;
            throw e;
        }
    }

    shutdown() {
        // Close the storage manager
        log.info('Closing project storage manager')
        if (this._localRepo) {
            this._localRepo.shutdown()
        }
    }

    async eraseLocalStorage() {
        // Erase the local storage
        if (this._localRepo) {
            await this._localRepo.eraseStorage()
        } else {
            log.warning('Local storage not initialized. Nothing to erase.')
        }
    }
}
