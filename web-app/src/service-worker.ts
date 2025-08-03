import * as Comlink from 'comlink';
import { StorageServiceActual } from './storage/StorageService';

// DEBUG: Add logging to check entity registration
import { getLogger } from 'fusion/logging';
import { registerEntityClasses } from './core/entityRegistrationHack';

const log = getLogger('service-worker');

declare const self: ServiceWorkerGlobalScope;

// Register entity classes in service worker context
registerEntityClasses();

// Configure the service worker to update immediately and claim clients upon activation
self.addEventListener('install', event => {
    // Skip waiting to activate the service worker immediately
    console.log('Service worker installed');
    event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
    // Claim clients immediately
    console.log('Service worker activated');
    event.waitUntil(self.clients.claim());
});

// //Test - add heartbeat log
// let counter = 0;
// setInterval(() => {
//     console.log('SWHB:', counter++);
// }, 1000);

let storageService = new StorageServiceActual();
storageService.setupMediaRequestInterception();

// Set up broadcast channel for storage updates
let broadcastChannel = new BroadcastChannel('storage-service-proxy-channel');

// Handle MessageChannel connections from main thread
self.addEventListener("message", (event: ExtendableMessageEvent) => {
    console.log('Service worker received message:', event.data);

    // Handle Comlink connection setup
    if (event.data && event.data.type === 'CONNECT_STORAGE') {
        const port = event.ports[0];
        if (port) {
            console.log('Service worker: Setting up Comlink on MessageChannel port');
            // Expose the storage service on this specific port
            Comlink.expose(storageService, port);
            console.log('Service worker: Comlink exposed on port');
        } else {
            console.error('Service worker: No port received in CONNECT_STORAGE message');
        }
        return;
    }

    // Handle other messages (legacy logging)
    console.log('Service worker: Unhandled message type');
});
