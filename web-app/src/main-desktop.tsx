import React from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";
import serviceWorkerUrl from "@/service-worker?url"

import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';
import { pamet, type ProjectStorageConfigFactory } from "@/core/facade";
import { WebAppState } from "@/containers/app/WebAppState";
import { DEFAULT_KEYBINDINGS } from "@/core/keybindings";
import { updateAppFromRouteOrAutoassist, updateAppStateFromConfig } from "@/procedures/app";
import { appActions } from "@/actions/app";

import { MiscPropertiesService, PametSettingsService } from "@/services/config/Config";
import { LocalStorageConfigAdapter } from "@/services/config/LocalStorageConfigAdapter";
import { RestDesktopConfigAdapter } from "@/services/config/RestDesktopConfigAdapter";

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

const desktopConfigAdapter = new RestDesktopConfigAdapter(baseUrl, desktopAuth);
const configService = new PametSettingsService(desktopConfigAdapter);
const appMiscProperties = new MiscPropertiesService(new LocalStorageConfigAdapter());
pamet.setConfigService(configService)
pamet.setAppMiscProperties(appMiscProperties)

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
    await desktopConfigAdapter.initialize();

    // Setup the user and device configs. For now the simplest possible setup:
    // Generate device if none. Generate anonymous user and default project and page if none
    let config = pamet.config
    let deviceId = pamet.appMiscProperties.getDeviceId();
    if (!deviceId) {
        deviceId = "device-" + crypto.randomUUID();
        pamet.appMiscProperties.setDeviceId(deviceId);
    }

    // Check for user. If none - create with default 'local' user
    // Default user is 'local' for initial provisioning. When setting up storage
    // with a real user account, the project should be moved explicitly from 'local'
    // to the actual user. This allows the app to work immediately without requiring
    // user registration, while still supporting proper user-scoped storage later.
    if (!config.getUserData()) {
        let userData = {
            id: LOCAL_USER_ID,
            name: "Local User",
        }
        config.setUserData(userData);
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
        log.info("Initializing storage service in desktop mode...");
        await storageService.setupInServiceWorker(serviceWorkerUrl);
        log.info("Storage service initialized in desktop mode");
    } catch (e) {
        log.error("Failed to initialize storage service", e);
    }

    await updateAppStateFromConfig(pamet.appViewState).catch((e) => {
        log.error('[setConfig] Error updating app state from config', e);
    });

    pamet.initRouter();

    // Handle the route
    try {
        await updateAppFromRouteOrAutoassist()
    } catch (e) {
        log.error("Error in updateAppFromRouteOrAutoassist", e);
    }
}

let appState = new WebAppState({ userId: LOCAL_USER_ID })
pamet.setAppViewState(appState)
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
