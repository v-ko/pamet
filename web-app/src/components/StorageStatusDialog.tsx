import { useEffect, useRef } from "react";
import "@/components/dialogs/Dialog.css";
import { WebAppState } from "@/containers/app/WebAppState";

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

export function StorageStatusDialog({ state, onClose }: StorageStatusDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const serviceState = state.storageState.service;

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
      <div className="dialog-content">
        <div className="row-between">
          <h3 className="dialog-title">Storage Status</h3>
          <button
            type="button"
            className="icon-button dialog-close"
            onClick={() => dialogRef.current?.close()}
          >
            x
          </button>
        </div>

        <div><strong>Backend:</strong> {serviceState.backend}</div>
        <div><strong>Connection:</strong> {serviceState.connectionPhase}</div>
        <div><strong>Project:</strong> {serviceState.projectPhase}</div>
        <div><strong>Active Project ID:</strong> {serviceState.activeProjectId ?? "none"}</div>
        <div><strong>Connected:</strong> {serviceState.connected ? "yes" : "no"}</div>
        <div><strong>Service Worker State:</strong> {serviceState.workerLifecycle}</div>
        <div><strong>Last Ready:</strong> {formatTimestamp(serviceState.lastReadyAt)}</div>

        <div className="field">
          <strong>Latest Error</strong>
          {serviceState.lastError ? (
            <>
              <div><strong>Code:</strong> {serviceState.lastError.code}</div>
              <div><strong>Operation:</strong> {serviceState.lastError.operation ?? "none"}</div>
              <div><strong>Message:</strong> {serviceState.lastError.message}</div>
              <div><strong>When:</strong> {formatTimestamp(serviceState.lastError.timestamp)}</div>
              {serviceState.lastError.reloadRecommended && (
                <div className="dialog-hint">Reload the page to restore service-worker storage.</div>
              )}
              {!serviceState.lastError.reloadRecommended && serviceState.lastError.recoverable && (
                <div className="dialog-hint">The next storage action will try to reconnect once.</div>
              )}
            </>
          ) : (
            <div>No errors recorded.</div>
          )}
        </div>
      </div>
    </dialog>
  );
}
