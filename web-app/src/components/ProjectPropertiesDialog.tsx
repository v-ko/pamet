import { useState, useRef, useEffect } from 'react';
import type { ProjectData } from '@/model/config/Project';
import { projectActions } from "@/actions/project";
import { pamet } from "@/core/facade";
import { deleteProjectAndSwitch } from '@/procedures/app';
import { getLogger } from 'fusion/logging';

let log = getLogger("ProjectPropertiesDialog");

interface ProjectPropertiesDialogProps {
  project: ProjectData;
  onClose: () => void;
}

export function ProjectPropertiesDialog({ project, onClose }: ProjectPropertiesDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [title, setTitle] = useState(project.title);
  const [titleError, setTitleError] = useState<string | null>(null);

  function validateTitle(value: string): string | null {
    if (!value.trim()) {
      return 'Title is required';
    }
    if (pamet.projects().some(p => p.title === value && p.id !== project.id)) {
      return 'A project with this title already exists';
    }
    return null;
  }

  function onDelete(project: ProjectData) {
    // Confirmation dialog
    const confirmed = window.confirm('Are you sure you want to delete this project from local storage?');
    if (!confirmed) return;

    onClose();
    deleteProjectAndSwitch(project).catch((e) => {
      log.error("Error in startProjectDeletionProcedure", e);
    });
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
      style={{
        border: 'none',
        borderRadius: '4px',
        padding: '16px',
        backgroundColor: 'white',
        boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
        maxWidth: '300px',
        width: '90vw'
      }}
    >
      <h3 style={{ margin: 0, marginBottom: '12px' }}>Project Properties</h3>

      <form
        method="dialog"
        style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
        onSubmit={(e) => {
          // Note: when the form method is "dialog", the submit event fires, but
          // the default action is to close the dialog, not to submit the form.
          // So we can just do our thing here and not call e.preventDefault()
          if (titleError) return;

          const updatedProject = {
            ...project,
            title: title.trim()
          };

          try {
            projectActions.updateProject(updatedProject);
            // No need to call onClose, the dialog will close automatically
          } catch (error) {
            setTitleError((error as Error).message);
          }
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <input
            type="text"
            value={title}
            onChange={e => {
              const newTitle = e.target.value;
              setTitle(newTitle);
              setTitleError(validateTitle(newTitle));
            }}
            placeholder="Project Title"
            style={{
              padding: '4px',
              border: '1px solid #ddd',
              borderRadius: '4px'
            }}
          />
          {titleError && (
            <small style={{ color: 'red' }}>{titleError}</small>
          )}
        </div>

        <input
          type="text"
          value={project.id}
          disabled
          title="Project ID cannot be changed"
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
            disabled={!title.trim() || titleError !== null}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: titleError || !title.trim() ? '#f5f5f5' : '#0066cc',
              color: titleError || !title.trim() ? '#666' : 'white',
              cursor: titleError || !title.trim() ? 'not-allowed' : 'pointer'
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

      <button
        formMethod="dialog"
        formNoValidate
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
      </button>
    </dialog>
  );
}
