import React, { useEffect, useRef, useState } from 'react';
import { pamet } from "@/core/facade";

interface DebugDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DebugDialog: React.FC<DebugDialogProps> = ({ isOpen, onClose }) => {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [repoHeadState, setRepoHeadState] = useState<any>(null);
  const [fdsState, setFdsState] = useState<any>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [isOpen]);

  const fetchRepoHeadState = async () => {
    try {
      const currentProjectId = pamet.appViewState.currentProjectId;
      console.log('Fetching repo head state for project ID:', currentProjectId);
      if (currentProjectId) {
        const headState = await pamet.storageService.headState(currentProjectId);
        setRepoHeadState(headState);
      }
    } catch (error) {
      console.error('Error fetching repo head state:', error);
      setRepoHeadState({ error: String(error) });
    }
  };

  const a_restartServiceWorker = async () => {
    try {
        await pamet.procedures.restartServiceWorker();
    } catch (error) {
        console.error('Error restarting service worker:', error);
        alert('Error restarting service worker. See console for details.');
    }
    };

  const fetchFdsState = () => {
    try {
      console.log('Fetching FDS state');
      const fdsData = pamet.frontendDomainStore.data();
      setFdsState(fdsData);
    } catch (error) {
      console.error('Error fetching FDS state:', error);
      setFdsState({ error: String(error) });
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="debug-info-dialog"
      style={{
        width: '80vw',
        height: '70vh',
      }}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) {
          onClose();
        }
      }}
    >
      <button
        onClick={onClose}
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          background: 'none',
          border: 'none',
          fontSize: '20px',
          cursor: 'pointer',
        }}
      >
        ×
      </button>

      <h2>Debug Info</h2>
      {/* print config collapsible*/}
      <details>
        <summary>Config</summary>
        <pre>{JSON.stringify(pamet.config.data(), null, 2)}</pre>
      </details>

      {/* Repo head state button and display */}
      <button onClick={fetchRepoHeadState}>
        Fetch Repo Head State
      </button>

      {repoHeadState && (
        <details>
          <summary>Repo Head State</summary>
          <pre style={{
            maxHeight: '300px',
            overflow: 'auto',
            border: '1px solid black'
          }}>
            {JSON.stringify(repoHeadState, null, 2)}
          </pre>
        </details>
      )}

      {/* FDS state button and display */}
      <button onClick={fetchFdsState}>
        Fetch FDS State
      </button>

      {fdsState && (
        <details>
          <summary>FDS State</summary>
          <pre style={{
            maxHeight: '300px',
            overflow: 'auto',
            border: '1px solid black'
          }}>
            {JSON.stringify(fdsState, null, 2)}
          </pre>
        </details>
      )}
      <button onClick={a_restartServiceWorker}>
        Restart Service Worker
      </button>
    </dialog>
  );
};

export default DebugDialog;
