import { FileRequest, FileRequestParser, StorageService } from "fusion/storage/management/StorageService";
import { PametRoute } from "@/services/routing/PametRoute";
import { getLogger } from "fusion/logging";

let log = getLogger('storage-utils');


export const parsePametFileUrl: FileRequestParser = (storageService: StorageService, url: string): FileRequest | null => {
    const route = PametRoute.fromUrl(url);

    if (route.filePath && route.projectId) {
        log.info(`Parsed file request from URL: ${url}`, route);
        return {
            projectId: route.projectId,
            filePath: route.filePath,
        };
    }

    return null;
}
