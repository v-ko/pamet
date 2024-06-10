import { DeviceData } from "../model/Device";
import { UserData } from "../model/User";
import { BaseConfigAdapter } from "./BaseConfigAdapter";

export class PametConfig {
    /**
     * A wrapper to access and modify user settings, device settings,
     * project metadata, and possibly other light config items that will be
     * stored in the local storage
     */
    private _adapter: BaseConfigAdapter;

    constructor(adapter: BaseConfigAdapter) {
        this._adapter = adapter;
    }

    setUpdateHandler(handler: () => void) {
        this._adapter.setUpdateHandler(handler);
    }

    clear() {
        this._adapter.clear();
    }

    get userData() : UserData | undefined {
        let userData = this._adapter.get('user');
        if (userData) {
            return userData as UserData;
        } else {
            return undefined;
        }
    }
    set userData(userData: UserData) {
        this._adapter.set('user', userData);
    }

    get deviceData() : DeviceData | undefined {
        let deviceData = this._adapter.get('device');
        if (deviceData) {
            return deviceData as DeviceData;
        } else {
            return undefined;
        }
    }
    set deviceData(deviceData: DeviceData) {
        this._adapter.set('device', deviceData);
    }
}

