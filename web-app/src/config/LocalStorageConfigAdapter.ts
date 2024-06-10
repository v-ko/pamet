import { BaseConfigAdapter } from "./BaseConfigAdapter";

export class LocalStorageConfigAdapter extends BaseConfigAdapter {
    private _handler = () => {};

    getJSON(key: string): any | undefined {
        return localStorage.getItem(key);
    }

    setJSON(key: string, value: string | undefined): void {
        if (value === undefined) {
            localStorage.removeItem(key);
            return;
        }
        localStorage.setItem(key, value);
        // Trigger update, since only remote updates trigger the storage events
        this._handler();
    }

    setUpdateHandler(handler: () => void) {
        super.setUpdateHandler(handler);

        this._handler = handler; // For local updates

        // Listen for updates from other tabs
        window.addEventListener('storage', (event) => {
            if (event.storageArea === localStorage) {
                handler();
            }
        });
    }
    keys(): string[] {
        return Object.keys(localStorage);
    }
}
