import { StorageServiceActual } from 'fusion/storage/management/StorageService';
import { parsePametFileUrl } from "@/storage/storage-utils";
import { setupServiceWorker } from 'fusion/storage/management/service-worker-utils';

import { getLogger } from 'fusion/logging';
import { registerEntityClasses } from "@/core/entityRegistrationHack";
import { DesktopStorageAddon } from "@/storage/DesktopStorageAddon";

getLogger('service-worker-desktop');

registerEntityClasses();

let storageService = new StorageServiceActual(parsePametFileUrl, [
    { name: 'DesktopStorageAddon', create: (psm) => new DesktopStorageAddon(psm) },
]);
storageService.setupFileRequestInterception();
setupServiceWorker(storageService);
