import React from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";

import { getLogger, setupWebWorkerLoggingChannel } from 'fusion/logging';
import { pamet, type ProjectStorageConfigFactory } from "@/app/facade";
import { AppViewState } from "@/views/AppViewState";
import { DEFAULT_KEYBINDINGS } from "@/app/default-keybindings";
import { ensureProjectAndNavigate } from "@/procedures/app";
import { appActions } from "@/actions/app";

import { WebSocketSyncService } from "fusion/storage/sync/WebSocketSyncService";

import WebApp from "@/views/App";
import folderCheckIconUrl from "@/resources/icons/folder-check-line.svg";
import folderLineIconUrl from "@/resources/icons/folder-line.svg";
import folderWarningIconUrl from "@/resources/icons/folder-warning-line.svg";
import folderCloseIconUrl from "@/resources/icons/folder-close-line.svg";

import { FileStoreAdapterNames } from 'fusion/storage/management/ProjectStorageManager';
import { VcsAdapterNames } from 'fusion/storage/repository/Repository';
import { DomainStoreAdapterNames } from 'fusion/storage/domain-store-adapter/DomainStoreAdapter';
import { StorageServiceProxy } from "fusion/storage/management/StorageServiceProxy";
import { registerEntityClasses } from "@/app/entityRegistrationHack";
import { ProjectProperties } from "@/model/config/ProjectProperties";
import { LOCAL_USER_ID } from "@/app/constants";
import { buildDeviceBranchName } from "./app/util";
import { ErrorBoundary } from "@/views/ErrorBoundary";

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
                userId: userId,
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
    unsavedIconUrl: folderLineIconUrl,
    failedIconUrl: folderWarningIconUrl,
    unavailableIconUrl: folderCloseIconUrl,
});

// Initialize the desktop app (async: storage, config, routing)
async function initializeDesktopApp() {
  try {
    // Set auth cookie so bare <img src> requests carry credentials
    document.cookie = `pamet_desktop_token=${desktopAccessToken}; path=/; samesite=strict`;

    // Setup config store with WebSocket sync to desktop server
    const wsUrl = baseUrl.replace(/^http/, 'ws') + '/config/store/ws';
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
    let storageService = new StorageServiceProxy();
    storageService.setStateChangeHandler((nextState) => {
        appActions.setStorageServiceState(appViewState, nextState);
    });
    pamet.setStorageService(storageService);
    try {
        log.info("Initializing storage service in desktop mode (SharedWorker)...");
        const worker = new SharedWorker(
            new URL('@/shared-worker-desktop.ts', import.meta.url),
            { type: 'module' },
        );
        await storageService.setupInSharedWorker(worker);
        log.info("Storage service initialized in desktop mode (SharedWorker)");
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
  } finally {
    pamet.hideSplash();
  }
}

let appViewState = new AppViewState({ userId: LOCAL_USER_ID })
pamet.setAppViewState(appViewState)
pamet.setContext('desktopMode', true);
pamet.initClipboard();
pamet.initializeTheme();

// Wire desktop-specific change history hook
pamet.changeHistoryService.onError = (message: string) => {
    pamet.storageService.reportError(message);
    // Flag integrity error in replay panel if it's a hash mismatch
    if (message.includes("hash mismatch") || message.includes("Snapshot hash mismatch")) {
        const vs = pamet.appViewState.replayPanelVS;
        if (vs) {
            vs.hasIntegrityError = true;
        }
    }
};

pamet.onChangeHistoryConfigChanged = (projectId: string) => {
    const propsEntity = pamet.appConfigStore.findOne({
        id: ProjectProperties.idForProject(projectId),
    });
    const enabled = propsEntity
        ? (propsEntity as ProjectProperties).recordAllChanges
        : false;

    if (enabled && !pamet.changeHistoryService.enabled) {
        if (!pamet._currentProjectStore) {
            log.info('ChangeHistory: store not attached yet, deferring enable');
            return;
        }
        const wsUrl = baseUrl.replace(/^http/, 'ws')
            + `/desktop/projects/${encodeURIComponent(projectId)}/changes/history/ws`;
        pamet.changeHistoryService.enable(pamet._currentProjectStore, wsUrl).catch((e) => {
            log.error('Failed to enable change history service', e);
        });
    } else if (!enabled && pamet.changeHistoryService.enabled) {
        pamet.changeHistoryService.disable();
    }
};

initializeDesktopApp().catch((e) => {
    log.error("Error in initializeDesktopApp", e);
});

// Render the app
const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
    <React.StrictMode>
        <ErrorBoundary>
            <WebApp state={pamet.appViewState} />
        </ErrorBoundary>
    </React.StrictMode>
);
