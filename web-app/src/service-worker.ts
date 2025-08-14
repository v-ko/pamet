import { StorageServiceActual } from 'fusion/storage/management/StorageService';
import { parsePametMediaUrl } from "@/storage/storage-utils";
import { setupServiceWorker } from 'fusion/storage/management/service-worker-utils';

import { getLogger } from 'fusion/logging';
import { registerEntityClasses } from "@/core/entityRegistrationHack";

getLogger('service-worker');
// let test=1
// Register entity classes in service worker context
registerEntityClasses();

let storageService = new StorageServiceActual(parsePametMediaUrl);
storageService.setupMediaRequestInterception();
setupServiceWorker(storageService);
