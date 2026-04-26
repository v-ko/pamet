import React from "react";
import { observer } from "mobx-react-lite";
import { action } from "mobx";
import { BackupPanelViewState, BackupEntry } from "@/views/replay/BackupViewState";
import { replayActions } from "@/actions/replay";
import { pamet } from "@/app/facade";
import "@/views/replay/BackupsPane.css";

/**
 * Sidebar pane listing backup entries for the current page.
 * Styled like the GlobalSearch sidebar — lives in the panel-layer grid.
 */
export const BackupsPane = observer(({
    state,
}: {
    state: BackupPanelViewState;
}) => {
    const closePane = () => replayActions.closeBackups(pamet.appViewState);
    const selectBackup = action((id: string) => {
        state.selectedBackupId = state.selectedBackupId === id ? null : id;
    });

    const fmtTime = (ms: number) => {
        const d = new Date(ms);
        return d.toLocaleDateString(undefined, {
            month: "short", day: "numeric", year: "numeric",
            hour: "2-digit", minute: "2-digit",
        });
    };

    return (
        <div className="backups-pane">
            <div className="backups-pane-header">
                <span className="backups-pane-title">Backups</span>
                <button
                    className="backups-pane-close"
                    onClick={closePane}
                    title="Close backups"
                >✕</button>
            </div>
            <ul className="backups-pane-list">
                {state.backups.length === 0 && (
                    <li className="backups-pane-empty">No backups available.</li>
                )}
                {state.backups.map((entry: BackupEntry) => (
                    <li
                        key={entry.id}
                        className={`backups-pane-item${state.selectedBackupId === entry.id ? " selected" : ""}`}
                        onClick={() => selectBackup(entry.id)}
                    >
                        <div className="backups-pane-item-label">{entry.label}</div>
                        <div className="backups-pane-item-time">{fmtTime(entry.timestamp)}</div>
                    </li>
                ))}
            </ul>
        </div>
    );
});
