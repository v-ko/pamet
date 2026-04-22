/**
 * Stateless Service Worker for web file serving.
 *
 * Serves cached files from Cache API. No in-memory state — the SW can die
 * and restart between any two requests. Cache API persists independently.
 *
 * Desktop mode does NOT register this SW — files are served via direct
 * backend URLs with cookie auth.
 */
import { PametRoute } from "@/services/routing/PametRoute";

declare const self: ServiceWorkerGlobalScope;

self.addEventListener('install', () => { void self.skipWaiting(); });
self.addEventListener('activate', (event) => { event.waitUntil(self.clients.claim()); });

self.addEventListener('fetch', (event) => {
    const route = PametRoute.fromUrl(event.request.url);

    if (!route.filePath || !route.projectId) return; // let browser handle

    event.respondWith((async () => {
        const cache = await caches.open(`pamet-file-${route.projectId}`);
        const match = await cache.match(`files/${route.filePath}`);
        if (match) return match;
        return new Response('File not found', { status: 404 });
    })());
});
