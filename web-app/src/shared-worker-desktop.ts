import { StorageService } from 'sivkit/storage/management/StorageService';
import { setupSharedWorker } from 'sivkit/storage/management/shared-worker-utils';

import { getLogger } from 'sivkit/logging';
import { registerEntityClasses } from "@/app/entityRegistrationHack";
import { DesktopStorageAddon } from "@/storage/DesktopStorageAddon";
import { historyAddonDescriptor } from "@/storage/HistoryAddon";

getLogger('shared-worker-desktop');

registerEntityClasses();

let storageService = new StorageService([
    { name: 'DesktopStorageAddon', create: (psm) => new DesktopStorageAddon(psm) },
    // Reverse teardown drains history while its desktop bridge is still open.
    historyAddonDescriptor({ check: 'backend' }),
]);
setupSharedWorker(storageService);
