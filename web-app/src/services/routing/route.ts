import { getLogger } from "fusion/logging";

let log = getLogger('PametRoute');


export const PROJECT_PROTOCOL = 'project:';


export enum PametRoutes {
    ROOT = 'root',
    PROJECT = 'project',
    PAGE = 'page',
    MEDIA = 'media'
}

export class PametRoute {
    // General
    originalPath: string = '';
    protocol?: string = undefined;
    host?: string = undefined;

    // Pamet specific
    userId?: string = undefined;
    projectId?: string = undefined;

    // Page specific
    pageId?: string = undefined;
    viewportCenter?: [number, number] = undefined;
    viewportEyeHeight?: number = undefined;
    focusedNoteId?: string = undefined;

    // Media specific
    mediaItemId?: string = undefined;
    mediaItemContentHash?: string = undefined;

    _parseSubProjectParts(subProjectParts: string[]): void {
        if (subProjectParts[0] == 'page') {
            const pageId = subProjectParts[1];
            this.pageId = pageId;
        } else if (subProjectParts[0] == 'media' && subProjectParts[1] == 'item') {
            // Media item route  like /media/item/{mediaItemId}#{mediaItemContentHash}
            const mediaItemId = subProjectParts[2];
            this.mediaItemId = mediaItemId;
            // Later we can add /media/path/MEDIA_PATH#hash for more readable urls
        }
    }

    static fromUrl(url: string): PametRoute {
        const url_ = new URL(url);
        log.info('Parsing URL:', url);

        // Local urls start with project:///, globals are regular with a host
        let route = new PametRoute();

        if (url_.protocol) {
            route.protocol = url_.protocol
        }
        if (url_.host) {
            route.host = url_.host;
        }

        const path = url_.pathname;
        route.originalPath = path;

        if (url_.protocol === PROJECT_PROTOCOL) {
            route._parseSubProjectParts(path.split('/').slice(1)); // Remove leading slash
        } else if (path) {  // Should be a network protocol htpp/https

            // The user is the first segment if specfied
            const pathParts = path.split('/');  // pathname starts with leading /,

            if (pathParts[1].length > 0) {
                route.userId = pathParts[1];
            }

            // Get the project id from the path
            // Check that there's at least a project id
            if (pathParts.length >= 3) {
                route.projectId = pathParts[2];
            }

            route._parseSubProjectParts(pathParts.slice(3));
        }

        // Parse the search
        const search = url_.search;
        const searchParams = new URLSearchParams(search);
        const eye_at = searchParams.get('eye_at');
        if (eye_at) {
            const [eyeHeight, x, y] = eye_at.split('/').map(parseFloat);
            if (!isNaN(eyeHeight) && !isNaN(x) && !isNaN(y)) {
                route.viewportEyeHeight = eyeHeight;
                route.viewportCenter = [x, y];
            }
        }

        // Parse the hash
        const hash = url_.hash;
        if (hash.startsWith('#note=')) {
            route.focusedNoteId = decodeURIComponent(
                hash.substring(6)); // remove the '#note='
        } else if (route.mediaItemId && hash.length === 33) {
            // If media item id is set, the hash should be the content hash
            route.mediaItemContentHash = decodeURIComponent(hash.substring(1)); // remove the '#'
        }

        log.info('Parsed PametRoute from URL:', route);
        return route;
    }

    get isInternal(): boolean {
        return this.protocol === PROJECT_PROTOCOL;
    }

    projectScopedPath(): string {
        return toProjectScopedPath(this);
    }

    path(): string {
        let path = '/';

        if (this.projectId) {
            if (this.userId === undefined) {
                throw new Error(`Project id set without user id. Got userId: ${this.userId}, projectId: ${this.projectId}`);
            }
            path += `${this.userId}/`;
            path += `${this.projectId}`;
        }

        let projectScopedPath = toProjectScopedPath(this);
        if (projectScopedPath !== '/') {
            path += projectScopedPath;
        }

        return path;
    }

    toProjectScopedURI(): string {
        let path = toProjectScopedPath(this);
        return `project://${path}`;
    }

    toUrlString(): string {
        if (!this.host) {
            throw new Error('Host is not set. Cannot create URL string.');
        }
        if (!this.protocol) {
            throw new Error('Protocol is not set. Cannot create URL string.');
        }
        const url = new URL(this.protocol + '//' + this.host);
        url.pathname = this.path();
        return url.toString();
    }
}

export function toProjectScopedPath(route: PametRoute): string {
    // same as the tuUrlPath logic but for the subpath after project
    let path = '/';

    if (route.pageId && route.pageId.length === 8) {
        path += `page/${encodeURIComponent(route.pageId)}`;
    } else if (route.mediaItemId) {
        // For media items, userId and projectId are required to match cache format
        if (!route.userId || !route.projectId) {
            throw new Error(`Media item routes require userId and projectId. Got userId: ${route.userId}, projectId: ${route.projectId}`);
        }
        path += `media/item/${encodeURIComponent(route.mediaItemId)}`;
        if (route.mediaItemContentHash) {
            path += `#${encodeURIComponent(route.mediaItemContentHash)}`;
        }
        return path; // Return early for media items, no search params or note hash
    }

    let search = '';
    if (route.viewportEyeHeight && route.viewportCenter) {
        search = `?eye_at=${encodeURIComponent(route.viewportEyeHeight.toString())}/${encodeURIComponent(route.viewportCenter[0].toString())}/${encodeURIComponent(route.viewportCenter[1].toString())}`;
    }

    let hash = '';
    if (route.focusedNoteId) {
        hash = `#note=${encodeURIComponent(route.focusedNoteId)}`;
    }

    return path + search + hash;
}

