import { useState, useRef, useEffect } from 'react';
import type { ProjectData } from '@/model/config/Project';
import { projectActions } from "@/actions/project";
import { pamet } from "@/core/facade";
import { deleteProjectAndSwitch } from '@/procedures/app';
import { getLogger } from 'fusion/logging';
import "@/components/dialogs/Dialog.css";

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
      className="app-dialog"
    >
      <h3 className="dialog-title">Project Properties</h3>
      <button
        type="button"
        className="icon-button dialog-close"
        onClick={() => dialogRef.current?.close()}
      >
        ×
      </button>

      <form
        method="dialog"
        className="form-vertical"
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
        <div className="field">
          <input
            type="text"
            value={title}
            onChange={e => {
              const newTitle = e.target.value;
              setTitle(newTitle);
              setTitleError(validateTitle(newTitle));
            }}
            placeholder="Project Title"
            className="dialog-input"
          />
          {titleError && (
            <small className="dialog-error">{titleError}</small>
          )}
        </div>

        <input
          type="text"
          value={project.id}
          disabled
          title="Project ID cannot be changed"
          className="dialog-input"
        />

        <div className="dialog-actions row-between">
          <button
            type="button"
            onClick={() => onDelete(project)}
            className="btn btn-danger"
          >
            Delete Project
          </button>
          <button
            type="submit"
            disabled={!title.trim() || titleError !== null}
            className="btn btn-primary"
          >
            Save
          </button>
        </div>
      </form>

      
    </dialog>
  );
}
