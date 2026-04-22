import React from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";
import sharedWorkerUrl from "@/shared-worker?url"
import fileSwUrl from "@/service-worker-files?url"

import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';
import { pamet, type ProjectStorageConfigFactory } from "@/app/facade";
import { AppViewState } from "@/views/AppViewState";
import { DEFAULT_KEYBINDINGS } from "@/app/default-keybindings";
import { ensureProjectAndNavigate } from "@/procedures/app";
import { appActions } from "@/actions/app";

import { LocalStorageConfigSync } from "@/services/config/LocalStorageConfigSync";

import WebApp from "@/views/App";
import folderWarningIconUrl from "@/resources/icons/folder-warning-line.svg";
import folderCloseIconUrl from "@/resources/icons/folder-close-line.svg";

import { FileStoreAdapterNames } from 'fusion/storage/management/ProjectStorageManager';
import { VcsAdapterNames } from 'fusion/storage/repository/Repository';
import { StorageService } from "fusion/storage/management/StorageService";
import { LOCAL_USER_ID } from "@/app/constants";
import { registerEntityClasses } from "@/app/entityRegistrationHack";
import { buildDeviceBranchName } from "./app/util";
import { ErrorBoundary } from "@/views/ErrorBoundary";

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

// Create app view state and render synchronously so the UI appears immediately
let appViewState = new AppViewState({ userId: LOCAL_USER_ID })
pamet.setAppViewState(appViewState)
pamet.initializeTheme();

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
    <React.StrictMode>
        <ErrorBoundary>
            <WebApp state={pamet.appViewState} />
        </ErrorBoundary>
    </React.StrictMode>
);

// Initialize the web app (async: storage, config, routing)
async function initializeWebApp() {
  try {
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
        appActions.setStorageServiceState(appViewState, nextState);
    });
    pamet.setStorageService(storageService);
    try {
        log.info("Initializing storage service in web mode...");
        if (typeof SharedWorker !== 'undefined') {
            await storageService.setupInSharedWorker(sharedWorkerUrl);
        } else {
            storageService.setupInMainThread(); // Chrome Android fallback
        }
        log.info("Storage service initialized in web mode");
    } catch (e) {
        log.error("Failed to initialize storage service", e);
    }

    // Register stateless SW for serving cached files
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register(fileSwUrl, { type: 'module', scope: '/' }).catch(err => {
            log.error("Failed to register file-serving service worker", err);
        });
    }

    // Populate app view state from config store
    appViewState.deviceId = pamet.getDeviceId() ?? null;
    appViewState.trackedProjects = pamet.getTrackedProjectsFromConfig();
    appViewState.recentProjects = pamet.getRecentProjects();

    pamet.initRouter();

    // Handle the route
    try {
        await ensureProjectAndNavigate()
    } catch (e) {
        log.error("Error in updateAppFromRouteOrAutoassist", e);
    }
  } finally {
    pamet.hideSplash();
  }
}

initializeWebApp().catch((e) => {
    log.error("Error in initializeWebApp", e);
});
