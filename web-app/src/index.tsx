import React, { createContext } from 'react';
import ReactDOM from 'react-dom/client';
import WebApp from './containers/app/App';
import { WebAppState } from "./containers/app/WebAppState";
import './index.css';
// import reportWebVitals from './reportWebVitals';
import { PametFacade, pamet } from './core/facade';
import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';


// Register entity classes for @entityType decorators
import { registerEntityClasses } from './core/entityRegistrationHack';

// Canvas view imports (still needed for UI components)
import { InternalLinkNoteCanvasView } from './components/note/InternalLinkCanvasView';
import { ExternalLinkNoteCanvasView } from './components/note/ExternalLinkCanvasView';
import { ScriptNoteCanvasView } from './components/note/ScriptNoteCanvasView';
import { CardNoteCanvasView } from './components/note/CardNoteCanvasView';
import { fusion } from 'fusion/index';
import { ActionState } from 'fusion/libs/Action';
import { PametConfigService } from './services/config/Config';
import { LocalStorageConfigAdapter } from './services/config/LocalStorageConfigAdapter';
import { StorageService } from './storage/StorageService';
import { ProjectStorageConfig, StorageAdapterNames } from './storage/ProjectStorageManager';
import { updateAppFromRouteOrAutoassist } from './procedures/app';

// Register entity classes in main thread context
registerEntityClasses();

// Keep canvas view imports to prevent tree-shaking
let dummyImports: any[] = [];
dummyImports.push(InternalLinkNoteCanvasView)
dummyImports.push(ExternalLinkNoteCanvasView)
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
pamet.setAppViewState(appState)

const config = new PametConfigService(new LocalStorageConfigAdapter())

// Setup the user and device configs. For now the simplest possible setup:
// Generate device if none. Generate anonymous user and default project and page if none

// Check if the device is set - if missing - generate metadata
let deviceData = config.deviceData;
if (!deviceData) {
    deviceData = {
        id: "device-" + crypto.randomUUID(),
        name: "WebApp",
    }
    config.deviceData = deviceData;
}

// Check for user. If none - create with default 'local' user
// Default user is 'local' for initial provisioning. When setting up storage
// with a real user account, the project should be moved explicitly from 'local'
// to the actual user. This allows the app to work immediately without requiring
// user registration, while still supporting proper user-scoped storage later.
if (!config.userData) {
    let userData = {
        id: "local",
        name: "Local User",
        projects: []
    }
    config.userData = userData;
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

function offlineAppConfigFactory(projectId: string): ProjectStorageConfig {
    return {
        currentBranchName: deviceData!.id,
        localRepo: {
            name: "DesktopServer" as StorageAdapterNames,
            args: {
                projectId: projectId,
                localBranchName: deviceData!.id
            }
        },
        localMediaStore: {
            name: "CacheAPI",
            args: {
                projectId: projectId
            }
        }
    }
}

pamet.projectManagerConfigFactory = offlineAppConfigFactory

async function initializeApp() {
    // Init storage service
    try{
        // Create a storage service in the main thread
        // let storageService = StorageService.inMainThread();
        // pamet.setStorageService(storageService);

        log.info("Initializing storage service...");
        let storage_service = await StorageService.serviceWorkerProxy();
        pamet.setStorageService(storage_service);
        log.info("Storage service initialized");
    } catch (e) {
        log.error("Failed to initialize storage service", e);
    }

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



// App close confirmation
window.addEventListener('beforeunload', (event) => {
    const pageViewState = pamet.appViewState.currentPageViewState;
    if (pageViewState && pageViewState.noteEditWindowState) {
        // Standard way to trigger the browser's "Are you sure you want to leave?"
        event.preventDefault();
        event.returnValue = '';
    }
});


// Testing: log the actions channel
fusion.rootActionEventsChannel.subscribe((actionState: ActionState) => {
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
