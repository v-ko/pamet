import { useState, useEffect, useRef, FormEvent } from 'react';
import { pamet } from '@/app/facade';
import { timestamp, currentTime } from 'fusion/util/base';
import { createProject, navigateToProject } from "@/procedures/app";
import { ProjectData } from '@/model/Project';
import "@/views/dialogs/Dialog.css";

interface CreateProjectDialogProps {
  onClose: () => void;
}

const projectIdRegex = /^[a-z0-9-_]{1,40}$/;

export function CreateProjectDialog({ onClose }: CreateProjectDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState('');
  const [id, setId] = useState('');
  const [description, setDescription] = useState('');
  const [idError, setIdError] = useState<string | null>(null);
  const trackedProjects = pamet.appViewState.trackedProjects;

  function validateId(value: string): string | null {
    if (!value) return null;
    if (!projectIdRegex.test(value)) {
      return 'Project ID can only contain lowercase letters, numbers, dashes and underscores';
    }
    if (trackedProjects.some(p => p.id === value)) {
      return 'This ID is already taken';
    }
    return null;
  }

  function generateId(baseTitle: string): string {
    const baseId = baseTitle.toLowerCase()
      .replace(/[^a-z0-9-\s]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-');

    let uniqueId = baseId;
    let i = 1;
    while (trackedProjects.some(p => p.id === uniqueId)) {
      i++;
      uniqueId = `${baseId}-${i}`;
    }
    return uniqueId;
  }

  function generateDefaultTitle(): string {
    let title = 'Project 1';
    let i = 1;
    while (trackedProjects.some(p => p.title === title)) {
      i++;
      title = `Project ${i}`;
    }
    return title;
  }

  useEffect(() => {
    const dialog = dialogRef.current;
    const titleInput = titleInputRef.current;

    if (dialog && !dialog.open) {
      dialog.showModal();
    }

    const defaultTitle = generateDefaultTitle();
    setTitle(defaultTitle);
    setId(generateId(defaultTitle));

    // Select the title text after the dialog opens
    setTimeout(() => {
      if (titleInput) {
        titleInput.select();
      }
    }, 0);
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    const error = validateId(id);
    if (error) {
      setIdError(error);
      return;
    }

    const newProject: ProjectData = {
      id,
      title,
      description,
      created: timestamp(currentTime())
    };

    await createProject(newProject);
    await navigateToProject(newProject.id);
    dialogRef.current?.close();
  }

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
      <div className="dialog-content">
        <h3 className="dialog-title">Create Project</h3>
        <form onSubmit={handleCreate} className="form-vertical">
          <div className="field">
            <input
              ref={titleInputRef}
              autoFocus
              placeholder="Project Title"
              value={title}
              onChange={e => {
                const newTitle = e.target.value;
                setTitle(newTitle);
                if (newTitle) {
                  const newId = generateId(newTitle);
                  setId(newId);
                  setIdError(validateId(newId));
                }
              }}
              className="dialog-input"
            />
          </div>

          <div className="field">
            <input
              placeholder="Project ID"
              value={id}
              onChange={e => {
                const newId = e.target.value;
                setId(newId);
                setIdError(validateId(newId));
              }}
              className="dialog-input"
            />
            {idError ? (
              <small className="dialog-error">{idError}</small>
            ) : (
              <small className="dialog-hint">The ID should be short, suitable for an url.</small>
            )}
          </div>

          <div className="field">
            <textarea
              placeholder="Project Description"
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="dialog-textarea"
            />
          </div>

          <div className="dialog-actions" style={{ justifyContent: 'flex-end' }}>
            <button className="btn btn-primary" type="submit" disabled={!id.trim() || !title.trim() || idError !== null}>
              Create
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
