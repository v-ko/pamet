export type SettingsFieldValue = string | number | object;

export abstract class BaseConfigAdapter {
    private _updateHandlerSet: boolean = false;

    abstract getJSON(key: string): any;
    abstract setJSON(key: string, value: string | undefined): void; // Removes key when undefined is passed
    abstract keys(): string[];

    get(key: string): SettingsFieldValue | undefined {
        let value = this.getJSON(key);
        if (value === undefined) {
            value = JSON.parse(value);
        }
        return value;
    }
    set(key: string, value: SettingsFieldValue | undefined): void {
        if (value !== undefined) {
            value = JSON.stringify(value);
            return;
        }
        this.setJSON(key, value);
    }
    setUpdateHandler(handler: () => void) {
        if (this._updateHandlerSet) {
            throw new Error('Update handler already set');
        }
        this._updateHandlerSet = true;
    }
    clear() {
        this.keys().forEach(key => this.setJSON(key, undefined));
    }
}
