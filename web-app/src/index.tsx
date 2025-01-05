import React, { createContext } from 'react';
import ReactDOM from 'react-dom/client';
import WebApp, { WebAppState } from './containers/app/App';
import './index.css';
// import reportWebVitals from './reportWebVitals';
import { PametFacade, pamet } from './core/facade';
import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';


// Imports that are required to just activate decorators. Might be removed when
// some extensions logic is implemented
import { TextNote } from './model/TextNote';
import { CardNote } from './model/CardNote';
import { ImageNote } from './model/ImageNote';
import { OtherPageListNote } from './model/OtherPageListNote';
import { ScriptNote } from './model/ScriptNote';
import { InternalLinkNote } from './model/InternalLinkNote';
import { InternalLinkNoteCanvasView } from './components/note/InternalLinkCanvasView';
import { ExternalLinkNote } from './model/ExternalLinkNote';
import { ExternalLinkNoteCanvasView } from './components/note/ExternalLinkCanvasView';
import { ScriptNoteCanvasView } from './components/note/ScriptNoteCanvasView';
import { CardNoteCanvasView } from './components/note/CardNoteCanvasView';
import { fusion } from 'fusion/index';
import { ActionState } from 'fusion/libs/Action';
import { appActions } from './actions/app';
import { PametConfig } from './config/Config';
import { LocalStorageConfigAdapter } from './config/LocalStorageConfigAdapter';
import { ProjectData } from './model/config/Project';
import { currentTime, timestamp } from 'fusion/util';
import { StorageService } from './storage/StorageService';

let dummyImports: any[] = [];
dummyImports.push(TextNote);
dummyImports.push(CardNote);
dummyImports.push(ImageNote);
dummyImports.push(OtherPageListNote);
dummyImports.push(ScriptNote);
dummyImports.push(InternalLinkNote);
dummyImports.push(ExternalLinkNote);
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
let app_state = new WebAppState()
pamet.setAppViewState(app_state)

const config = new PametConfig(new LocalStorageConfigAdapter())
pamet.setConfig(config)

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

// Check for user. If none - create
let userData = config.userData;
if (!userData) {
    userData = {
        id: "user-" + crypto.randomUUID(),
        name: "Anonymous",
        projects: []
    }
    config.userData = userData;
}

// Check for projects. If none - create a default one
let projects = userData.projects;
if (!projects || projects.length === 0) {
    let project: ProjectData = {
        id: 'notes',
        name: "Notebook",
        owner: userData.id,
        description: 'Default project',
        created: timestamp(currentTime())
    }
    userData.projects = [project];
    config.userData = userData;
}

// Setup state updates on config updates and do an initial update
// This should be more integrated with mobx
appActions.updateAppStateFromConfig(app_state);
config.setUpdateHandler(() => {
    appActions.updateAppStateFromConfig(app_state);
});

// // Setup the sync service
setupWebWorkerLoggingChannel();

// Create a storage service in the main thread
let storageService = StorageService.inMainThread();
pamet.setStorageService(storageService);
// Determine the route and do an initial update
// let route = pamet.router.currentRoute()
// appActions.applyRoute(app_state, route);

// Setup automatic handling
pamet.router.handleRouteChange(true);
pamet.router.reachRouteOrAutoassist(
    pamet.router.currentRoute()).catch((e) => {
        log.error("Error in reachRouteOrAutoassist", e);
    });

// Load the default project - in applyRoute


// // Start loading the storage service in the service worker
// // When/if done successfully - swap it out
// StorageService.serviceWorkerProxy().then((serviceWorkerStorageService) => {
//     pamet.setStorageService(serviceWorkerStorageService);
//     log.info("Service worker storage service loaded");
// }).catch((e) => {
//     log.error("Error loading service worker storage service", e);
// });


// // Disconnect on app close
// window.addEventListener('beforeunload', () => {
//     storageService.disconnect();
// });

// // Initial entity load (TMP, will be done by the sync service)
// const afterLoad = () => {
//     log.info("Loaded all entities")

//     appActions.setLoading(app_state, false);

//     let urlPath = window.location.pathname;
//     // If we're at the index page, load home or first
//     if (urlPath === "/") {
//         appActions.setPageToHomeOrFirst(app_state);

//         // If the URL contains /p/ - load the page by id, else load the home page
//     } else if (urlPath.includes("/p/")) {
//         const pageId = urlPath.split("/")[2];

//         // Get the page from the pages array
//         const page = pamet.findOne({ id: pageId });
//         if (page) {
//             appActions.setCurrentPage(app_state, page.id);
//         } else {
//             log.warning(`Page with id ${pageId} not found`);
//             appActions.setCurrentPage(app_state, null, PageError.NOT_FOUND);
//         }
//     } else {
//         console.log("Url not supported", urlPath)
//         appActions.setCurrentPage(app_state, null);
//     }
// }
// pamet.loadAllEntitiesTMP(afterLoad);

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
