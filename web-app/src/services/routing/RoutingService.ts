import { getLogger } from "fusion/logging";
import { PametRoute } from "@/services/routing/route";
import { updateAppFromRouteOrAutoassist } from "@/procedures/app";

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
        const url = route.toRelativeReference();
        window.history.replaceState({}, '', url);
    }

    pushRoute(route: PametRoute): void {
        log.info('Pushing route', route);
        const url = route.toRelativeReference();
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
}
