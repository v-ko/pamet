import React, { createContext } from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";

// import reportWebVitals from './reportWebVitals';
import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';
import { PametFacade, webStorageConfigFactory, pamet } from "@/core/facade";


import { registerEntityClasses } from "@/core/entityRegistrationHack";
registerEntityClasses();

// Canvas view imports (still needed for UI components)
import { ScriptNoteCanvasView } from "@/components/note/ScriptNoteCanvasView";
import { CardNoteCanvasView } from "@/components/note/CardNoteCanvasView";
import { ActionState } from 'fusion/registries/Action';
import { PametConfigService } from "@/services/config/Config";
import { LocalStorageConfigAdapter } from "@/services/config/LocalStorageConfigAdapter";
import { StorageService } from 'fusion/storage/management/StorageService';
import { updateAppFromRouteOrAutoassist } from "@/procedures/app";

import WebApp from "@/containers/app/App";
import { WebAppState } from "@/containers/app/WebAppState";

import serviceWorkerUrl from "@/service-worker?url"
import { PAMET_INMEMORY_STORE_CONFIG } from "@/storage/PametStore";
import { MediaStoreAdapterNames, ProjectStorageConfig } from 'fusion/storage/management/ProjectStorageManager';
import { DEFAULT_KEYBINDINGS } from "@/core/keybindings";
import { addChannel } from 'fusion/registries/Channel';
import { StorageAdapterNames } from 'fusion/storage/repository/Repository';
// import { MediaProcessingDialogState } from './components/system-modal-dialog/state';

// Register entity classes in main thread context

// Keep canvas view imports to prevent tree-shaking
let dummyImports: any[] = [];
dummyImports.push(ScriptNoteCanvasView)
dummyImports.push(CardNoteCanvasView)

const log = getLogger("index.tsx");

// Create the root
const root = ReactDOM.createRoot(
    document.getElementById('root') as HTMLElement
);

// Pass the facade to all components
const PametContext = createContext<PametFacade>(pamet);
(window as any).pamet = pamet; // For debugging

// Configure pamet
let appState = new WebAppState()
// let testSystemDialog = new MediaProcessingDialogState();
// testSystemDialog.title = "Test Dialog";
// testSystemDialog.taskDescription = "Lorem impsum i guess";
// appState.systemModalDialogState = testSystemDialog;

pamet.setAppViewState(appState)
pamet.setKeybindings(DEFAULT_KEYBINDINGS);

// Setup FocusManager for declarative context management
pamet.setupFocusManager();
pamet.focusManager.updateContextOnFocus({
    selector: '.page-view',
    contextKey: 'canvasFocus',
    valOnFocus: true,
    valOnBlur: false,
});

pamet.focusManager.updateContextOnFocus({
    selector: '.note-edit-view',
    contextKey: 'noteEditViewFocused',
    valOnFocus: true,
    valOnBlur: false,
});

const config = new PametConfigService(new LocalStorageConfigAdapter())

// Setup the user and device configs. For now the simplest possible setup:
// Generate device if none. Generate anonymous user and default project and page if none

// Check if the device is set - if missing - generate metadata
let deviceData = config.getDeviceData();
if (!deviceData) {
    deviceData = {
        id: "device-" + crypto.randomUUID(),
        name: "WebApp",
    }
    config.setDeviceData(deviceData);
}

// Check for user. If none - create with default 'local' user
// Default user is 'local' for initial provisioning. When setting up storage
// with a real user account, the project should be moved explicitly from 'local'
// to the actual user. This allows the app to work immediately without requiring
// user registration, while still supporting proper user-scoped storage later.
if (!config.getUserData()) {
    let userData = {
        id: "local",
        name: "Local User",
        projects: []
    }
    config.setUserData(userData);
}

pamet.setConfig(config)

// // Setup the sync service
setupWebWorkerLoggingChannel();

// // Setup for desktop testing
// deviceData = {
//     id: 'desktop',
//     name: 'Desktop device'
// }
// log.info('User', config.userData, 'Device', config.deviceData)

// config.deviceData = deviceData


// Service related
export function inMainThreadConfigFactory(projectId: string): ProjectStorageConfig {
    let device = pamet.config.getDeviceData();
    if (!device) {
        throw Error('Device not set');
    }
    return {
        deviceBranchName: device.id,
        storeIndexConfigs: PAMET_INMEMORY_STORE_CONFIG,
        onDeviceStorageAdapter: {
            name: 'IndexedDB' as StorageAdapterNames,
            args: {
                projectId: projectId,
                localBranchName: device.id,
            }
        },
        onDeviceMediaStore: {
            name: 'CacheAPI' as MediaStoreAdapterNames, // ???
            args: {
                projectId: projectId
            }
        }
    }
}


async function initializeApp() {
    // Init storage service
    try{
        // Create a storage service in the main thread
        // let storageService = StorageService.inMainThread();
        // pamet.setStorageService(storageService);

        log.info("Initializing storage service...");

        pamet.setProjectStorageConfigFactory(webStorageConfigFactory)
        // pamet.setProjectStorageConfigFactory(inMainThreadConfigFactory)

        let storageService = new StorageService();
        await storageService.setupInServiceWorker(serviceWorkerUrl);
        // storageService.setupInMainThread();
        pamet.setStorageService(storageService);
        log.info("Storage service initialized");
    } catch (e) {
        log.error("Failed to initialize storage service", e);
    }

    // Initialize router after config and initial URL → State hydration
    pamet.router.init(pamet.appViewState);

    // Handle the route
    try{
        await updateAppFromRouteOrAutoassist(pamet.router.currentRoute())
    } catch (e) {
        log.error("Error in updateAppFromRouteOrAutoassist", e);
    }
}
initializeApp().catch((e) => {
    log.error("Error in initializeApp", e);
    alert("Failed to initialize app. Please check the console for details.");
});



// // App close confirmation
// window.addEventListener('beforeunload', (event) => {
//     const pageViewState = pamet.appViewState.currentPageViewState;
//     if (pageViewState && pageViewState.noteEditWindowState) {
//         // Standard way to trigger the browser's "Are you sure you want to leave?"
//         event.preventDefault();
//         event.returnValue = '';
//     }
// });


// Testing: log the actions channel
let rootActionEventsChannel = addChannel('rootActionEvents');
rootActionEventsChannel.subscribe((actionState: ActionState) => {
    if (actionState.issuer !== 'user') {
        return;
    }
    log.info(`rootActionEventsChannel: ${actionState.name} ${actionState.runState}`);
});

// Render the app
root.render(
    <React.StrictMode>
        <PametContext.Provider value={pamet}>
            <WebApp state={pamet.appViewState} />
        </PametContext.Provider>
    </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
// reportWebVitals();
