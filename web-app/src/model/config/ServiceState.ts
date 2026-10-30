import { Entity, EntityData, entityType } from 'sivkit/model/Entity';

export interface FileSaveErrorData {
    id: string;
    path: string;
    message: string;
}

export interface ProjectProblem {
    kind: 'unreadable_file' | 'unlisted_folder' | 'duplicate_id';
    path: string;
    reason: string;
}

export interface FileSystemState {
    saving: boolean;
    errors: Record<string, FileSaveErrorData>;
    problems: Record<string, ProjectProblem>;
}

export interface BackupServiceState {
    backups_enabled: boolean;
    backup_folder: string;
    error: string | null;
}

export interface DesktopStorageStateData extends EntityData {
    closing: boolean;
    config_errors: Record<string, string>;
}

export interface ProjectStorageStateData extends EntityData {
    project_id: string;
    phase: 'loading' | 'open' | 'closing';
    filesystem: FileSystemState | null;
    backup: BackupServiceState | null;
    history_error: string | null;
}

@entityType('DesktopStorageState')
export class DesktopStorageState extends Entity<DesktopStorageStateData> {
    static readonly SINGLETON_ID = 'desktop-storage-state';
}

@entityType('ProjectStorageState')
export class ProjectStorageState extends Entity<ProjectStorageStateData> {
    static idForProject(projectId: string): string {
        return `project-storage-state-${projectId}`;
    }
}

export function isServiceStateId(id: string): boolean {
    return id === DesktopStorageState.SINGLETON_ID || id.startsWith('project-storage-state-');
}
