import { Entity, EntityData, entityType } from "fusion/model/Entity"

export interface ProjectPropertiesData extends EntityData {
    projectId: string;
    title: string;
    description: string;
    created: string;
    home_page_id?: string;
    backups_enabled?: boolean;
}

@entityType('ProjectProperties')
export class ProjectProperties extends Entity<ProjectPropertiesData> {
    static idForProject(projectId: string): string {
        return `project-props-${projectId}`;
    }

    get projectId(): string { return this._data.projectId; }

    get title(): string { return this._data.title; }
    set title(value: string) { this._data.title = value; }

    get description(): string { return this._data.description; }
    set description(value: string) { this._data.description = value; }

    get created(): string { return this._data.created; }

    get homePageId(): string | undefined { return this._data.home_page_id; }
    set homePageId(value: string | undefined) { this._data.home_page_id = value; }

    get backupsEnabled(): boolean { return this._data.backups_enabled ?? true; }
    set backupsEnabled(value: boolean) { this._data.backups_enabled = value; }
}
