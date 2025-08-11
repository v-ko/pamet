import { useState, useEffect, useRef, FormEvent } from 'react';
import { appActions } from '@/actions/app';
import { pamet } from '@/core/facade';
import { timestamp, currentTime } from 'fusion/base-util';
import { switchToProject } from "@/procedures/app";

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

  function validateId(value: string): string | null {
    if (!value) return null;
    if (!projectIdRegex.test(value)) {
      return 'Project ID can only contain lowercase letters, numbers, dashes and underscores';
    }
    if (pamet.projects().some(p => p.id === value)) {
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
    while (pamet.projects().some(p => p.id === uniqueId)) {
      i++;
      uniqueId = `${baseId}-${i}`;
    }
    return uniqueId;
  }

  function generateDefaultTitle(): string {
    let title = 'Project 1';
    let i = 1;
    while (pamet.projects().some(p => p.title === title)) {
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

  function handleClose() {
    const dialog = dialogRef.current;
    if (dialog?.open) {
      dialog.close();
    }
    onClose();
  }

  function handleBackgroundClick(event: React.MouseEvent) {
    if (event.target === dialogRef.current) {
      handleClose();
    }
  }

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    const error = validateId(id);
    if (error) {
      setIdError(error);
      return;
    }

    const newProject = {
      id,
      title,
      owner: pamet.config.userData!.id,
      description,
      created: timestamp(currentTime())
    };

    appActions.createProject(newProject);
    switchToProject(newProject.id).catch(e => {
      console.error('Failed to switch to the new project', e);
    });
    handleClose();
  }

  return (
    <dialog ref={dialogRef} onCancel={handleClose} onClick={handleBackgroundClick}>
      <div className="content-wrapper">
        <h3>Create Project</h3>
        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
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
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <input
              placeholder="Project ID"
              value={id}
              onChange={e => {
                const newId = e.target.value;
                setId(newId);
                setIdError(validateId(newId));
              }}
            />
            {idError ? (
              <small style={{ color: 'red' }}>{idError}</small>
            ) : (
              <small>The ID should be short, suitable for an url.</small>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <textarea
              placeholder="Project Description"
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button type="button" onClick={handleClose}>Cancel</button>
            <button type="submit" disabled={!id.trim() || !title.trim() || idError !== null}>
              Create
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
