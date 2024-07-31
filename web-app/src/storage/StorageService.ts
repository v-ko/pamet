import * as Comlink from 'comlink';
import { Commit } from "pyfusion/storage/Commit";
import { ProjectStorageManager, ProjectStorageConfig } from './ProjectStorageManager';
import { SerializedStoreData } from 'pyfusion/storage/BaseStore';
import { Delta, DeltaData } from 'pyfusion/storage/Delta';
import { getLogger } from "pyfusion/logging";
import serviceWorkerUrl from "../service-worker?url"
import { RepoUpdate } from '../../../fusion/js-src/src/storage/BaseRepository';
import { createId } from 'pyfusion/util';

let log = getLogger('StorageService')

export type RepoUpdateNotifiedSignature = (update: RepoUpdate) => void;

// export interface RepoLoadResponce { // This is needed, so that
//     subscriptionId: number;
//     headState: SerializedStoreData;
// }

export interface StorageServiceActualInterface {
    loadRepo: (projectId: string, repoManagerConfig: ProjectStorageConfig, commitNotify: RepoUpdateNotifiedSignature) => Promise<number>;
    unloadRepo: (subscriptionId: number) => Promise<void>;
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
    update: RepoUpdate
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
    // private _reconnectSet: boolean = false;
    _worker: ServiceWorker | null = null;
    _workerRegistration: ServiceWorkerRegistration | null = null;
    _proxyBroadcastChannel: BroadcastChannel | null = null;
    _repoSubscriptions: { [key: string]: number } = {}; // track subs for this instance

    static inMainThread(): StorageService {
        let service = new StorageService();
        service._service = new StorageServiceActual();
        return service;
    }

    static async serviceWorkerProxy(): Promise<StorageService> {
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
        } catch (error) {
            throw Error("Service worker test failed");
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
    async loadProject(projectId: string, projectStorageConfig: ProjectStorageConfig, commitNotify: RepoUpdateNotifiedSignature): Promise<void> {
        let subscriptionId = await this.service.loadRepo(projectId, projectStorageConfig, commitNotify);
        this._repoSubscriptions[projectId] = subscriptionId;
    }
    async unloadProject(projectId: string): Promise<void> {
        let subscriptionId = this._repoSubscriptions[projectId];
        if (!subscriptionId) {
            log.warning('Tryging to unload a project that is not loaded')
        }
        return this.service.unloadRepo(subscriptionId);
    }
    async _storageOperationRequest(request: StorageOperationRequest): Promise<any> {
        return this.service._storageOperationRequest(request);
    }
    commit(projectId: string, deltaData: DeltaData, message: string) {
        let request = createCommitRequest(projectId, deltaData, message)
        this._storageOperationRequest(request);
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
    private _localUpdateChannel: BroadcastChannel = new BroadcastChannel(LOCAL_STORAGE_UPDATE_CHANNEL)
    private _storageOperationQueue: StorageOperationRequest[] = [];

    constructor() {
        this._localUpdateChannel.addEventListener('message', (message) => {
            this._onLocalStorageUpdate(message.data)
        })
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
        log.info('Loading repo', projectId);
        let repoManager = this.repoManagers[projectId];
        if (!repoManager) {
            repoManager = new ProjectStorageManager(this, projectStorageConfig);
            this.repoManagers[projectId] = repoManager;
            await repoManager.init();

            this.subscriptions[projectId] = [];
        } else { // Repo already loaded
            // Check that the configs are the same
            if (repoManager.config !== projectStorageConfig) {
                throw new Error("Repo already loaded with different config");
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

        // let repoManager = this.repoManagers[subscription.projectId];
        let projectSubs = this.subscriptions[subscription.projectId];
        let index = projectSubs.indexOf(subscription);
        projectSubs.splice(index, 1);

        if (projectSubs.length === 0) {
            delete this.repoManagers[subscription.projectId];
            delete this.subscriptions[subscription.projectId];
            // await repoManager.close();
        }
    }
    async _storageOperationRequest(request: StorageOperationRequest): Promise<void> {
        log.info('Storage operation request made', request)
        // This is a wrapper for the actual storage operation
        // It's used to queue operations and execute them in order
        this._storageOperationQueue.push(request);

        // Call queue processing deferred
        setTimeout(() => {
            this.processStorageOperationQueue();
        });
    }
    async _executeStorageOperationRequest(request: StorageOperationRequest): Promise<void> {
        log.info('Executing storage operation request', request)
        if (request.type === 'commit') {
            console.log('Type is commit')
            let commitRequest = request as CommitRequest;
            let projectStorageManager = this.repoManagers[commitRequest.projectId];

            // Commit to in-mem
            let commit = await projectStorageManager.inMemoryRepo.commit(new Delta(commitRequest.deltaData), commitRequest.message);
            console.log('Created commit', commit)
            // Save in local storage
            await projectStorageManager.localStorageRepo.pull(projectStorageManager.inMemoryRepo);

            // Notify subscribers
            this.broadcastLocalUpdate({
                projectId: commitRequest.projectId,
                storageServiceId: this.id,
                update: {
                    commitGraph: this.repoManagers[commitRequest.projectId].inMemoryRepo.commitGraph.data(),
                    newCommits: [commit.data()]
                }
            })
        }
    }

    async processStorageOperationQueue() {
        log.info('Processing storage operation queue')
        for (let request of this._storageOperationQueue) {
            try {
                await this._executeStorageOperationRequest(request);
            } catch (error) {
                log.error('Error processing storage operation request', error)
            }
        }
        this._storageOperationQueue = [];
    }

    broadcastLocalUpdate(update: LocalStorageUpdateMessage) {
        log.info('Broadcasting local storage update', update)
        this._localUpdateChannel.postMessage(update)
    }

    _onLocalStorageUpdate(updateMessage: LocalStorageUpdateMessage) {
        log.info('Received local storage update', updateMessage)
        // (Edge case) If there's more than one local storage service
        // (e.g. hard refresh and no service worker) - react on updates by pulling
        if (updateMessage.storageServiceId === this.id) {
            if (updateMessage.projectId in this.repoManagers) {
                let repoManager = this.repoManagers[updateMessage.projectId];
                repoManager.inMemoryRepo.pull(repoManager.localStorageRepo)
            }
        }

        // Notify all subscribers
        this._notifySubscribers(updateMessage.projectId, updateMessage.update);
    }

    _notifySubscribers(projectId: string, update: RepoUpdate) {
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

