import { useState, useEffect, useRef } from 'react';
import { pamet } from 'web-app/src/core/facade';
import type { ProjectData } from 'web-app/src/model/config/Project';

interface ProjectsDialogProps {
  onClose: () => void;
}

export function ProjectsDialog({ onClose }: ProjectsDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const projects = pamet.projects();

  // Open dialog on mount
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (!dialog.open) {
      dialog.showModal();
    }
  }, []);

  // Close helper
  function handleClose() {
    const dialog = dialogRef.current;
    if (dialog?.open) {
      dialog.close();
    }
    onClose();
  }

  // Close dialog on background click
  function handleBackgroundClick(event: React.MouseEvent) {
    if (event.target === dialogRef.current) {
      handleClose();
    }
  }

  return (
    <dialog
      ref={dialogRef}
      onCancel={handleClose}
      onClick={handleBackgroundClick}
      style={{
        border: 'none',
        borderRadius: '4px',
        padding: '16px',
        maxWidth: '400px',
        width: '100%'
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
            onClick={() => alert('Create project not implemented yet')}
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
              <span>{project.name}</span>
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
