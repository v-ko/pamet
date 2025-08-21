import { getLogger } from "fusion/logging";
import { reaction } from "mobx";
import { PametRoute } from "@/services/routing/route";
import { updateAppFromRoute } from "@/procedures/app";
import type { WebAppState } from "@/containers/app/WebAppState";
import { pamet } from "@/core/facade";
import { PageMode } from "@/components/page/PageViewState";

const log = getLogger('RoutingService');


interface LastPageSnapshot {
    pageId: string;
    viewportCenter?: [number, number];
    viewportEyeHeight?: number;
}

export class RoutingService {
    // State <-> URL synchronizer
    private appState: WebAppState | null = null;
    private disposeStateReaction: (() => void) | null = null;
    private popstateHandler: ((e: PopStateEvent) => void) | null = null;

    // Loop and policy guards
    private isApplyingRouteToState = false;
    private atToggledRoute: 'none' | 'back' | 'forward' = 'none'; // When toggling between two pages we mark in which one we are (if any)
    private suppressToggleTrackingOnce = false;
    private disposeModeReaction: (() => void) | null = null;

    // Throttling for minor (viewport-only) URL updates
    private lastMinorReplaceAt = 0;
    private minorCooldownMs = 500;
    private pendingMinorTimer: number | null = null;
    private pendingMinorRoute: PametRoute | null = null;

    // Tracking for diffing and toggle
    private lastComputedRoute: PametRoute | null = null; // last computed from state
    private lastPageByProject: Map<string, LastPageSnapshot> = new Map();

    // Legacy listener holder (unused now)
    private routingListener: (() => void) | null = null;

    // Utilities
    currentRoute(): PametRoute {
        return PametRoute.fromUrl(window.location.href);
    }
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
    // --- Helpers ---------------------------------------------------------------

