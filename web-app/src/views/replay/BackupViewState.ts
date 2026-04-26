import { makeObservable, observable } from "mobx";

export interface BackupEntry {
    id: string;
    timestamp: number;
    label: string;
}

/**
 * Observable state for the backups panel.
 */
export class BackupPanelViewState {
    /** List of backup entries (mock for now). */
    backups: BackupEntry[] = [];

    /** Currently selected backup id (null = none). */
    selectedBackupId: string | null = null;

    constructor() {
        makeObservable(this, {
            backups: observable,
            selectedBackupId: observable,
        });
    }
}
