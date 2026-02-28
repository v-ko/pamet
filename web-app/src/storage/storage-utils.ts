import { FileRequest, FileRequestParser, StorageServiceActual } from "fusion/storage/management/StorageService";
import { PametRoute } from "@/services/routing/route";
import { getLogger } from "fusion/logging";

let log = getLogger('storage-utils');


export const parsePametFileUrl: FileRequestParser = (storageService: StorageServiceActual, url: string): FileRequest | null => {
    const route = PametRoute.fromUrl(url);

    if (route.fileItemId && route.projectId) {
        log.info(`Parsed file request from URL: ${url}`, route);
        return {
            projectId: route.projectId,
            fileItemId: route.fileItemId,
            fileItemContentHash: route.fileItemContentHash,
        };
    }

    return null;
}
