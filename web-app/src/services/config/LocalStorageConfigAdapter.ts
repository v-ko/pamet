import { getLogger } from "fusion/logging";
import { BaseConfigAdapter } from "./BaseConfigAdapter";

const log = getLogger('LocalStorageConfigAdapter');


export class LocalStorageConfigAdapter extends BaseConfigAdapter {
    private _handler = () => { };

    getJSON(key: string): any | undefined {
        return localStorage.getItem(key);
    }

    setJSON(key: string, value: string | undefined): void {
        if (value === undefined) {
            localStorage.removeItem(key);
        } else {
            localStorage.setItem(key, value);
        }
        // Trigger update, since only remote updates trigger the storage events
        this._handler();
    }
    keys(): string[] {
        return Object.keys(localStorage);
    }
    setUpdateHandler(handler: () => void) {
        this._handler = handler; // For local updates

        // Listen for updates from other tabs
        window.addEventListener('storage', (event) => {
            if (event.storageArea === localStorage) {
                log.info('Local storage update detected', event);
                handler();
            }
        });
    }
}
