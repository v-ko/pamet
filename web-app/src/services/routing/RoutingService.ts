import { getLogger } from "fusion/logging";
import { PametRoute } from "@/services/routing/route";

const log = getLogger('RoutingService');


interface LastPageSnapshot {
    pageId: string;
    viewportCenter?: [number, number];
    viewportEyeHeight?: number;
}

export type RouteUpdateHandler = (route: PametRoute) => void;

export class RoutingService {
    private popstateHandler: ((e: PopStateEvent) => void) | null = null;
    private _updateHandler: RouteUpdateHandler | null = null;

    // Toggle state machine
    private atToggledRoute: 'none' | 'back' | 'forward' = 'none';
    private suppressToggleTrackingOnce = false;

    // Throttling for minor (viewport-only) URL updates
    private lastMinorReplaceAt = 0;
    private minorCooldownMs = 500;
    private pendingMinorTimer: number | null = null;
    private pendingMinorRoute: PametRoute | null = null;

    // Tracking for diffing and toggle
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

    /**
     * Sync the URL to match the given route.
     * Decides push vs replace internally, debounces viewport-only changes.
     */
    navigateToRoute(route: PametRoute): void {
        const currentUrlRoute = this.currentRoute();

        // Update last-page tracker and clear toggle marker as needed
        const prevForLast = this.lastSyncedRoute ?? currentUrlRoute;
        this.updateLastPageTracker(prevForLast, route);

        // Decide whether to update URL
        if (this.routesEqual(currentUrlRoute, route)) {
            this.suppressToggleTrackingOnce = false;
            this.lastSyncedRoute = route;
            return;
        }

        const significant = this.isSignificantChange(currentUrlRoute, route);
        const op = this.atToggledRoute !== 'none' ? 'replace' as const
            : significant ? 'push' as const : 'replace' as const;

        // Minor-change path: debounce viewport-only changes
        if (op === 'replace' && !significant && this.atToggledRoute === 'none') {
            if (this.scheduleMinorReplace(route)) {
                return;
            }
        }

        // Immediate path
        this.clearPendingMinorTimer();
        if (op === 'push') {
            this.pushRoute(route);
        } else {
            this.replaceRoute(route);
        }

        this.suppressToggleTrackingOnce = false;
        this.lastSyncedRoute = route;
    }

    /**
     * Flush any pending debounced URL update immediately.
     * Call this on drag-end or when a definitive viewport is established.
     */
    flushPendingNavigation(route: PametRoute): void {
        this.clearPendingMinorTimer();
        this.replaceRoute(route);
        this.lastMinorReplaceAt = this.now();
        this.lastSyncedRoute = route;
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
        this.clearPendingMinorTimer();
    }

    // --- History primitives ---------------------------------------------------

    replaceRoute(route: PametRoute): void {
        log.info('Setting route', route);
        window.history.replaceState({}, '', route.toRelativeReference());
    }

    pushRoute(route: PametRoute): void {
        log.info('Pushing route', route);
        window.history.pushState({}, '', route.toRelativeReference());
    }

    // --- Internals ------------------------------------------------------------

    private routeKey(route: PametRoute): string {
        return route.toRelativeReference();
    }

    private routesEqual(a: PametRoute, b: PametRoute): boolean {
        return this.routeKey(a) === this.routeKey(b);
    }

    private isSignificantChange(prev: PametRoute, next: PametRoute): boolean {
        return prev.userId !== next.userId
            || prev.projectId !== next.projectId
            || prev.pageId !== next.pageId;
    }

    private now(): number {
        return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    }

    private clearPendingMinorTimer(): void {
        if (this.pendingMinorTimer !== null) {
            window.clearTimeout(this.pendingMinorTimer);
            this.pendingMinorTimer = null;
            this.pendingMinorRoute = null;
        }
    }

    private scheduleMinorReplace(nextRoute: PametRoute): boolean {
        const now = this.now();
        this.pendingMinorRoute = nextRoute;

        const remaining = this.minorCooldownMs - (now - this.lastMinorReplaceAt);
        this.clearPendingMinorTimer();
        const delay = remaining > 0 ? remaining : 0;

        this.pendingMinorTimer = window.setTimeout(() => {
            const routeToApply = this.pendingMinorRoute || nextRoute;
            this.replaceRoute(routeToApply);
            this.pendingMinorRoute = null;
            this.pendingMinorTimer = null;
            this.lastMinorReplaceAt = this.now();
        }, delay);

        this.suppressToggleTrackingOnce = false;
        this.lastSyncedRoute = nextRoute;
        return true;
    }

    private updateLastPageTracker(prevForLast: PametRoute, nextRoute: PametRoute): void {
        const projectUnchanged = prevForLast.projectId === nextRoute.projectId;
        const pageChanged = prevForLast.pageId !== nextRoute.pageId;

        if (projectUnchanged && pageChanged && !this.suppressToggleTrackingOnce && prevForLast.pageId) {
            this.lastPageByProject.set(prevForLast.projectId!, {
                pageId: prevForLast.pageId!,
                viewportCenter: prevForLast.viewportCenter,
                viewportEyeHeight: prevForLast.viewportEyeHeight,
            });
        }

        if (projectUnchanged && pageChanged && !this.suppressToggleTrackingOnce) {
            this.atToggledRoute = 'none';
        }
    }

    private async handlePopstate(_evt: PopStateEvent): Promise<void> {
        this.clearPendingMinorTimer();
        this.suppressToggleTrackingOnce = true;

        if (this._updateHandler) {
            const route = this.currentRoute();
            this._updateHandler(route);
        }
    }
}
