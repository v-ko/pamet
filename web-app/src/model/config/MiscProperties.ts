import { Entity, EntityData, entityType } from "fusion/model/Entity"
import { ProjectReference } from "@/model/Project";

export interface MiscPropertiesData extends EntityData {
    deviceId?: string;
    recentProjects?: ProjectReference[];
}

@entityType('MiscProperties')
export class MiscProperties extends Entity<MiscPropertiesData> {
    static readonly SINGLETON_ID = 'misc';

    get deviceId(): string | undefined { return this._data.deviceId; }
    set deviceId(value: string | undefined) { this._data.deviceId = value; }

    get recentProjects(): ProjectReference[] { return this._data.recentProjects ?? []; }
    set recentProjects(value: ProjectReference[]) { this._data.recentProjects = value; }
}
