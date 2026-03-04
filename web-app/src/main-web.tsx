import React from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";
import serviceWorkerUrl from "@/service-worker?url"

import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';
import { pamet } from "@/core/facade";
import { WebAppState } from "@/containers/app/WebAppState";
import { DEFAULT_KEYBINDINGS } from "@/core/keybindings";
import { updateAppFromRouteOrAutoassist, updateAppStateFromConfig } from "@/procedures/app";
import { appActions } from "@/actions/app";

import { PametKeyValueStorageService } from "@/services/config/Config";
import { LocalStorageConfigAdapter } from "@/services/config/LocalStorageConfigAdapter";

import WebApp from "@/containers/app/App";
import folderWarningIconUrl from "@/resources/icons/folder-warning-line.svg";
import folderCloseIconUrl from "@/resources/icons/folder-close-line.svg";

import { PAMET_INMEMORY_STORE_CONFIG } from "@/storage/PametStore";
import { FileStoreAdapterNames, ProjectStorageConfig } from 'fusion/storage/management/ProjectStorageManager';
import { StorageAdapterNames } from 'fusion/storage/repository/Repository';
import { StorageService } from "fusion/storage/management/StorageService";
import { LOCAL_USER_ID } from "@/core/constants";
import { registerEntityClasses } from "@/core/entityRegistrationHack";

const log = getLogger("main-web.tsx");
setupWebWorkerLoggingChannel();
registerEntityClasses();

// Pass the facade to all components
(window as any).pamet = pamet; // For debugging convenience

log.info("Running in web mode");

// Configure storage adapters
const configService = new PametKeyValueStorageService(new LocalStorageConfigAdapter())
pamet.setConfigService(configService)

// Web storage configuration factory (IndexedDB + CacheAPI)
function webStorageConfigFactory(projectId: string): ProjectStorageConfig {
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
        onDeviceFileStore: {
            name: 'CacheAPI' as FileStoreAdapterNames,
            args: {
                projectId: projectId
            }
        }
    }
}

pamet.setProjectStorageConfigFactory(webStorageConfigFactory);
pamet.setStorageStatusIconSet({
    healthyIconUrl: folderWarningIconUrl,
    failedIconUrl: folderCloseIconUrl,
});

// Initialize the web app
async function initializeWebApp() {
    let appState = new WebAppState({ userId: LOCAL_USER_ID })
    pamet.setAppViewState(appState)

    // Setup the user and device configs. For now the simplest possible setup:
    // Generate device if none. Generate anonymous user and default project and page if none
    let config = pamet.config

    // Check if the device is set - if missing - generate metadata
    let deviceData = config.getDeviceData();
    if (!deviceData) {
        deviceData = {
            id: "device-" + crypto.randomUUID(),
            name: "WebApp",
        }
        config.setDeviceData(deviceData);
    }

    // User data is optional - no need to create default user
    // User will be set when cloud auth is implemented
    // For now, ensure we have at least an empty user data object with projects array
    // if (!config.getUserData()) {
    //     let userData = {
    //         projects: []
    //     }
    //     config.setUserData(userData);
    // }

    updateAppStateFromConfig(pamet.appViewState).catch((e) => {
        log.error('[setConfig] Error updating app state from config', e);
    });

    pamet.setKeybindings(DEFAULT_KEYBINDINGS);

    // Focus management related
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

    // Init storage service
    let storageService = new StorageService();
    storageService.setStateChangeHandler((nextState) => {
        appActions.setStorageServiceState(appState, nextState);
    });
    pamet.setStorageService(storageService);
    try {
        log.info("Initializing storage service in web mode...");
        if ('serviceWorker' in navigator) {
            await storageService.setupInServiceWorker(serviceWorkerUrl);
        } else {
            storageService.setupInMainThread();
        }
        log.info("Storage service initialized in web mode");
    } catch (e) {
        log.error("Failed to initialize storage service", e);
    }

    // Initialize router after config and initial URL → State hydration
    pamet.router.init(pamet.appViewState);

    // Handle the route
    try {
        await updateAppFromRouteOrAutoassist(pamet.router.currentRoute())
    } catch (e) {
        log.error("Error in updateAppFromRouteOrAutoassist", e);
    }
}

initializeWebApp().catch((e) => {
    log.error("Error in initializeWebApp", e);
});

// Render the app
const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
    <React.StrictMode>
        <WebApp state={pamet.appViewState} />
    </React.StrictMode>
);
