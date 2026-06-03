import { Entity, EntityData, entityType } from "sivkit/model/Entity"
import { ProjectReference } from "@/model/Project";

export interface DeviceStateData extends EntityData {
    deviceId?: string;
    recentProjects?: ProjectReference[];
}

@entityType('DeviceState')
export class DeviceState extends Entity<DeviceStateData> {
    static readonly SINGLETON_ID = 'device-state';

    get deviceId(): string | undefined { return this._data.deviceId; }
    set deviceId(value: string | undefined) { this._data.deviceId = value; }

    get recentProjects(): ProjectReference[] { return this._data.recentProjects ?? []; }
    set recentProjects(value: ProjectReference[]) { this._data.recentProjects = value; }
}
