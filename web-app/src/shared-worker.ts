import { StorageService } from 'sivkit/storage/management/StorageService';
import { setupSharedWorker } from 'sivkit/storage/management/shared-worker-utils';

import { getLogger } from 'sivkit/logging';
import { registerEntityClasses } from "@/app/entityRegistrationHack";

getLogger('shared-worker');

registerEntityClasses();

let storageService = new StorageService();
setupSharedWorker(storageService);
