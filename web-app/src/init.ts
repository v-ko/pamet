import serviceWorkerUrl from "@/service-worker?url"
import { WebAppState } from "@/containers/app/WebAppState";
import { pamet } from "@/core/facade";
import { DEFAULT_KEYBINDINGS } from "@/core/keybindings";
import { updateAppFromRouteOrAutoassist, updateAppStateFromConfig } from "@/procedures/app";
import { getLogger, setupWebWorkerLoggingChannel } from "fusion/logging";
import { StorageService } from "fusion/storage/management/StorageService";
import { registerEntityClasses } from "@/core/entityRegistrationHack";

let log = getLogger("init.ts");
setupWebWorkerLoggingChannel();
registerEntityClasses();

export async function initializeApp() {
    let appState = new WebAppState()
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
    try {
        // Create a storage service in the main thread
        // let storageService = StorageService.inMainThread();
        // pamet.setStorageService(storageService);

        log.info("Initializing storage service...");
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
    try {
        await updateAppFromRouteOrAutoassist(pamet.router.currentRoute())
    } catch (e) {
        log.error("Error in updateAppFromRouteOrAutoassist", e);
    }
}
