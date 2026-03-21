import type { ProjectData } from "fusion/storage/management/StorageService";

export type { ProjectData };

export interface ProjectReference {
    id: string;
    title: string;
    uri: string;
}

export interface PametProjectProperties {
    defaultPageId?: string;
    [key: string]: unknown;
}

export interface PametProjectData extends ProjectData {
    properties?: PametProjectProperties;
}
