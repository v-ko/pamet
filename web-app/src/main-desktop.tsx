import React from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";
import serviceWorkerUrl from "@/service-worker-desktop?url"

import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';
import { pamet, type ProjectStorageConfigFactory } from "@/core/facade";
import { AppViewState } from "@/containers/app/AppViewState";
import { DEFAULT_KEYBINDINGS } from "@/core/default-keybindings";
import { ensureProjectAndNavigate } from "@/procedures/app";
import { appActions } from "@/actions/app";

import { WebSocketSyncService } from "fusion/storage/sync/WebSocketSyncService";

import WebApp from "@/containers/app/App";
import folderCheckIconUrl from "@/resources/icons/folder-check-line.svg";
import folderCloseIconUrl from "@/resources/icons/folder-close-line.svg";

import { FileStoreAdapterNames } from 'fusion/storage/management/ProjectStorageManager';
import { VcsAdapterNames } from 'fusion/storage/repository/Repository';
import { DomainStoreAdapterNames } from 'fusion/storage/domain-store-adapter/DomainStoreAdapter';
import { StorageService } from "fusion/storage/management/StorageService";
import { registerEntityClasses } from "@/core/entityRegistrationHack";
import { LOCAL_USER_ID } from "@/core/constants";
import { buildDeviceBranchName } from "./util";

const log = getLogger("main-desktop.tsx");
setupWebWorkerLoggingChannel();
registerEntityClasses();

// Desktop mode access token (injected by desktop app)
declare global {
    interface Window {
        PAMET_DESKTOP_ACCESS_TOKEN?: string;
        PAMET_DESKTOP_API_BASE_URL?: string;
    }
}

// Pass the facade to all components
(window as any).pamet = pamet; // For debugging convenience

log.info("Running in desktop mode");

// Configure storage adapters
const desktopAccessToken = window.PAMET_DESKTOP_ACCESS_TOKEN;
if (!desktopAccessToken) {
    throw Error('Desktop mode requires PAMET_DESKTOP_ACCESS_TOKEN for RestApi Bearer auth');
}
const desktopAuth = {
    type: 'Bearer' as const,
    token: desktopAccessToken,
};
const desktopApiBaseUrl = window.PAMET_DESKTOP_API_BASE_URL;
if (!desktopApiBaseUrl) {
    throw Error('Desktop mode requires PAMET_DESKTOP_API_BASE_URL for RestApi endpoint selection');
}
const baseUrl = desktopApiBaseUrl;

// Desktop storage configuration factory (IndexedDB for VCS, RestApi for media/filesystem bridge)
const desktopStorageConfigFactory: ProjectStorageConfigFactory = (projectId, userId, deviceId) => {
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
            name: 'RestApi' as FileStoreAdapterNames,
            args: {
                projectId: projectId,
                baseUrl: baseUrl,
                auth: desktopAuth,
            }
        },
        domainStore: {
            name: 'RestApi' as DomainStoreAdapterNames,
            args: {
                projectId: projectId,
                baseUrl: baseUrl,
                auth: desktopAuth,
            }
        },
    };
};

pamet.setProjectStorageConfigFactory(desktopStorageConfigFactory);
pamet.setStorageStatusIconSet({
    healthyIconUrl: folderCheckIconUrl,
    failedIconUrl: folderCloseIconUrl,
});

// Initialize the desktop app (async: storage, config, routing)
async function initializeDesktopApp() {
    // Setup config store with WebSocket sync to desktop server
    const wsUrl = baseUrl.replace(/^http/, 'ws') + '/config/store/ws?token=' + encodeURIComponent(desktopAccessToken!);
    const configSync = new WebSocketSyncService({
        role: 'receiver',
        url: wsUrl,
    });
    await pamet.setupConfigStore(configSync);

    // Generate device if none
    let deviceId = pamet.getDeviceId();
    if (!deviceId) {
        deviceId = "device-" + crypto.randomUUID();
        pamet.setDeviceId(deviceId);
    }

    // Check for user. If none - create with default 'local' user
    if (!pamet.getUserData()) {
        pamet.setUserData({
            id: LOCAL_USER_ID,
            name: "Local User",
        });
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
        log.info("Initializing storage service in desktop mode...");
        await storageService.setupInServiceWorker(serviceWorkerUrl);
        log.info("Storage service initialized in desktop mode");
    } catch (e) {
        log.error("Failed to initialize storage service", e);
    }

    // Populate app view state from config store
    appViewState.deviceId = pamet.getDeviceId() ?? null;
    const userData = pamet.getUserData();
    if (userData?.id) {
        appViewState.userId = userData.id;
    }
    appViewState.trackedProjects = pamet.getTrackedProjectsFromConfig();
    appViewState.recentProjects = pamet.getRecentProjects();

    pamet.initRouter();

    // Handle the route
    try {
        await ensureProjectAndNavigate()
    } catch (e) {
        log.error("Error in updateAppFromRouteOrAutoassist", e);
    }
}

let appViewState = new AppViewState({ userId: LOCAL_USER_ID })
pamet.setAppViewState(appViewState)
initializeDesktopApp().catch((e) => {
    log.error("Error in initializeDesktopApp", e);
});

// Render the app
const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
    <React.StrictMode>
        <WebApp state={pamet.appViewState} />
    </React.StrictMode>
);
