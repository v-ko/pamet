import * as Comlink from 'comlink';
import { ProjectStorageManager, ProjectStorageConfig } from './ProjectStorageManager';
import { SerializedStoreData } from 'fusion/storage/BaseStore';
import { Delta, DeltaData } from 'fusion/storage/Delta';
import { getLogger } from "fusion/logging";
import serviceWorkerUrl from "../service-worker?url"
import { RepoUpdateData } from "fusion/storage/BaseRepository"
import { createId } from 'fusion/util';
import { buildHashTree } from 'fusion/storage/HashTree';

let log = getLogger('StorageService')

export type RepoUpdateNotifiedSignature = (update: RepoUpdateData) => void;

export interface StorageServiceActualInterface {
    loadRepo: (projectId: string, repoManagerConfig: ProjectStorageConfig, commitNotify: RepoUpdateNotifiedSignature) => Promise<number>;
    unloadRepo: (subscriptionId: number) => Promise<void>;
    deleteRepo: (projectId: string, projectStorageConfig: ProjectStorageConfig) => Promise<void>;
    headState: (projectId: string) => Promise<SerializedStoreData>;
    _storageOperationRequest: (request: StorageOperationRequest) => Promise<void>;
    test(): void;
}

interface StorageOperationRequest {
    type: string;
}
interface CommitRequest extends StorageOperationRequest {
    projectId: string;
    deltaData: DeltaData;
    message: string;
}
function createCommitRequest(projectId: string, deltaData: DeltaData, message: string): CommitRequest {
    return {
        type: 'commit',
        projectId: projectId,
        deltaData: deltaData,
        message: message
    }
}

export interface LocalStorageUpdateMessage {
    projectId: string
    storageServiceId: string
    update: RepoUpdateData
}

class Subscription {
    id: number;
    projectId: string;
    localStorageUpdateHandler: RepoUpdateNotifiedSignature;

    constructor(projectId: string, subscriptionId: number, localStorageUpdateHandler: RepoUpdateNotifiedSignature) {
        this.projectId = projectId;
        this.id = subscriptionId;
        this.localStorageUpdateHandler = localStorageUpdateHandler;
    }
}

const LOCAL_STORAGE_UPDATE_CHANNEL = 'storage-service-local-storage-update-channel'
const STORAGE_SERVICE_PROXY_CHANNEL = 'storage-service-proxy-channel'

export class StorageService {
    /**
     * This is a wrapper that allows the storage service to be run in either
     * a service worker or the main thread.
     *
     * Commit, squish, merge and other storage operations are wrapped as requests
     * so that they can be executed in request order as to avoid consistency problems
     */
    private _service: StorageServiceActualInterface | null = null;
    _worker: ServiceWorker | null = null;
    _workerRegistration: ServiceWorkerRegistration | null = null;
    _proxyBroadcastChannel: BroadcastChannel | null = null;
    _repoSubscriptions: { [key: string]: number } = {}; // track subs for this instance

    static inMainThread(): StorageService {
        log.info('Creating storage service in main thread')
        let service = new StorageService();
        service._service = new StorageServiceActual();
        return service;
    }

    static async serviceWorkerProxy(): Promise<StorageService> {
        log.info('Creating service worker proxy')
        let service = new StorageService();
        await service._setupProxy();
        return service;
    }

    get service(): StorageServiceActualInterface {
        if (!this._service) {
            throw new Error("Service not initialized");
        }
        return this._service;
    }

