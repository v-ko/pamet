import { useState, useEffect, useRef, useMemo, FormEvent } from 'react';
import { pamet } from "@/core/facade";
import { getLogger } from 'fusion/logging';
import { DEFAULT_NEW_PAGE_PREFIX } from '@/core/constants';
import "@/views/dialogs/Dialog.css";

let log = getLogger('CreatePageDialog');

interface CreatePageDialogProps {
  onClose: () => void;
  onCreate: (name: string) => void;
}

export function CreatePageDialog({ onClose, onCreate }: CreatePageDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [pageName, setPageName] = useState('');

  // Give a unique default name on mount, then open the dialog
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    // Generate default name (new pages are created in root)
    const existingNames = new Set(
      Array.from(pamet.pages()).filter(p => p.folder === '').map(p => p.name)
    );
    let newName = DEFAULT_NEW_PAGE_PREFIX;
    let i = 1;
    while (existingNames.has(newName)) {
      newName = `${DEFAULT_NEW_PAGE_PREFIX} ${i++}`;
    }
    setPageName(newName);

    // Open dialog
    if (!dialog.open) {
      dialog.showModal();
    }
  }, []);

  // Check if name is already taken in root folder
  const isNameTaken = useMemo(() => {
    const trimmed = pageName.trim();
    if (!trimmed) return false;
    return Array.from(pamet.pages()).some(p => p.folder === '' && p.name === trimmed);
  }, [pageName]);

  function handleCreate(e: FormEvent) {
    const trimmed = pageName.trim();
    if (!isNameTaken && trimmed) {
      log.info(`Creating new page: ${trimmed}`);
      onCreate(trimmed);
      onClose();
    }
  }

  return (
    <dialog
      ref={dialogRef}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) { // Close on outside click
            onClose();
        }
      }}
      className="app-dialog"
    >
      <div className="dialog-content">
        <h3 className="dialog-title">Create page</h3>
        <form method="dialog" onSubmit={handleCreate} className="form-vertical">
          <input
            autoFocus
            type="text"
            value={pageName}
            onChange={e => setPageName(e.target.value)}
            placeholder="Page name"
            className="dialog-input"
          />
          {isNameTaken && <div className="dialog-error">This name is already taken.</div>}
          <div className="dialog-actions">
            <button className="btn btn-primary" type="submit" disabled={isNameTaken || !pageName.trim()}>
              Create
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
