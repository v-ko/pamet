import { WebAppState } from "../../containers/app/App";

export const PROJECT_PROTOCOL = 'project:';


export enum PametRoutes {
    ROOT = 'root',
    PROJECT = 'project',
    PAGE = 'page',
    MEDIA = 'media'
}

export class PametRoute {
    protocol?: string = undefined;
    userId?: string = undefined;
    projectId?: string = undefined;
    pageId?: string = undefined;
    viewportCenter?: [number, number] = undefined;
    viewportEyeHeight?: number = undefined;
    focusedNoteId?: string = undefined;
    originalPath: string = '';

    static fromUrl(url: string): PametRoute {
        const url_ = new URL(url);
        const path = url_.pathname;
        const search = url_.search;
        const hash = url_.hash;

        let route = new PametRoute();

        // Local urls start with project:///, globals are regular with a host
        route.protocol = url_.protocol
        route.originalPath = path;
        let subProjectPath: string;
        if (url_.protocol === PROJECT_PROTOCOL) {
            subProjectPath = path;
        } else {
            // Get the user (first part) if any. If it's 'local' there's no registration
            const pathParts = path.split('/');
            let subUserPath: string;
            if (pathParts.length >= 2) {
                if (pathParts[1] === 'local') {
                    route.userId = pathParts[1];
                }
                subUserPath = pathParts.slice(2).join('/');
            } else {
                subUserPath = '';
            }

            // Get the project id from the path
            // Check that there's at least a project id and it's 8 characters long
            if (pathParts.length >= 3) {
                route.projectId = pathParts[2];
                subProjectPath = pathParts.slice(3).join('/');
            } else {
                subProjectPath = '';
            }

        }

        // Get the page id if any
        if (subProjectPath.startsWith('/page/')) {
            const pageId = subProjectPath.substring(6);
            route.pageId = pageId;
        }

        // Parse the search
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
        if (hash.startsWith('#note=')) {
            route.focusedNoteId = decodeURIComponent(
                hash.substring(6)); // remove the '#note='
        }

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

        // For internal paths. This should probably be fixed at some point
        if (this.isInternal) {
            return this.originalPath
        }

        let userId = this.userId;
        if (!this.userId) {
            userId = 'local';
        }
        path += `${userId}/`;

        if (this.projectId) {
            path += `${this.projectId}`;
        }

        let projectScopedPath = toProjectScopedPath(this);
        if (projectScopedPath !== '/') {
            path += projectScopedPath;
        }

        return path;
    }

    toLocalUrl(): string {
        let path = toProjectScopedPath(this);
        return `project://${path}`;
    }

    toUrl(host: string): string {
        // If the host is not in the format schema://host - add the schema
        if (!host.indexOf('://')) {
            host = `https://${host}`;
        }
        let url = new URL(host);
        url.pathname = this.path();
        return url.toString();
    }
}

export function toProjectScopedPath(route: PametRoute): string {
    // same as the tuUrlPath logic but for the subpath after project
    let path = '/';

    if (route.pageId && route.pageId.length === 8) {
        path += `page/${encodeURIComponent(route.pageId)}`;
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

export function routeFromAppState(state: WebAppState): PametRoute {
    let route = new PametRoute();
    let projectId = state.currentProjectId;
    let pageId = state.currentPageId;

    if (projectId === null && pageId !== null) {
        throw new Error('Page id set without project id. Removing page id.');
    }

    if (projectId) {
        route.projectId = projectId;
    }
    if (pageId) {
        route.pageId = pageId;
    }

    return route;
}