    private hasMissingPage(route: PametRoute): boolean {
        return !!route.pageId && !pamet.page(route.pageId);
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

    private isDragging(): boolean {
        return !!this.appState &&
            !!this.appState.currentPageViewState &&
            this.appState.currentPageViewState.mode === PageMode.DragNavigation;
    }

    /**
     * Decide push vs replace based on policy:
     * - Toggle hops always replace
     * - Missing current or next page => replace
     * - Otherwise, significant (user/project/page) => push; minor => replace
     */
    private computeOperation(currentUrlRoute: PametRoute, nextRoute: PametRoute): 'push' | 'replace' {
        const significant = this.isSignificantChange(currentUrlRoute, nextRoute);
        const missingCurrentPage = this.hasMissingPage(currentUrlRoute);
        const missingNextPage = this.hasMissingPage(nextRoute);

        if (this.atToggledRoute !== 'none') return 'replace';
        if (missingCurrentPage || missingNextPage) return 'replace';
        return significant ? 'push' : 'replace';
    }

    /**
     * Returns true if we scheduled a delayed minor replace and the caller should return early.
     * Also updates internal trackers.
     */
    private scheduleMinorReplace(nextRoute: PametRoute): boolean {
        // Skip while dragging
        if (this.isDragging()) {
            this.suppressToggleTrackingOnce = false;
            this.lastComputedRoute = nextRoute;
            // Do not schedule any trailing write during drag
            this.clearPendingMinorTimer();
            return true; // caller should return
        }

        const now = this.now();
        this.pendingMinorRoute = nextRoute;

        const remaining = this.minorCooldownMs - (now - this.lastMinorReplaceAt);
        // reschedule (debounce) to the end of cooldown window
        this.clearPendingMinorTimer();
        const delay = remaining > 0 ? remaining : 0;

        this.pendingMinorTimer = window.setTimeout(() => {
            const routeToApply = this.pendingMinorRoute || nextRoute;
            this.replaceRoute(routeToApply);
            this.pendingMinorRoute = null;
            this.pendingMinorTimer = null;
            this.lastMinorReplaceAt = this.now();
        }, delay);

        // Mirror immediate path bookkeeping
        this.suppressToggleTrackingOnce = false;
        this.lastComputedRoute = nextRoute;
        return true;
    }

    /** Write a final minor update immediately (used on drag end) */
    private flushMinorReplace(route: PametRoute): void {
        this.clearPendingMinorTimer();
        this.replaceRoute(route);
        this.lastMinorReplaceAt = this.now();
        this.lastComputedRoute = route;
    }

    /** Track previous page snapshot inside a project for toggling */
    private updateLastPageTracker(prevForLast: PametRoute, nextRoute: PametRoute): void {
        const projectUnchanged = prevForLast.projectId === nextRoute.projectId;
        const pageChanged = prevForLast.pageId !== nextRoute.pageId;

        if (projectUnchanged && pageChanged && !this.suppressToggleTrackingOnce && prevForLast.pageId) {
            const projId = prevForLast.projectId!;
            const snapshot: LastPageSnapshot = {
                pageId: prevForLast.pageId!,
                viewportCenter: prevForLast.viewportCenter,
                viewportEyeHeight: prevForLast.viewportEyeHeight,
            };
            this.lastPageByProject.set(projId, snapshot);
        }

        // On normal page switches (not toggle/pop), clear toggle-mode marker
        if (projectUnchanged && pageChanged && !this.suppressToggleTrackingOnce) {
            this.atToggledRoute = 'none';
        }
    }

    /** Popstate handler extracted for clarity */
    private async handlePopstate(_evt: PopStateEvent): Promise<void> {
        if (this.isApplyingRouteToState) {
            return;
        }
        this.isApplyingRouteToState = true;

        // Cancel any pending minor replace to avoid stale writes after navigation
        this.clearPendingMinorTimer();

        this.suppressToggleTrackingOnce = true; // do not rewrite last page on back/forward
        try {
            const route = this.currentRoute();
            await updateAppFromRoute(route);
        } catch (e) {
            log.error('Error applying route on popstate', e);
        } finally {
            this.isApplyingRouteToState = false;
        }
    }

    // History primitives
    replaceRoute(route: PametRoute): void {
        log.info('Setting route', route);
        const url = route.toRelativeReference();
        window.history.replaceState({}, '', url);
    }

    pushRoute(route: PametRoute): void {
        log.info('Pushing route', route);
        const url = route.toRelativeReference();
        window.history.pushState({}, '', url);
    }

    // Synchronizer API
    init(appState: WebAppState): void {
        if (this.appState) {
            log.warning('RoutingService already initialized, ignoring init()');
            return;
        }
        this.appState = appState;

        // Seed lastComputedRoute from current URL so the first reaction compares against it
        this.lastComputedRoute = this.currentRoute();

        // State -> URL reaction
        // Do NOT fire immediately on init; initial load should be URL -> State only.
        this.disposeStateReaction = reaction(
            () => {
                if (!this.appState) return null;
                // Compute route from state (includes viewport if present)
                return this.appState.toRoute();
            },
            (nextRoute) => {
                if (!nextRoute) return;
                this.syncUrlFromState(nextRoute);
            }
        );

        // Flush a minor URL update when drag navigation ends
        this.disposeModeReaction = reaction(
            () => this.appState?.currentPageViewState?.mode,
            (mode, prevMode) => {
                if (!this.appState) return;
                if (prevMode === PageMode.DragNavigation && mode !== PageMode.DragNavigation) {
                    const route = this.appState.toRoute();
                    const currentUrlRoute = this.currentRoute();
                    if (!this.isSignificantChange(currentUrlRoute, route)) {
                        this.flushMinorReplace(route);
                    }
                }
            }
        );

        // URL -> State on browser navigation
        this.popstateHandler = (evt: PopStateEvent) => { void this.handlePopstate(evt); };
        window.addEventListener('popstate', this.popstateHandler);

        log.info('RoutingService initialized');
    }

    dispose(): void {
        if (this.disposeStateReaction) {
            this.disposeStateReaction();
            this.disposeStateReaction = null;
        }
        if (this.popstateHandler) {
            window.removeEventListener('popstate', this.popstateHandler);
            this.popstateHandler = null;
        }
        if (this.disposeModeReaction) {
            this.disposeModeReaction();
            this.disposeModeReaction = null;
        }
        this.appState = null;
        this.lastComputedRoute = null;
        this.atToggledRoute = 'none';
        this.suppressToggleTrackingOnce = false;
        this.lastPageByProject.clear();

        if (this.pendingMinorTimer !== null) {
            window.clearTimeout(this.pendingMinorTimer);
            this.pendingMinorTimer = null;
            this.pendingMinorRoute = null;
        }
    }

    // Main synchronizer
    private syncUrlFromState(nextRoute: PametRoute): void {
        if (this.isApplyingRouteToState) {
            // We are currently reflecting URL -> state; do not emit URL updates
            this.lastComputedRoute = nextRoute;
            return;
        }

        const currentUrlRoute = this.currentRoute();

        // Update last-page tracker and clear toggle marker as needed
        const prevForLast = this.lastComputedRoute ?? currentUrlRoute;
        this.updateLastPageTracker(prevForLast, nextRoute);

        // Decide whether to update URL
        const equalToCurrent = this.routesEqual(currentUrlRoute, nextRoute);
        if (!equalToCurrent) {
            // Decide how to write URL (push vs replace)
            const op = this.computeOperation(currentUrlRoute, nextRoute);

            // Minor-change path with cooldown/debounce
            const significant = this.isSignificantChange(currentUrlRoute, nextRoute);
            const missingCurrentPage = this.hasMissingPage(currentUrlRoute);
            const missingNextPage = this.hasMissingPage(nextRoute);
            const isMinor =
                this.atToggledRoute === 'none' &&
                !significant &&
                !missingCurrentPage &&
                !missingNextPage;

            if (op === 'replace' && isMinor) {
                if (this.scheduleMinorReplace(nextRoute)) {
                    return;
                }
            }

            // Immediate path: clear any pending minor replace
            this.clearPendingMinorTimer();

            if (op === 'push') {
                this.pushRoute(nextRoute);
            } else {
                this.replaceRoute(nextRoute);
            }
        }

        // Clear one-shot flags and store last
        this.suppressToggleTrackingOnce = false;
        this.lastComputedRoute = nextRoute;
    }

    private async applyRouteToState(route: PametRoute): Promise<void> {
        this.isApplyingRouteToState = true;
        try {
            await updateAppFromRoute(route);
        } finally {
            this.isApplyingRouteToState = false;
        }
    }

    // Toggle between current and last page within the same project using browser history (popstate will update state)
    toggleLastPage() {
        if (!this.appState) {
            log.error('toggleLastPage called before router init');
            return;
        }
        const userId = this.appState.userId;
        const projectId = this.appState.currentProjectId;
        const currentPageId = this.appState.currentPageId;

        if (!userId || !projectId || !currentPageId) {
            return;
        }

        // Guard: only toggle within same project and when we have a tracked last page different from current
        const last = this.lastPageByProject.get(projectId);
        const canToggleBack = !!last && last.pageId !== currentPageId;

        // Use a simple state machine: first toggle goes back, next goes forward, etc.
        if (this.atToggledRoute === 'none') {
            if (!canToggleBack) {
                return;
            }
            this.suppressToggleTrackingOnce = true; // do not record last on this hop
            this.atToggledRoute = 'back';
            window.history.back(); // popstate -> updateAppFromRoute()
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
}
