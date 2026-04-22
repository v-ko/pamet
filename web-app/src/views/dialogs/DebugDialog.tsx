import React, { useEffect, useRef, useState } from 'react';
import { pamet } from "@/app/facade";
import { Entity } from 'fusion/model/Entity';
import { PametTabIndex } from '@/app/constants';
import { restartStorageWorker } from '@/procedures/app';

interface DebugDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ProblematicEntityInfo {
  id: string;
  count: number;
  firstError?: string;
  entity: Entity<any>;
}

export const DebugDialog: React.FC<DebugDialogProps> = ({ isOpen, onClose }) => {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [commitStats, setCommitStats] = useState<any>(null);
  const [fdsState, setFdsState] = useState<any>(null);
  const [problematicEntities, setProblematicEntities] = useState<ProblematicEntityInfo[]>([]);
  const [mobxStateSize, setMobxStateSize] = useState<number | null>(null);
  const [debugPaintOperations, setDebugPaintOperations] = useState(pamet.debugPaintOperations);

    let configDataJson: string;
    try {
        configDataJson = JSON.stringify(pamet.getUserData(), null, 2);
    } catch {
        configDataJson = '(config store not ready)';
    }

    const handleDebugPaintOperationsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = event.target.checked;
        pamet.debugPaintOperations = newValue;
        setDebugPaintOperations(newValue);
    };

  useEffect(() => {
    if (isOpen) {
        // Update the problematic entities list every time the dialog is opened.
        const problematicEntitiesMap = pamet._entityProblemCounts;
        const entitiesInfo: ProblematicEntityInfo[] = [];

        for (const [entityId, entry] of problematicEntitiesMap.entries()) {
            const entity = pamet.findOne({ id: entityId });
            if (entity) {
                const firstError = entry.firstError
                    ? (entry.firstError instanceof Error ? entry.firstError.stack || entry.firstError.message : String(entry.firstError))
                    : undefined;
                entitiesInfo.push({ id: entityId, count: entry.count, firstError, entity });
            }
        }
        setProblematicEntities(entitiesInfo);
    }
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [isOpen]);

  const fetchCommitStats = async () => {
    try {
      const currentProjectId = pamet.appViewState.currentProjectId;
      console.log('Fetching commit stats for project ID:', currentProjectId);
      if (currentProjectId) {
        // Get commit graph and commits from storage service
        const commitGraphData = await pamet.storageService.getCommitGraph(currentProjectId);
        const allCommitIds = commitGraphData.commits.map(c => c.id);
        const commits = allCommitIds.length > 0 ? await pamet.storageService.getCommits(currentProjectId, allCommitIds) : [];

        // Calculate statistics
        const branches = commitGraphData.branches;
        const currentBranch = 'main'; // Default branch
        const headCommit = branches.find(b => b.name === currentBranch);

        // Get commits for current branch (simplified - just show all for now)
        const commitStats = commits.map(commit => ({
          id: commit.id.substring(0, 8),
          message: commit.message,
          timestamp: new Date(commit.timestamp).toLocaleString(),
          deltaSize: JSON.stringify(commit.deltaData).length
        }));

        setCommitStats({
          branches: branches,
          headCommitId: headCommit?.headCommitId?.substring(0, 8) || 'none',
          totalCommits: commits.length,
          commits: commitStats
        });
      }
    } catch (error) {
      console.error('Error fetching commit stats:', error);
      setCommitStats({ error: String(error) });
    }
  };

  const a_restartStorageWorker = async () => {
    try {
        await restartStorageWorker();
    } catch (error) {
        console.error('Error restarting storage worker:', error);
        alert('Error restarting storage worker. See console for details.');
    }
    };

  const fetchFdsState = () => {
    try {
      console.log('Fetching FDS state');
      const fdsData = pamet.currentProjectStore.data();
      setFdsState(fdsData);
    } catch (error) {
      console.error('Error fetching FDS state:', error);
      setFdsState({ error: String(error) });
    }
  };

  const calculateMobxStateSize = () => {
    try {
      const mobxState = pamet.appViewState;
      const jsonString = JSON.stringify(mobxState);
      const sizeInBytes = new Blob([jsonString]).size;
      setMobxStateSize(sizeInBytes);
    } catch (error) {
      console.error('Error calculating MobX state size:', error);
      setMobxStateSize(null);
      alert('Error calculating MobX state size. See console for details.');
    }
  };

  const mouseDownOnBackdrop = useRef(false);

  return (
    <dialog
      ref={dialogRef}
      className="debug-info-dialog"
      style={{
        width: '80vw',
        height: '70vh',
      }}
      onCancel={onClose}
      onMouseDown={(e) => { mouseDownOnBackdrop.current = e.target === dialogRef.current; }}
      onClick={(e) => {
        if (e.target === dialogRef.current && mouseDownOnBackdrop.current) {
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
        tabIndex={-1}
      >
        ×
      </button>

      <h2>Debug Info</h2>
      {/* print config collapsible*/}
      <details>
        <summary>Config</summary>
        <pre>{configDataJson}</pre>
      </details>

      {/* Commit stats button and display */}
      <button onClick={fetchCommitStats} tabIndex={PametTabIndex.DebugDialog_FetchCommitStats}>
        Fetch Commit Statistics
      </button>

      {commitStats && (
        <details>
          <summary>Commit Statistics</summary>
          <div style={{
            maxHeight: '300px',
            overflow: 'auto',
            border: '1px solid black',
            padding: '10px'
          }}>
            {commitStats.error ? (
              <p>Error: {commitStats.error}</p>
            ) : (
              <>
                <p><strong>Branches:</strong> {commitStats.branches?.map((b: any) => `${b.name} (${b.headCommitId?.substring(0, 8) || 'empty'})`).join(', ') || 'none'}</p>
                <p><strong>Head Commit:</strong> {commitStats.headCommitId}</p>
                <p><strong>Total Commits:</strong> {commitStats.totalCommits}</p>
                <h4>Commits:</h4>
                {commitStats.commits?.map((commit: any, index: number) => (
                  <div key={index} style={{ marginBottom: '8px', fontSize: '12px' }}>
                    <div><strong>{commit.id}</strong> - {commit.message}</div>
                    <div style={{ color: 'var(--color-text-muted)' }}>{commit.timestamp} | Delta size: {commit.deltaSize} bytes</div>
                  </div>
                )) || <p>No commits</p>}
              </>
            )}
          </div>
        </details>
      )}

      {/* FDS state button and display */}
      <button onClick={fetchFdsState} tabIndex={PametTabIndex.DebugDialog_FetchFdsState}>
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

      {/* Button to calculate MobX state size */}
        <button onClick={calculateMobxStateSize} tabIndex={PametTabIndex.DebugDialog_CalcMobxSize}>
            Calculate MobX State Size
        </button>
        {mobxStateSize !== null && (
            <p>MobX State Size: {(mobxStateSize / 1024).toFixed(2)} KB</p>
        )}

      <button onClick={a_restartStorageWorker} tabIndex={PametTabIndex.DebugDialog_RestartStorageWorker}>
        Restart Storage Worker
      </button>

        <div>
            <label>
                <input
                    type="checkbox"
                    checked={debugPaintOperations}
                    onChange={handleDebugPaintOperationsChange}
                    tabIndex={PametTabIndex.DebugDialog_DebugPaintCheckbox}
                />
                Debug Paint Operations
            </label>
        </div>

      {/* Last render error */}
      {(() => {
        const err = pamet.lastRenderError;
        const count = pamet.renderErrorCount;
        return err ? (
          <details open style={{ marginBottom: '10px' }}>
            <summary style={{ color: 'var(--color-danger)', fontWeight: 'bold' }}>Render Errors ({count})</summary>
            <pre style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              background: '#ffe0e0',
              padding: '5px',
              border: '1px solid #c00',
              marginTop: '5px'
            }}>
              {err.stack || err.message}
            </pre>
          </details>
        ) : null;
      })()}

      {/* Problematic entities display */}
      <details open={problematicEntities.length > 0}>
        <summary>
          Problematic Entities ({problematicEntities.length})
        </summary>
        <div style={{
          maxHeight: '300px',
          overflowY: 'auto',
          border: '1px solid black',
          padding: '10px',
          marginTop: '10px'
        }}>
          {problematicEntities.length > 0 ? (
            problematicEntities.map(info => (
              <details key={info.id}>
                <summary>
                  ID: {info.id}, Type: {info.entity.constructor.name}, Errors: {info.count}
                </summary>
                {info.firstError && (
                  <pre style={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                    background: '#ffe0e0',
                    padding: '5px',
                    border: '1px solid #c00',
                    marginBottom: '5px'
                  }}>
                    {info.firstError}
                  </pre>
                )}
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  background: '#f5f5f5',
                  padding: '5px',
                  border: '1px solid #ddd'
                }}>
                  {JSON.stringify(info.entity.data(), null, 2)}
                </pre>
              </details>
            ))
          ) : (
            <p>No problematic entities found.</p>
          )}
        </div>
      </details>
    </dialog>
  );
};

export default DebugDialog;
