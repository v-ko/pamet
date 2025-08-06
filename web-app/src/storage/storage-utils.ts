import { MediaRequest, MediaRequestParser, StorageServiceActual } from "fusion/storage/StorageService";
import { PametRoute } from "../services/routing/route";
import { getLogger } from "fusion/logging";

let log = getLogger('storage-utils');


export const parsePametMediaUrl: MediaRequestParser = (storageService: StorageServiceActual, url: string): MediaRequest | null => {
    const route = PametRoute.fromUrl(url);

    if (route.mediaItemId && route.projectId) {
        log.info(`Parsed media request from URL: ${url}`, route);
        return {
            projectId: route.projectId,
            mediaItemId: route.mediaItemId,
            mediaItemContentHash: route.mediaItemContentHash,
        };
    }

    return null;
}
