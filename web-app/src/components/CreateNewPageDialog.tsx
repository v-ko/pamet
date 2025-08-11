import { useState, useEffect, useRef, useMemo, FormEvent } from 'react';
import { pamet } from "@/core/facade";
import { Page } from "@/model/Page";

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

  // Close helper
  function handleClose() {
    const dialog = dialogRef.current;
    if (dialog?.open) {
      dialog.close();
    }
    onClose();
  }

  // Check if name is already taken
  const isNameTaken = useMemo(() => {
    const trimmed = pageName.trim();
    return trimmed ? !!pamet.findOne({ type: Page, name: trimmed }) : false;
  }, [pageName]);

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    const trimmed = pageName.trim();
    if (!isNameTaken && trimmed) {
      onCreate(trimmed);
      handleClose();
    }
  }

  // Close dialog on background click
  function handleBackgroundClick(event: React.MouseEvent) {
    if (event.target === dialogRef.current) {
      handleClose();
    }
  }

  return (
    <dialog ref={dialogRef} onCancel={handleClose} onClick={handleBackgroundClick}>
      <div className="content-wrapper">
        <h3>Create page</h3>
        <form onSubmit={handleCreate}>
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
