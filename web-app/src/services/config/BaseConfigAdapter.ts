export type SettingsFieldValue = string | number | object;

export abstract class BaseConfigAdapter {
    abstract getJSON(key: string): any;
    abstract setJSON(key: string, value: string | undefined): void; // Removes key when undefined is passed
    abstract keys(): string[];
    abstract setUpdateHandler(handler: () => void) : void;

    get(key: string): SettingsFieldValue | undefined {
        let value = this.getJSON(key);
        if (value !== undefined) {
            value = JSON.parse(value);
        }
        return value;
    }
    set(key: string, value: SettingsFieldValue | undefined): void {
        if (value !== undefined) {
            value = JSON.stringify(value);
        }
        this.setJSON(key, value);
    }
    clear() {
        this.keys().forEach(key => this.setJSON(key, undefined));
    }
    data(): object {
        let data: { [key: string]: SettingsFieldValue } = {};
        for (const key of this.keys()) {
            data[key] = this.get(key) as SettingsFieldValue;
        }
        return data;
    }
}