    async _getServiceWorker(): Promise<ServiceWorker | null> {
        /**
         * Register the service worker and set the Comlink wrapper up.
         * Reconnect if the service worker changes.
         */
        if (!("serviceWorker" in navigator)) {
            log.warning("Service workers are not supported.");
            return null;
        }

        log.info('Registering service worker ', serviceWorkerUrl)
        let registration: ServiceWorkerRegistration;

        if (!this._workerRegistration) {
            try {
                registration = await navigator.serviceWorker.register(
                    serviceWorkerUrl, { type: "module", scope: "/" })
                this.setWorkerRegistration(registration);
            } catch (error) {
                log.warning(`Service worker registration failed: ${error}`);
                return null;
            }
        }

        await navigator.serviceWorker.ready;
        console.log('After ready')

        const controller = navigator.serviceWorker.controller;
        if (!controller) {
            // A hard reset disables workers. There might be other similar
            // reliability issues, like private browsing, etc
            log.warning("Service worker controller not found.");
            return null;
        }

        return controller;
    }
    async _setupProxy() {
        let controller = await this._getServiceWorker();
        if (!controller) {
            throw new Error("Service worker not available");
        }
        // Create the broadcast channel
        this._proxyBroadcastChannel = new BroadcastChannel(STORAGE_SERVICE_PROXY_CHANNEL);

        // Wrap the worker
        this._worker = controller;
        let service = Comlink.wrap<StorageServiceActualInterface>(this._worker);

        // Confirm the broadcast link
        try {
            await service.test();
        } catch (e) {
            throw Error(`Service worker test failed: ${e}`);
        }

        this._service = service;
        console.log('Remote service initialized', service)
    }

    setWorkerRegistration(registration: ServiceWorkerRegistration) {
        this._workerRegistration = registration;
        if (registration.installing) {
            console.log("Setting registration. State: installing");
        } else if (registration.waiting) {
            console.log("Setting registration. State: installed");
        } else if (registration.active) {
            console.log("Setting registration. State: active");
        }
        console.log("Scope: ", registration.scope);
    }

    // Proxy interface methods
    async loadRepo(projectId: string, projectStorageConfig: ProjectStorageConfig, commitNotify: RepoUpdateNotifiedSignature): Promise<void> {
        log.info('Loading project', projectId)
        let subscriptionId = await this.service.loadRepo(projectId, projectStorageConfig, commitNotify);
        this._repoSubscriptions[projectId] = subscriptionId;
        log.info('Loaded project', projectId)
    }
    async unloadRepo(projectId: string): Promise<void> {
        log.info('Unloading project', projectId)
        let subscriptionId = this._repoSubscriptions[projectId];
        if (subscriptionId === undefined) {
            log.warning('Trying to unload a project that is not loaded:', projectId)
        }
        return this.service.unloadRepo(subscriptionId);
    }
    async deleteProject(projectId: string, projectStorageConfig: ProjectStorageConfig): Promise<void> {
        return this.service.deleteRepo(projectId, projectStorageConfig);
    }
    async _storageOperationRequest(request: StorageOperationRequest): Promise<any> {
        return this.service._storageOperationRequest(request);
    }
    commit(projectId: string, deltaData: DeltaData, message: string) {
        let request = createCommitRequest(projectId, deltaData, message)
        this._storageOperationRequest(request).catch((error) => {
            log.error('Error committing', error)
        })
    }
    headState(projectId: string): Promise<SerializedStoreData> {
        return this.service.headState(projectId);
    }
    async test() {
        return this.service.test();
    }
}

export class StorageServiceActual {
    /**
     * This service provides an interface for the storage management.
     *
     * When the service worker is available - it's run in it and is used via
     * wrappers in all windows/tabs (to save on resources and
     *
     * Normally each tab/window will only load a single project. Those can be
     * different though, so the service should accomodate that with minimal overhead.
     * Therefore it will act on a subscription principle. Each request for loading
     * a repo will constitue a subscription to that repos changes. The first load
     * inits the repo, and the last close(=unsubscribe) closes the repo and frees
     * memory.
     *
     * There's a local repo and at some point - a sync service
     * > The local repo does not issue changes, since it's solely owned by the client.
     * It may be index-db based or device (desktop/mobile) based.
     * > The sync service will push local sync graph changes and notify for remote
     *   sync graph changes.
     *
     */
    id: string = createId(8)
    private repoManagers: { [key: string]: ProjectStorageManager } = {}; // Per projectId
    private subscriptions: { [key: string]: Subscription[] } = {}; // Per projectId
    private _storageOperationBroadcaster: BroadcastChannel;
    private _storageOperationReceiver: BroadcastChannel;
    private _storageOperationQueue: StorageOperationRequest[] = [];

