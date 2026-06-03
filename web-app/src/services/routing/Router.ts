import { getLogger } from "sivkit/logging";
import { PametRoute } from "@/services/routing/PametRoute";

const log = getLogger('RoutingService');


interface LastPageSnapshot {
    pageId: string;
    viewportCenter?: [number, number];
    viewportEyeHeight?: number;
}

export type RouteUpdateHandler = (route: PametRoute) => void;

export class Router {
    private popstateHandler: ((e: PopStateEvent) => void) | null = null;
    private _updateHandler: RouteUpdateHandler | null = null;

    // Toggle state machine
    private atToggledRoute: 'none' | 'back' | 'forward' = 'none';
    private suppressToggleTrackingOnce = false;

    // Throttling for replace URL updates
    private lastReplaceAt = 0;
    private replaceCooldownMs = 500;
    private pendingReplaceTimer: number | null = null;
    private pendingReplaceRoute: PametRoute | null = null;

    // Tracking for toggle
    private lastSyncedRoute: PametRoute | null = null;
    private lastPageByProject: Map<string, LastPageSnapshot> = new Map();

    // --- Public API -----------------------------------------------------------

    currentRoute(): PametRoute {
        return PametRoute.fromUrl(window.location.href);
    }

    setUpdateHandler(handler: RouteUpdateHandler): void {
        this._updateHandler = handler;
    }

    init(): void {
        if (this.popstateHandler) {
            log.warning('RoutingService already initialized, ignoring init()');
            return;
        }

        // Seed lastSyncedRoute from current URL
        this.lastSyncedRoute = this.currentRoute();

        this.popstateHandler = (evt: PopStateEvent) => { void this.handlePopstate(evt); };
        window.addEventListener('popstate', this.popstateHandler);

        log.info('RoutingService initialized');
    }

    /** Push a new history entry. */
    pushRoute(route: PametRoute): void {
        this.clearPendingReplaceTimer();
        this.updateLastPageTracker(this.lastSyncedRoute ?? this.currentRoute(), route);
        log.info('Pushing route', route);
        window.history.pushState({}, '', route.toRelativeReference());
        this.lastSyncedRoute = route;
    }

    /** Replace the current URL. Use debounce=true for continuous updates (drag/zoom). */
    replaceRoute(route: PametRoute, { debounce = false }: { debounce?: boolean } = {}): void {
        this.updateLastPageTracker(this.lastSyncedRoute ?? this.currentRoute(), route);

        if (!debounce) {
            this.clearPendingReplaceTimer();
            this.doReplace(route);
            return;
        }

        const now = this.now();
        this.pendingReplaceRoute = route;

        const remaining = this.replaceCooldownMs - (now - this.lastReplaceAt);
        this.clearPendingReplaceTimer();
        const delay = remaining > 0 ? remaining : 0;

        if (delay === 0) {
            this.doReplace(route);
        } else {
            this.pendingReplaceTimer = window.setTimeout(() => {
                const routeToApply = this.pendingReplaceRoute || route;
                this.doReplace(routeToApply);
                this.pendingReplaceTimer = null;
                this.pendingReplaceRoute = null;
            }, delay);
            // Update tracking immediately even if the actual URL update is deferred
            this.lastSyncedRoute = route;
        }
    }

    toggleLastPage(currentProjectId: string | null, currentPageId: string | null): void {
        if (!currentProjectId || !currentPageId) {
            return;
        }

        const last = this.lastPageByProject.get(currentProjectId);
        const canToggleBack = !!last && last.pageId !== currentPageId;

        if (this.atToggledRoute === 'none') {
            if (!canToggleBack) {
                return;
            }
            this.suppressToggleTrackingOnce = true;
            this.atToggledRoute = 'back';
            window.history.back();
            return;
        }

        if (this.atToggledRoute === 'back') {
            this.suppressToggleTrackingOnce = true;
            this.atToggledRoute = 'forward';
            window.history.forward();
            return;
        }

        // atToggledRoute === 'forward'
        this.suppressToggleTrackingOnce = true;
        this.atToggledRoute = 'back';
        window.history.back();
    }

    dispose(): void {
        if (this.popstateHandler) {
            window.removeEventListener('popstate', this.popstateHandler);
            this.popstateHandler = null;
        }
        this.lastSyncedRoute = null;
        this.atToggledRoute = 'none';
        this.suppressToggleTrackingOnce = false;
        this.lastPageByProject.clear();
        this.clearPendingReplaceTimer();
    }

    // --- Internals ------------------------------------------------------------

    private doReplace(route: PametRoute): void {
        log.info('Replacing route', route);
        window.history.replaceState({}, '', route.toRelativeReference());
        this.lastReplaceAt = this.now();
        this.lastSyncedRoute = route;
    }

    private now(): number {
        return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    }

    private clearPendingReplaceTimer(): void {
        if (this.pendingReplaceTimer !== null) {
            window.clearTimeout(this.pendingReplaceTimer);
            this.pendingReplaceTimer = null;
            this.pendingReplaceRoute = null;
        }
    }

    private updateLastPageTracker(prevRoute: PametRoute, nextRoute: PametRoute): void {
        const projectUnchanged = prevRoute.projectId === nextRoute.projectId;
        const pageChanged = prevRoute.pageId !== nextRoute.pageId;

        if (projectUnchanged && pageChanged && !this.suppressToggleTrackingOnce && prevRoute.pageId) {
            this.lastPageByProject.set(prevRoute.projectId!, {
                pageId: prevRoute.pageId!,
                viewportCenter: prevRoute.viewportCenter,
                viewportEyeHeight: prevRoute.viewportEyeHeight,
            });
        }

        if (projectUnchanged && pageChanged && !this.suppressToggleTrackingOnce) {
            this.atToggledRoute = 'none';
        }

        this.suppressToggleTrackingOnce = false;
    }

    private async handlePopstate(_evt: PopStateEvent): Promise<void> {
        this.clearPendingReplaceTimer();
        this.suppressToggleTrackingOnce = true;

        if (this._updateHandler) {
            const route = this.currentRoute();
            this._updateHandler(route);
        }
    }
}
