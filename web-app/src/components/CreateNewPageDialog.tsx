import { useState, useEffect, useRef, useMemo, FormEvent } from 'react';
import { pamet } from "@/core/facade";
import { Page } from "@/model/Page";
import { getLogger } from 'fusion/logging';

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

    // Generate default name
    let newName = 'New Page';
    let i = 1;
    while (pamet.findOne({ type: Page, name: newName })) {
      newName = `New Page ${i++}`;
    }
    setPageName(newName);

    // Open dialog
    if (!dialog.open) {
      dialog.showModal();
    }
  }, []);

  // Check if name is already taken
  const isNameTaken = useMemo(() => {
    const trimmed = pageName.trim();
    return trimmed ? !!pamet.findOne({ type: Page, name: trimmed }) : false;
  }, [pageName]);

  function handleCreate(e: FormEvent) {
    const trimmed = pageName.trim();
    if (!isNameTaken && trimmed) {
      log.info(`Creating new page: ${trimmed}`);
      onCreate(trimmed);
      // No need to call onClose, the dialog will close automatically
    }
  }

  return (
    <dialog ref={dialogRef} onCancel={onClose} onClick={(e) => {
        if (e.target === dialogRef.current) { // Close on outside click
            onClose();
        }
    }}>
      <div className="content-wrapper">
        <h3>Create page</h3>
        <form method="dialog" onSubmit={handleCreate}>
          <input
            autoFocus
            type="text"
            value={pageName}
            onChange={e => setPageName(e.target.value)}
            placeholder="Page name"
          />
          {isNameTaken && <div>This name is already taken.</div>}
          <button type="submit" disabled={isNameTaken || !pageName.trim()}>
            Create
          </button>
        </form>
      </div>
    </dialog>
  );
}
