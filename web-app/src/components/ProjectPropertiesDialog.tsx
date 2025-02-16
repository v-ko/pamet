import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import type { ProjectData } from 'web-app/src/model/config/Project';
import { appActions } from '../actions/app';

interface ProjectPropertiesDialogProps {
  project: ProjectData;
  onClose: () => void;
  onSave: (project: ProjectData) => void;
  // onDelete: (project: ProjectData) => void;
}

export function ProjectPropertiesDialog({
  project,
  onClose,
  onSave,
  // onDelete
}: ProjectPropertiesDialogProps) {
  const [projectId, setProjectId] = useState(project.id);

  function onDelete(project: ProjectData) {
    onClose();

    // Confirmation dialog
    const confirmed = window.confirm('Are you sure you want to delete this project from local storage?');
    if (!confirmed) return;

    appActions.startProjectDeletionProcedure(project);
  }

  return (
    <Dialog.Root open={true} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.4)',
            position: 'fixed',
            inset: 0,
            animation: 'overlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1)'
          }}
        />
        <Dialog.Content
          style={{
            backgroundColor: 'white',
            borderRadius: '4px',
            boxShadow: 'hsl(206 22% 7% / 35%) 0px 10px 38px -10px',
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '90vw',
            maxWidth: '300px',
            padding: '16px',
            animation: 'contentShow 150ms cubic-bezier(0.16, 1, 0.3, 1)'
          }}
        >
          <Dialog.Title style={{ margin: 0, marginBottom: '12px' }}>
            Project Properties
          </Dialog.Title>

          <form
            style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
            onSubmit={(e) => {
              e.preventDefault();
              const updatedProject = project;
              updatedProject.id = projectId;
              onSave(updatedProject);
              onClose();
            }}
          >
            <input
              type="text"
              value={projectId}
              onChange={e => setProjectId(e.target.value)}
              disabled
              title="Project ID changing is not implemented yet"
              style={{
                padding: '4px',
                backgroundColor: '#f5f5f5',
                cursor: 'not-allowed',
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
              <button
                type="submit"
                disabled
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '4px',
                  backgroundColor: '#f5f5f5',
                  cursor: 'not-allowed'
                }}
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => onDelete(project)}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '4px',
                  backgroundColor: '#dc3545',
                  color: 'white',
                  cursor: 'pointer'
                }}
              >
                Delete Project
              </button>
            </div>
          </form>

          <Dialog.Close
            style={{
              position: 'absolute',
              top: '10px',
              right: '10px',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontSize: '18px'
            }}
          >
            ×
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
