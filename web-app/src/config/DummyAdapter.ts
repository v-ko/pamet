import { BaseConfigAdapter } from "./BaseConfigAdapter";

export class DummyConfigAdapter extends BaseConfigAdapter {
    private _data: any = {};
    private _updateHandler = () => {};

    getJSON(key: string): any {
        return this._data[key];
    }
    setJSON(key: string, value: string | undefined): void {
        if (value === undefined) {
            delete this._data[key];
        } else {
            this._data[key] = value;
        }
        this._updateHandler();
    }
    keys(): string[] {
        return Object.keys(this._data);
    }
    setUpdateHandler(handler: () => void) {
        this._updateHandler = handler;
    }
}
