import { getLogger } from "fusion/logging";
import { buildRestApiAuthHeaders, RestApiAuthConfig } from "fusion/storage/rest-api/Auth";
import { BaseConfigAdapter } from "@/services/config/BaseConfigAdapter";

const log = getLogger("RestDesktopConfigAdapter");

type DesktopSettingsPayload = Record<string, unknown> | undefined;

export class RestDesktopConfigAdapter extends BaseConfigAdapter {
    private _baseUrl: string;
    private _auth: RestApiAuthConfig;
    private _cache: Map<string, string> = new Map();
    private _handler = () => { };

    constructor(baseUrl: string, auth: RestApiAuthConfig) {
        super();
        this._baseUrl = baseUrl;
        this._auth = auth;
    }

    async initialize(): Promise<void> {
        const response = await fetch(this._url("/desktop/settings/user"), {
            method: "GET",
            headers: this._headers(),
            cache: "no-store",
        });
        if (!response.ok) {
            throw new Error(`Failed to load desktop user settings (${response.status} ${response.statusText})`);
        }
        const payload = await response.json() as DesktopSettingsPayload;
        this._cache.clear();
        if (payload !== undefined) {
            this._cache.set("userSettings", JSON.stringify(payload));
        }
    }

    getJSON(key: string): string | undefined {
        return this._cache.get(key);
    }

    setJSON(key: string, value: string | undefined): void {
        if (value === undefined) {
            this._cache.delete(key);
        } else {
            this._cache.set(key, value);
        }
        this._handler();
        void this._persist(key, value);
    }

    keys(): string[] {
        return [...this._cache.keys()];
    }

    setUpdateHandler(handler: () => void): void {
        this._handler = handler;
    }

    private _headers(): HeadersInit {
        return buildRestApiAuthHeaders(this._auth);
    }

    private _url(path: string): string {
        const normalizedPath = path.startsWith("/") ? path : `/${path}`;
        return new URL(`${this._baseUrl}${normalizedPath}`).toString();
    }

    private async _persist(key: string, value: string | undefined): Promise<void> {
        if (key !== "userSettings") {
            log.error(`Unsupported desktop settings key ${key}`);
            return;
        }

        const response = await fetch(this._url("/desktop/settings/user"), {
            method: "PUT",
            headers: {
                ...this._headers(),
                "Content-Type": "application/json",
            },
            body: value === undefined ? JSON.stringify({}) : value,
        });

        if (!response.ok) {
            log.error(`Failed to persist desktop setting ${key}`, response.status, response.statusText);
        }
    }
}
