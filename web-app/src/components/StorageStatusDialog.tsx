import { useEffect, useRef, useState } from "react";
import "@/components/dialogs/Dialog.css";
import { WebAppState } from "@/containers/app/WebAppState";
import { getLogger } from "fusion/logging";

const log = getLogger("StorageStatusDialog");

interface BackupServiceStatus {
  present: boolean;
  backups_enabled: boolean;
  backup_folder: string;
}

interface DSSStatus {
  errors: Record<string, Record<string, string>>;
  backup_service: Record<string, BackupServiceStatus>;
}

interface StorageStatusDialogProps {
  state: WebAppState;
  onClose: () => void;
}

function formatTimestamp(timestamp: number | null): string {
  if (timestamp === null) {
    return "Never";
  }
  return new Date(timestamp).toLocaleString();
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

export function StorageStatusDialog({ state, onClose }: StorageStatusDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const s = state.storageState.service;
  const [dssStatus, setDssStatus] = useState<DSSStatus | null>(null);
  const [dssError, setDssError] = useState<string | null>(null);

  const projectId = s.activeProjectId;
  const backupStatus = projectId && dssStatus?.backup_service?.[projectId];
  const isDesktop = !!window.PAMET_DESKTOP_API_BASE_URL;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }
  }, []);

  useEffect(() => {
    if (!isDesktop) return;
    desktopFetch("/status")
      .then(r => {
        if (!r.ok) throw new Error(`Status fetch failed: ${r.status}`);
        return r.json();
      })
      .then(data => setDssStatus(data))
      .catch(e => {
        log.error("Failed to fetch DSS status", e);
        setDssError(e.message);
      });
  }, [isDesktop]);

  function openBackupsFolder() {
    if (!projectId) return;
    desktopFetch(`/commands/open_backups_folder/`, {
      method: "POST",
      body: JSON.stringify({ project_id: projectId }),
    }).catch(e => log.error("Failed to open backups folder", e));
  }

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }
  }, []);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) {
          onClose();
        }
      }}
      className="app-dialog"
    >
      <div className="dialog-content" style={{ fontSize: '0.9em', color: 'var(--color-text-muted, #666)' }}>
        <div className="row-between">
          <h3 className="dialog-title" style={{ color: 'var(--color-text)' }}>Storage Status</h3>
          <button
            type="button"
            className="icon-button dialog-close"
            onClick={() => dialogRef.current?.close()}
          >
            x
          </button>
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
              >
                Open Backups Folder
              </button>
            </div>
          </>
        )}

        {isDesktop && dssStatus && (
          <>
            <h4 style={{ margin: 0, color: 'var(--color-text)' }}>Desktop Storage Service</h4>
            <hr style={{ border: 'none', borderTop: '1px solid var(--color-light-border)', width: '100%', margin: '0' }} />
            {(() => {
              const errorItems = Object.entries(dssStatus.errors).flatMap(([service, errors]) =>
                Object.entries(errors).map(([errType, msg]) => ({ key: `${service}-${errType}`, service, msg }))
              );
              return errorItems.length > 0 ? (
                errorItems.map(({ key, service, msg }) => (
                  <div key={key} className="dialog-error">
                    <strong>{service}:</strong> {msg}
                  </div>
                ))
              ) : (
                <div>No errors.</div>
              );
            })()}
          </>
        )}

        <h4 style={{ margin: 0, color: 'var(--color-text)' }}>Frontend Storage Service</h4>
        <hr style={{ border: 'none', borderTop: '1px solid var(--color-light-border)', width: '100%', margin: '0' }} />

        <div title="Backend / connection / worker lifecycle / project bridge">
          <strong>Service Worker:</strong> {s.backend} · {s.connectionPhase} · {s.workerLifecycle} · project {s.projectPhase}
        </div>
        <div title="The project ID currently loaded in the storage service (matches the URL route).">
          <strong>Active Project:</strong> {s.activeProjectId ?? "none"}
        </div>
        <div title="Overall readiness: true when the service worker link is alive and a project is attached.">
          <strong>Ready:</strong> {s.connected ? "yes" : "no"}
        </div>

        <div className="field">
          <strong>Last Error</strong>
          {s.lastError ? (
            <>
              <div title="Error classification code.">
                <strong>Code:</strong> {s.lastError.code}
              </div>
              <div title="The storage operation that was in progress when the error occurred.">
                <strong>Operation:</strong> {s.lastError.operation ?? "none"}
              </div>
              <div><strong>Message:</strong> {s.lastError.message}</div>
              <div><strong>When:</strong> {formatTimestamp(s.lastError.timestamp)}</div>
              {s.lastError.reloadRecommended && (
                <div className="dialog-hint">Reload the page to restore service-worker storage.</div>
              )}
              {!s.lastError.reloadRecommended && s.lastError.recoverable && (
                <div className="dialog-hint">The next storage action will try to reconnect once.</div>
              )}
            </>
          ) : (
            <div>No errors recorded.</div>
          )}
        </div>

        {isDesktop && dssError && (
          <div className="dialog-error">
            Failed to fetch backend status: {dssError}
          </div>
        )}
      </div>
    </dialog>
  );
}
