import { useState, useRef, useEffect } from 'react';
import type { PametProjectData } from '@/model/Project';
import { pamet } from "@/app/facade";
import { deleteProjectAndSwitch } from '@/procedures/app';
import { getLogger } from 'fusion/logging';
import { PametTabIndex } from '@/app/constants';
import "@/views/dialogs/Dialog.css";

let log = getLogger("ProjectPropertiesDialog");

interface ProjectPropertiesDialogProps {
  project: PametProjectData;
  onClose: () => void;
}

export function ProjectPropertiesDialog({ project, onClose }: ProjectPropertiesDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [title, setTitle] = useState(project.title);
  const [backupsEnabled, setBackupsEnabled] = useState(project.backups_enabled ?? true);
  const [titleError, setTitleError] = useState<string | null>(null);
  const trackedProjects = pamet.appViewState.trackedProjects;

  const trackedProject = trackedProjects.find(p => p.id === project.id);
  const isFileBacked = trackedProject?.uri?.startsWith('file:///');

  function validateTitle(value: string): string | null {
    if (!value.trim()) {
      return 'Title is required';
    }
    if (trackedProjects.some((p) => p.title === value && p.id !== project.id)) {
      return 'A project with this title already exists';
    }
    return null;
  }

  function onDelete(project: PametProjectData) {
    const confirmMessage = isFileBacked
      ? 'Are you sure you want to disconnect this project? The project folder will be kept on disk.'
      : 'Are you sure you want to delete this project? All data will be permanently removed.';
    const confirmed = window.confirm(confirmMessage);
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
      <h3 className="dialog-title">Project Properties</h3>

      <form
        className="form-vertical"
        onSubmit={async (e) => {
          e.preventDefault();
          if (titleError) return;

          const updatedProject = {
            ...project,
            title: title.trim(),
            backups_enabled: backupsEnabled,
          };

          try {
            pamet.saveProjectProperties(updatedProject);
            dialogRef.current?.close();
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
            tabIndex={PametTabIndex.ProjectPropertiesDialog_TitleInput}
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

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          title="When enabled, page snapshots are periodically saved to the .pamet/backups/ folder.">
          <input
            type="checkbox"
            checked={backupsEnabled}
            onChange={e => setBackupsEnabled(e.target.checked)}
            tabIndex={PametTabIndex.ProjectPropertiesDialog_BackupsCheckbox}
          />
          Backups enabled
        </label>

        <div className="dialog-actions row-between">
          <button
            type="button"
            onClick={() => onDelete(project)}
            className="btn btn-danger"
            tabIndex={PametTabIndex.ProjectPropertiesDialog_Delete}
          >
            {isFileBacked ? 'Disconnect Project' : 'Delete Project'}
          </button>
          <button
            type="submit"
            disabled={!title.trim() || titleError !== null}
            className="btn btn-primary"
            tabIndex={PametTabIndex.ProjectPropertiesDialog_Save}
          >
            Save
          </button>
        </div>
      </form>
      <button
        type="button"
        className="icon-button dialog-close"
        onClick={() => dialogRef.current?.close()}
        tabIndex={-1}
      >
        ×
      </button>

    </dialog>
  );
}
