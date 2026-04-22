import { StorageService } from 'fusion/storage/management/StorageService';
import { parsePametFileUrl } from "@/storage/storage-utils";
import { setupSharedWorker } from 'fusion/storage/management/shared-worker-utils';

import { getLogger } from 'fusion/logging';
import { registerEntityClasses } from "@/app/entityRegistrationHack";

getLogger('shared-worker');

registerEntityClasses();

let storageService = new StorageService(parsePametFileUrl);
setupSharedWorker(storageService);
