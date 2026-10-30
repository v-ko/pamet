import { observer } from 'mobx-react-lite';
import { useEffect, useRef } from "react";
import "@/views/dialogs/Dialog.css";
import { AppViewState } from "@/views/AppViewState";
import { PametTabIndex } from '@/app/constants';
import { getLogger } from "sivkit/logging";

const log = getLogger("StorageStatusDialog");

interface StorageStatusDialogProps {
  state: AppViewState;
  onClose: () => void;
}

function desktopFetch(path: string, options?: RequestInit): Promise<Response> {
  const baseUrl = window.PAMET_DESKTOP_API_BASE_URL;
  const token = window.PAMET_DESKTOP_ACCESS_TOKEN;
  if (!baseUrl || !token) {
    return Promise.reject(new Error("Desktop API not available"));
  }
  return fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
}

export const StorageStatusDialog = observer(function StorageStatusDialog({ state, onClose }: StorageStatusDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const s = state.storageState.service;
  const projectId = s.activeProjectId;
  const project = state.currentStorageProject;
  const backupStatus = project?.backup;
  const errors = state.storageErrors;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }
  }, []);

  function openBackupsFolder() {
    if (!projectId) return;
    desktopFetch(`/desktop/gui/commands/open_backups_folder/`, {
      method: "POST",
      body: JSON.stringify({ project_id: projectId }),
    }).catch(e => log.error("Failed to open backups folder", e));
  }

  const mouseDownOnBackdrop = useRef(false);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onMouseDown={(e) => { mouseDownOnBackdrop.current = e.target === dialogRef.current; }}
      onClick={(e) => {
        if (e.target === dialogRef.current && mouseDownOnBackdrop.current) {
          onClose();
        }
      }}
      className="app-dialog"
    >
      <div className="dialog-content" style={{ fontSize: '0.9em', color: 'var(--color-text-muted, #666)' }}>
        <div className="row-between">
          <h3 className="dialog-title" style={{ color: 'var(--color-text)' }}>Storage Status</h3>
        </div>

        {backupStatus && (
          <>
            <h4 style={{ margin: 0, color: 'var(--color-text)' }}>Backups</h4>
            <hr style={{ border: 'none', borderTop: '1px solid var(--color-light-border)', width: '100%', margin: '0' }} />
            <div title="Whether periodic page snapshots are being created for this project.">
              <strong>Enabled:</strong> {backupStatus.backups_enabled ? "yes" : "no"}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1em' }}>
              <span style={{ fontSize: '0.9em', opacity: 0.8 }}>
                To restore a page, manually copy the backup file over the current one.
                Pages are stored under folders named by page ID, not by title.
              </span>
              <button
                type="button"
                className="btn"
                onClick={openBackupsFolder}
                title="Open the backups folder in your file manager."
                style={{ whiteSpace: 'nowrap' }}
                tabIndex={PametTabIndex.StorageStatusDialog_OpenBackupsFolder}
              >
                Open Backups Folder
              </button>
            </div>
          </>
        )}

        {project && <div><strong>Backend project:</strong> {project.phase}</div>}

        {s.degraded && (
          <div style={{
            padding: '0.5em 0.75em',
            backgroundColor: 'var(--color-danger-bg, #fdecea)',
            color: 'var(--color-danger, #e53935)',
            borderRadius: '4px',
            fontSize: '0.9em',
          }}>
            <strong>Degraded mode:</strong> {s.degradedReason ?? 'Unknown reason'}
            <div style={{ marginTop: '0.3em', opacity: 0.85 }}>
              Storage is running in the main thread. Cross-tab storage sharing is limited.
              Reload the page to retry the SharedWorker.
            </div>
          </div>
        )}

        <div title="Connection phase and project bridge status">
          <strong>Connection:</strong> {s.connectionPhase} · project {s.projectPhase}
        </div>
        <div title="The project ID currently loaded in the storage service (matches the URL route).">
          <strong>Active Project:</strong> {s.activeProjectId ?? "none"}
        </div>

        {errors.length > 0 ? errors.map((message, index) => (
          <div key={index} className="dialog-error">{message}</div>
        )) : <div>No errors recorded.</div>}

        <button
          type="button"
          className="icon-button dialog-close"
          onClick={() => dialogRef.current?.close()}
          tabIndex={-1}
        >
          x
        </button>
      </div>
    </dialog>
  );
});
