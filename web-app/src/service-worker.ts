import * as Comlink from 'comlink';
import { StorageServiceActual } from './storage/StorageService';

declare const self: ServiceWorkerGlobalScope;

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

// Expose the storage service to the main thread via Comlink and broadcast channel
let broadcastChannel = 

// // // Expose the RepositoryService to the main thread via Comlink
// Comlink.expose(StorageService);// Define a type for the methods you expect to be available from the service worker

// Establish the comlink connection to the wrapper via a MessageChannel
self.addEventListener("message", (event: ExtendableMessageEvent) => {

    // if (event.data.comlinkInit) {
    //   Comlink.expose(StorageService, event.data.port);
    //   console.log('Comlink exposed', event.data.port);
    //   return;
    // }
// test: log received messages
    console.log('Service worker received message:', event.data);
});
