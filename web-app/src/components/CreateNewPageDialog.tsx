// CreatePageDialog.tsx
import { useState, useEffect, useRef, FormEvent } from 'react';
import { pamet } from '../core/facade';
import { Page } from '../model/Page';

interface CreatePageDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string) => void;
}

export function CreatePageDialog({ isOpen, onClose, onCreate }: CreatePageDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [pageName, setPageName] = useState('');
  const [isNameTaken, setIsNameTaken] = useState(false);

  useEffect(() => {
    if (isOpen) {
      let name = 'New Page';
      let i = 1;
      while (pamet.findOne({ type: Page, name: name })) {
        name = `New Page ${i}`;
        i++;
      }
      setPageName(name);
    }
  }, [isOpen]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen) {
      dialog.showModal();
      requestAnimationFrame(() => {
        if (inputRef.current) inputRef.current.focus();
      });
    } else if (dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  useEffect(() => {
    const trimmedName = pageName.trim();
    if (trimmedName) {
      setIsNameTaken(!!pamet.findOne({ type: Page, name: trimmedName }));
    } else {
      setIsNameTaken(false);
    }
  }, [pageName]);

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!isNameTaken && pageName.trim()) {
      onCreate(pageName.trim());
      onClose();
    }
  }

  function handleDialogCancel() {
    onClose();
  }

  return (
    <>
      <dialog
        ref={dialogRef}
        onCancel={handleDialogCancel}
        style={{
          background: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '20px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
          maxWidth: '300px',
          width: '90%',
        }}
      >
        <h3 style={{ margin: '0 0 10px 0' }}>Create page</h3>
        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <input
            ref={inputRef}
            type="text"
            value={pageName}
            onChange={e => setPageName(e.target.value)}
            placeholder="Page name"
            style={{
              padding: '8px',
              fontSize: '14px',
              borderRadius: '4px',
              border: '1px solid #ccc',
            }}
          />
          {isNameTaken && (
            <div style={{ color: 'red', fontSize: '12px', marginTop: '-5px' }}>
              This name is already taken.
            </div>
          )}
          <button
            type="submit"
            style={{
              padding: '8px 12px',
              fontSize: '14px',
              borderRadius: '4px',
              border: 'none',
              background: isNameTaken || !pageName.trim() ? '#ccc' : '#2196f3',
              color: 'white',
              cursor: isNameTaken || !pageName.trim() ? 'not-allowed' : 'pointer',
            }}
            disabled={isNameTaken || !pageName.trim()}
          >
            Create
          </button>
        </form>
      </dialog>
      <style>{`
        dialog::backdrop {
          background: rgba(0,0,0,0.5);
        }
      `}</style>
    </>
  );
}
