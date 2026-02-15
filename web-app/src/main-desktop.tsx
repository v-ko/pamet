import React from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";
import serviceWorkerUrl from "@/service-worker?url"

import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';
import { pamet } from "@/core/facade";
import { WebAppState } from "@/containers/app/WebAppState";
import { DEFAULT_KEYBINDINGS } from "@/core/keybindings";
import { updateAppFromRouteOrAutoassist, updateAppStateFromConfig } from "@/procedures/app";

import { DesktopPametConfigService } from "@/services/config/Config";
import { LocalStorageConfigAdapter } from "@/services/config/LocalStorageConfigAdapter";

import WebApp from "@/containers/app/App";

import { PAMET_INMEMORY_STORE_CONFIG } from "@/storage/PametStore";
import { MediaStoreAdapterNames, ProjectStorageConfig } from 'fusion/storage/management/ProjectStorageManager';
import { StorageAdapterNames } from 'fusion/storage/repository/Repository';
import { StorageService } from "fusion/storage/management/StorageService";
import { registerEntityClasses } from "@/core/entityRegistrationHack";
import { LOCAL_USER_ID } from "@/core/constants";

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

const configService = new DesktopPametConfigService({
    adapter: new LocalStorageConfigAdapter(),
    baseUrl: baseUrl,
    auth: desktopAuth,
});
pamet.setConfigService(configService)

// Desktop storage configuration factory (RestApi for both storage and media)
function desktopStorageConfigFactory(projectId: string): ProjectStorageConfig {
    let device = pamet.config.getDeviceData();
    if (!device) {
        throw Error('Device not set');
    }
    return {
        deviceBranchName: device.id,
        storeIndexConfigs: PAMET_INMEMORY_STORE_CONFIG,
        onDeviceStorageAdapter: {
            name: 'RestApi' as StorageAdapterNames,
            args: {
                projectId: projectId,
                localBranchName: device.id,
                baseUrl: baseUrl,
                auth: desktopAuth,
            }
        },
        onDeviceMediaStore: {
            name: 'RestApi' as MediaStoreAdapterNames,
            args: {
                projectId: projectId,
                baseUrl: baseUrl,
                auth: desktopAuth,
            }
        }
    }
}

pamet.setProjectStorageConfigFactory(desktopStorageConfigFactory);

// Initialize the desktop app
async function initializeDesktopApp() {
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
            name: "DesktopApp",
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
            id: LOCAL_USER_ID,
            name: "Local User",
        }
        config.setUserData(userData);
    }

    await configService.refreshLocalProjectsFromDesktop();

    await updateAppStateFromConfig(pamet.appViewState).catch((e) => {
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
    try {
        log.info("Initializing storage service in desktop mode...");
        let storageService = new StorageService();
        await storageService.setupInServiceWorker(serviceWorkerUrl);
        pamet.setStorageService(storageService);
        log.info("Storage service initialized in desktop mode");
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
