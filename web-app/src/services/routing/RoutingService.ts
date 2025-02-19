import { getLogger } from "fusion/logging";
import { PametRoute } from "./route";
import { updateAppFromRouteOrAutoassist } from "../../procedures/app";

const log = getLogger('RoutingService');


export class RoutingService {
    private routingListener: (() => void) | null = null;

    // get autoHandleRouteChange(): boolean {
    //     return !!this.routingListener
    // }

    currentRoute(): PametRoute {
        return PametRoute.fromUrl(window.location.href);
    }
    replaceRoute(route: PametRoute): void {
        log.info('Setting route', route)
        const url = route.path();
        window.history.replaceState({}, '', url);
    }

    pushRoute(route: PametRoute): void {
        log.info('Pushing route', route);
        const url = route.path();
        window.history.pushState({}, '', url);
    }

    async changeRouteAndApplyToApp(route: PametRoute): Promise<void> {
        log.info('Changing route and applying to app', route);
        this.pushRoute(route);
        await updateAppFromRouteOrAutoassist(route);
    }

    async changeRouteAndReload(route: PametRoute): Promise<void> {
        log.info('Changing route and reloading', route);
        this.pushRoute(route);
        window.location.reload();
    }

    // setHandleRouteChange(enable: boolean): void {
    //     if (enable) {
    //         if (this.routingListener) {
    //             throw Error('Route change handling already enabled');
    //         }
    //         this.routingListener = () => {
    //             log.info('Route changed, calling handler');
    //             const route = this.currentRoute();
    //             updateAppFromRouteOrAutoassist(route).catch((e) => {
    //                 log.error('[routeChangeHandler] Failed in applyRouteOrAutoassist', route, e);
    //             });
    //         };
    //         window.addEventListener('popstate', this.routingListener);
    //     } else if (!enable) {
    //         if (this.routingListener) {
    //             window.removeEventListener('popstate', this.routingListener);
    //             this.routingListener = null;
    //         } else {
    //             throw Error('Route change handling already disabled');
    //         }
    //     }
    // }
}
