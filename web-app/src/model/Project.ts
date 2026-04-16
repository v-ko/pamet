import type { ProjectData } from "fusion/storage/management/StorageService";

export type { ProjectData };

export interface ProjectReference {
    id: string;
    title: string;
    uri: string;
}

export interface PametProjectData extends ProjectData {
    home_page_id?: string;
    backups_enabled?: boolean;
    'files.exclude'?: Record<string, boolean>;
}