    constructor() {
        this._storageOperationBroadcaster = new BroadcastChannel(LOCAL_STORAGE_UPDATE_CHANNEL);
        this._storageOperationReceiver = new BroadcastChannel(LOCAL_STORAGE_UPDATE_CHANNEL);

        this._storageOperationReceiver.onmessage = (message) => {
            this._onLocalStorageUpdate(message.data);
        };
    }
    get inWorker(): boolean { // Might need to be more specific?
        return typeof self !== 'undefined';
    }

    test() {
        log.info('Test!!!!!!!!!')
    }

    async loadRepo(projectId: string, projectStorageConfig: ProjectStorageConfig, commitNotify: RepoUpdateNotifiedSignature): Promise<number> {
        /**
         * Creates the Repo manager (if not already present), pull()-s
         * subscribes the handler to new commits and returns the head state.
         *
         * Returns a subscription id
         */
        let repoManager = this.repoManagers[projectId];
        if (!repoManager) {
            repoManager = new ProjectStorageManager(this, projectStorageConfig);
            this.repoManagers[projectId] = repoManager;
            await repoManager.init();

            this.subscriptions[projectId] = [];
        } else { // Repo already loaded
            log.info('Repo already loaded', projectId);
            // Check that the configs are the same
            // deep compare the configs
            let configsAreTheSame = JSON.stringify(repoManager.config) === JSON.stringify(projectStorageConfig);
            if (!configsAreTheSame) {
                log.error('Repo already loaded with different config', projectId);
                log.error('Loaded config', repoManager.config);
                log.error('Requested config', projectStorageConfig);
                throw new Error('Repo already loaded with different config');
            }
        }

        // Add a subscription
        let subscription = new Subscription(projectId, this.subscriptions[projectId].length, commitNotify);
        this.subscriptions[projectId].push(subscription);

        return subscription.id
    }

    async unloadRepo(subscriptionId: number): Promise<void> {
        /**
         * Unsubscribes the handler from new commits and unloads the repo if no
         * more subscriptions are present
         */
        let subscription: Subscription | undefined;
        for (let projectId in this.subscriptions) {
            subscription = this.subscriptions[projectId].find(sub => sub.id === subscriptionId);
            if (subscription) {
                break;
            }
        }

        if (!subscription) {
            throw new Error("Subscription not found");
        }

        let repoManager = this.repoManagers[subscription.projectId];
        let projectSubs = this.subscriptions[subscription.projectId];
        let index = projectSubs.indexOf(subscription);
        projectSubs.splice(index, 1);

        if (projectSubs.length === 0) {
            delete this.repoManagers[subscription.projectId];
            delete this.subscriptions[subscription.projectId];
            repoManager.shutdown();
        }
    }
    async deleteRepo(projectId: string, projectStorageConfig: ProjectStorageConfig): Promise<void> {
        // Delete the local storage
        let projectStorageManager = this.repoManagers[projectId];

        // If the repo manager is not loaded - load it temporarily
        let subscriptionId: number | null = null;
        if (projectStorageManager === undefined) {
            log.info('Loading repo temporarily for deletion', projectId);
            subscriptionId = await this.loadRepo(projectId, projectStorageConfig, () => { });
            log.info('Loaded repo temporarily for deletion', projectId);
        }
        projectStorageManager = this.repoManagers[projectId];
        await projectStorageManager.localStorageRepo.eraseStorage();
        log.info('Erased local storage for project', projectId);

        if (subscriptionId !== null) { // Unload tmp repo
            await this.unloadRepo(subscriptionId);
            log.info('Unloaded temporary repo', projectId);
        }
    }

