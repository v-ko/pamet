import { useRef, useEffect } from 'react';
import { pamet } from '@/core/facade';
import { appActions } from '@/actions/app';
import { PametRoute } from "@/services/routing/route";
import { getLogger } from 'fusion/logging';

let log = getLogger('ProjectsDialog')

interface ProjectsDialogProps {
  onClose: () => void;
}

export function ProjectsDialog({ onClose }: ProjectsDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const projects = pamet.projects();

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
        if (e.target === dialogRef.current) { // Close on outside click
            onClose();
        }
      }}
      style={{
        border: 'none',
        borderRadius: '4px',
        padding: '16px',
        backgroundColor: 'white',
        boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
        maxWidth: '400px',
        width: '90vw'
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ margin: 0 }}>Projects</h3>
          <button
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              fontSize: '20px',
              color: '#007bff'
            }}
            title="Create new project"
            onClick={() => {
              appActions.openCreateProjectDialog(pamet.appViewState);
            }}
          >
            +
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {projects.map((project) => (
            <div
              key={project.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px',
                backgroundColor: '#f5f5f5',
                borderRadius: '4px'
              }}
            >
              <a
                href={(() => {
                  const userId = pamet.appViewState.userId;
                  if (!userId) {
                    log.error('Trying to open projects dialog with no userId set')
                    return;
                  }
                  const route = new PametRoute(({
                    userId: userId,
                    projectId: project.id}));
                  return route.toRelativeReference();
                })()}
                onClick={onClose}
                style={{
                  flex: 1,
                  padding: '4px',
                  color: 'inherit',
                  textDecoration: 'none',
                  cursor: 'pointer'
                }}
              >
                {project.title}
              </a>
              <button
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '4px',
                  fontSize: '16px'
                }}
                title="Project menu"
              >
                ⋮
              </button>
            </div>
          ))}
        </div>
      </div>
    </dialog>
  );
}
