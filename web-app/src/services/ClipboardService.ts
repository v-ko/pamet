import { dumpToDict, loadFromDict, SerializedEntityData } from "fusion/model/Entity";
import { Note } from "@/model/Note";
import { Arrow } from "@/model/Arrow";
import { getLogger } from "fusion/logging";

const log = getLogger('ClipboardService');

const CLIPBOARD_KEY = 'pamet_internal_clipboard';

interface SerializedClipboard {
    entities: SerializedEntityData[];
    projectId: string | null;
}

export interface ClipboardData {
    entities: (Note | Arrow)[];
    projectId: string | null;
}

/**
 * Manages localStorage persistence and cross-tab synchronization for the
 * internal clipboard (copy/cut/paste of notes and arrows).
 *
 * The service itself does NOT touch AppViewState — the facade coordinates
 * state updates (via an action) and service pushes, following the same
 * pattern as Router / Config sync.
 */
export class ClipboardService {
    private _onRemoteUpdate: ((data: ClipboardData) => void) | null = null;
    private _suppressPush = false;

    /** Register a callback invoked when another tab updates the clipboard. */
    setRemoteUpdateHandler(handler: (data: ClipboardData) => void) {
        this._onRemoteUpdate = handler;
    }

    /** Start listening for cross-tab storage events. */
    connectListener() {
        window.addEventListener('storage', this._handleStorageEvent);
    }

    /** Load any previously stored clipboard data from localStorage. */
    getInternalClipboard(): ClipboardData {
        try {
            const json = localStorage.getItem(CLIPBOARD_KEY);
            if (json) {
                return this._deserialize(json);
            }
        } catch (e) {
            log.error('Failed to load clipboard from localStorage', e);
        }
        return { entities: [], projectId: null };
    }

    /** Persist clipboard data to localStorage (called by the facade after state update). */
    setInternalClipboard(data: ClipboardData) {
        if (this._suppressPush) return;
        try {
            localStorage.setItem(CLIPBOARD_KEY, this._serialize(data));
        } catch (e) {
            log.error('Failed to save clipboard to localStorage', e);
        }
    }

    dispose() {
        window.removeEventListener('storage', this._handleStorageEvent);
    }

    // --- private ---

    private _handleStorageEvent = (event: StorageEvent) => {
        if (event.key !== CLIPBOARD_KEY) return;

        let data: ClipboardData;
        if (event.newValue) {
            try {
                data = this._deserialize(event.newValue);
            } catch (e) {
                log.error('Failed to deserialize clipboard from storage event', e);
                return;
            }
        } else {
            data = { entities: [], projectId: null };
        }

        // Suppress push so the facade method doesn't echo this back to localStorage
        this._suppressPush = true;
        try {
            this._onRemoteUpdate?.(data);
        } finally {
            this._suppressPush = false;
        }
    };

    private _serialize(data: ClipboardData): string {
        const payload: SerializedClipboard = {
            entities: data.entities.map(e => dumpToDict(e)),
            projectId: data.projectId,
        };
        return JSON.stringify(payload);
    }

    private _deserialize(json: string): ClipboardData {
        const payload: SerializedClipboard = JSON.parse(json);
        const entities = payload.entities.map(d => loadFromDict(d) as Note | Arrow);
        return { entities, projectId: payload.projectId };
    }
}