    async _storageOperationRequest(request: StorageOperationRequest): Promise<void> {
        log.info('Storage operation request made', request)
        // This is a wrapper for the actual storage operation
        // It's used to queue operations and execute them in order
        this._storageOperationQueue.push(request);

        // Call queue processing deferred
        setTimeout(() => {
            this.processStorageOperationQueue().catch((error) => {
                log.error('Error processing storage operation queue', error)
            });
        });
    }
    async _exectuteCommitRequest(request: CommitRequest): Promise<void> {
        console.log('Type is commit')
        let commitRequest = request as CommitRequest;
        let projectStorageManager = this.repoManagers[commitRequest.projectId];

        // Commit to in-mem
        let commit = await projectStorageManager.inMemoryRepo.commit(new Delta(commitRequest.deltaData), commitRequest.message);
        console.log('Created commit', commit)

        // Integrity check (TMP)
        let hashTree = await buildHashTree(projectStorageManager.inMemoryRepo.headStore);
        let currentHash = projectStorageManager.inMemoryRepo.hashTree.rootHash();

        if (currentHash !== hashTree.rootHash()) {
            log.error('Hash tree integrity check failed',
                'Current hash:', currentHash,
                'Expected hash:', hashTree.rootHash());
            return;
        }

        // Save in local storage
        log.info('Pulling the new commit from the adapter into the project inMem repo')
        await projectStorageManager.localStorageRepo.pull(projectStorageManager.inMemoryRepo);

        // Notify subscribers
        this.broadcastLocalUpdate({
            projectId: commitRequest.projectId,
            storageServiceId: this.id,
            update: {
                commitGraph: this.repoManagers[commitRequest.projectId].inMemoryRepo.commitGraph.data(),
                newCommits: [commit.data()]
            }
        });
    }
    async _executeStorageOperationRequest(request: StorageOperationRequest): Promise<void> {
        log.info('Executing storage operation request', request)
        if (request.type === 'commit') {
            await this._exectuteCommitRequest(request as CommitRequest);
        } else {
            log.error('Unknown storage operation request', request)
        }
    }

    async processStorageOperationQueue() {
        log.info('Processing storage operation queue')
        for (let request of this._storageOperationQueue) {
            try {
                await this._executeStorageOperationRequest(request);
            } catch (error) {
                log.error('Error processing storage operation request',request , error)
            }
        }
        this._storageOperationQueue = [];
    }

    broadcastLocalUpdate(update: LocalStorageUpdateMessage) {
        log.info('Broadcasting local storage update', update);
        this._storageOperationBroadcaster.postMessage(update);
    }

    _onLocalStorageUpdate(updateMessage: LocalStorageUpdateMessage) {
        log.info('Received local storage update', updateMessage)

        // (Edge case) If there's more than one local storage service
        // (e.g. hard refresh and no service worker) - react on updates by pulling
        if (updateMessage.storageServiceId === this.id) {
            if (updateMessage.projectId in this.repoManagers) {
                let repoManager = this.repoManagers[updateMessage.projectId];
                repoManager.inMemoryRepo.pull(repoManager.localStorageRepo).then(
                    () => {
                        this._notifySubscribers(updateMessage.projectId, updateMessage.update);
                    }
                ).catch((error) => {
                    log.error('Error pulling local storage update', error)
                });
            }
        } else {
            // Notify all subscribers
            this._notifySubscribers(updateMessage.projectId, updateMessage.update);
        }
    }

    _notifySubscribers(projectId: string, update: RepoUpdateData) {
        let subscriptions = this.subscriptions[projectId];
        if (!subscriptions) {
            return;
        }
        for (let subscription of subscriptions) {
            subscription.localStorageUpdateHandler(update);
        }
    }
    async headState(projectId: string): Promise<SerializedStoreData> {
        let repoManager = this.repoManagers[projectId];
        if (!repoManager) {
            throw new Error("Repo not loaded");
        }
        return repoManager.inMemoryRepo.headStore.data();
    }
}
