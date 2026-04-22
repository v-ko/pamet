import { StorageService } from 'fusion/storage/management/StorageService';
import { parsePametFileUrl } from "@/storage/storage-utils";
import { setupSharedWorker } from 'fusion/storage/management/shared-worker-utils';

import { getLogger } from 'fusion/logging';
import { registerEntityClasses } from "@/app/entityRegistrationHack";
import { DesktopStorageAddon } from "@/storage/DesktopStorageAddon";

getLogger('shared-worker-desktop');

registerEntityClasses();

let storageService = new StorageService(parsePametFileUrl, [
    { name: 'DesktopStorageAddon', create: (psm) => new DesktopStorageAddon(psm) },
]);
setupSharedWorker(storageService);
