import { Entity, EntityData, entityType } from "fusion/model/Entity"
import { ProjectReference } from "@/model/Project";
import { ThemePreference } from "@/app/theme";

export interface UserSettingsData extends EntityData {
    userId?: string;
    userName?: string;
    projects?: ProjectReference[];
    themePreference?: ThemePreference;
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
}
