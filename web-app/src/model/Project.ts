import type { ProjectData } from "sivkit/storage/management/StorageService";

export type { ProjectData };

export interface ProjectReference {
    id: string;
    title: string;
    uri: string;
}

export interface PametProjectData extends ProjectData {
    home_page_id?: string;
    backups_enabled: boolean;
    record_all_changes: boolean;
    canvas_palette?: { [mode: string]: { [role: string]: string } };
    files_exclude: Record<string, boolean>;
}

export function defaultProjectSettings() {
    return {
        backups_enabled: true,
        record_all_changes: false,
        files_exclude: { '**/.git': true },
    };
}
