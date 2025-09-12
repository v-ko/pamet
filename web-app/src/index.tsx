import React from 'react';
import ReactDOM from 'react-dom/client';
import "@/index.css";

import { getLogger } from 'fusion/logging';
import { webStorageConfigFactory, pamet } from "@/core/facade";

import { PametConfigService } from "@/services/config/Config";
import { LocalStorageConfigAdapter } from "@/services/config/LocalStorageConfigAdapter";

import WebApp from "@/containers/app/App";

import { PAMET_INMEMORY_STORE_CONFIG } from "@/storage/PametStore";
import { MediaStoreAdapterNames, ProjectStorageConfig } from 'fusion/storage/management/ProjectStorageManager';
import { StorageAdapterNames } from 'fusion/storage/repository/Repository';
import { initializeApp } from '@/init';

const log = getLogger("index.tsx");

// Pass the facade to all components
(window as any).pamet = pamet; // For debugging

// Configure storage adapters
const configService = new PametConfigService(new LocalStorageConfigAdapter())
pamet.setConfigService(configService)

// Service related
export function inMainThreadConfigFactory(projectId: string): ProjectStorageConfig {
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
        onDeviceMediaStore: {
            name: 'CacheAPI' as MediaStoreAdapterNames, // ???
            args: {
                projectId: projectId
            }
        }
    }
}

pamet.setProjectStorageConfigFactory(webStorageConfigFactory)
// pamet.setProjectStorageConfigFactory(inMainThreadConfigFactory)

initializeApp().catch((e) => {
    log.error("Error in initializeApp", e);
    // alert("Failed to initialize app. Please check the console for details.");
});

// // App close confirmation
// window.addEventListener('beforeunload', (event) => {
//     const pageViewState = pamet.appViewState.currentPageViewState;
//     if (pageViewState && pageViewState.noteEditWindowState) {
//         // Standard way to trigger the browser's "Are you sure you want to leave?"
//         event.preventDefault();
//         event.returnValue = '';
//     }
// });



// Render the app
const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
    <React.StrictMode>
        <WebApp state={pamet.appViewState} />
    </React.StrictMode>
);
