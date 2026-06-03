import { Entity, EntityData, entityType } from "sivkit/model/Entity"
import { ProjectReference } from "@/model/Project";
import { ThemePreference } from "@/app/theme";

/**
 * Script-related settings. Schema mirrored in
 * `pamet/server/pamet/storage/migrations/v4_to_v5.py::_build_v5_script_settings`.
 */
export interface ScriptSettings {
    /**
     * Per-path/per-folder allowlist. Key = canonicalized absolute path
     * (file or directory). Value = ISO timestamp of when the user clicked
     * "Always allow". Folder entries grant trust to all scripts under them.
     */
    accepted_paths?: Record<string, string>;
    run_in_terminal_prefix?: {
        posix?: string;
        windows?: string;
    };
    limits?: {
        max_concurrent_jobs_per_project?: number;
        output_ring_buffer_bytes?: number;
        kill_grace_seconds?: number;
    };
}

export interface UserSettingsData extends EntityData {
    userId?: string;
    userName?: string;
    projects?: ProjectReference[];
    themePreference?: ThemePreference;
    scripts?: ScriptSettings;
}

@entityType('UserSettings')
export class UserSettings extends Entity<UserSettingsData> {
    static readonly SINGLETON_ID = 'user-settings';

    get userId(): string | undefined { return this._data.userId; }
    set userId(value: string | undefined) { this._data.userId = value; }

    get userName(): string | undefined { return this._data.userName; }
    set userName(value: string | undefined) { this._data.userName = value; }

    get projects(): ProjectReference[] { return this._data.projects ?? []; }
    set projects(value: ProjectReference[]) { this._data.projects = value; }

    get themePreference(): ThemePreference | undefined { return this._data.themePreference; }
    set themePreference(value: ThemePreference | undefined) { this._data.themePreference = value; }

    get scripts(): ScriptSettings { return this._data.scripts ?? {}; }
    set scripts(value: ScriptSettings) { this._data.scripts = value; }
}
