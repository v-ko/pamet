import React from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";
import serviceWorkerUrl from "@/service-worker?url"

import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';
import { pamet, type ProjectStorageConfigFactory } from "@/core/facade";
import { WebAppState } from "@/containers/app/WebAppState";
import { DEFAULT_KEYBINDINGS } from "@/core/default-keybindings";
import { ensureProjectAndNavigate, updateAppStateFromConfig } from "@/procedures/app";
import { appActions } from "@/actions/app";

import { LocalStorageConfigSync } from "@/services/config/LocalStorageConfigSync";

import WebApp from "@/containers/app/App";
import folderWarningIconUrl from "@/resources/icons/folder-warning-line.svg";
import folderCloseIconUrl from "@/resources/icons/folder-close-line.svg";

import { FileStoreAdapterNames } from 'fusion/storage/management/ProjectStorageManager';
import { VcsAdapterNames } from 'fusion/storage/repository/Repository';
import { StorageService } from "fusion/storage/management/StorageService";
import { LOCAL_USER_ID } from "@/core/constants";
import { registerEntityClasses } from "@/core/entityRegistrationHack";
import { buildDeviceBranchName } from "./util";

const log = getLogger("main-web.tsx");
setupWebWorkerLoggingChannel();
registerEntityClasses();

// Pass the facade to all components
(window as any).pamet = pamet; // For debugging convenience

log.info("Running in web mode");

// Web storage configuration factory (IndexedDB + CacheAPI)
const webStorageConfigFactory: ProjectStorageConfigFactory = (projectId, userId, deviceId) => {
    const branchName = buildDeviceBranchName(userId, deviceId);
    return {
        projectId: projectId,
        deviceBranchName: branchName,
        onDeviceVcsAdapter: {
            name: 'IndexedDB' as VcsAdapterNames,
            args: {
                projectId: projectId,
                localBranchName: branchName,
            }
        },
        onDeviceFileStore: {
            name: 'CacheAPI' as FileStoreAdapterNames,
            args: {
                projectId: projectId
            }
        }
    };
};

pamet.setProjectStorageConfigFactory(webStorageConfigFactory);
pamet.setStorageStatusIconSet({
    healthyIconUrl: folderWarningIconUrl,
    failedIconUrl: folderCloseIconUrl,
});

// Create app state and render synchronously so the UI appears immediately
let appState = new WebAppState({ userId: LOCAL_USER_ID })
pamet.setAppViewState(appState)

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
    <React.StrictMode>
        <WebApp state={pamet.appViewState} />
    </React.StrictMode>
);

// Initialize the web app (async: storage, config, routing)
async function initializeWebApp() {

    // Setup config store with localStorage sync
    await pamet.setupConfigStore(new LocalStorageConfigSync());

    // Generate device if none
    let deviceId = pamet.getDeviceId();
    if (!deviceId) {
        deviceId = "device-" + crypto.randomUUID();
        pamet.setDeviceId(deviceId);
    }

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

    await updateAppStateFromConfig(pamet.appViewState).catch((e) => {
        log.error('[setConfig] Error updating app state from config', e);
    });

    pamet.initRouter();

    // Handle the route
    try {
        await ensureProjectAndNavigate()
    } catch (e) {
        log.error("Error in updateAppFromRouteOrAutoassist", e);
    }
}

initializeWebApp().catch((e) => {
    log.error("Error in initializeWebApp", e);
});
