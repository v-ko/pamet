import { StorageService } from 'sivkit/storage/management/StorageService';
import { setupSharedWorker } from 'sivkit/storage/management/shared-worker-utils';

import { getLogger } from 'sivkit/logging';
import { registerEntityClasses } from "@/app/entityRegistrationHack";
import { HistoryAddon } from "@/storage/HistoryAddon";

getLogger('shared-worker');

registerEntityClasses();

let storageService = new StorageService([
    { name: 'HistoryAddon', create: (psm) => new HistoryAddon(psm, { check: 'local', vcsAdapter: 'IndexedDB' }) },
]);
setupSharedWorker(storageService);
