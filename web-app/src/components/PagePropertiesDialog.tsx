import { useState, useEffect, useRef, useMemo, FormEvent } from 'react';
import { pamet } from '@/core/facade';
import "@/components/dialogs/Dialog.css";
import { Page } from '@/model/Page';

interface PagePropertiesDialogProps {
  page: Page;
  onClose: () => void;
  onSave: (page: Page) => void;
  onDelete: (page: Page) => void;
}

export function PagePropertiesDialog({ page, onClose, onSave, onDelete }: PagePropertiesDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [pageName, setPageName] = useState(page.name);

  // Open dialog on mount
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (!dialog.open) {
      dialog.showModal();
    }
  }, []);

  // Check if name is already taken by a different page
  const isNameTaken = useMemo(() => {
    const trimmed = pageName.trim();
    if (!trimmed || trimmed === page.name) return false;
    return !!pamet.findOne({ type: Page, name: trimmed });
  }, [pageName, page.name]);

  function handleSave(e: FormEvent) {
    const trimmed = pageName.trim();
    if (isNameTaken || !trimmed) {
      e.preventDefault();
      return;
    }
    const updatedPage = page;
    updatedPage.name = trimmed;
    onSave(updatedPage);
    // Allow default submit to close the dialog (method="dialog")
  }

  function handleDelete() {
      onDelete(page);
      // The dialog will close automatically because of the form method="dialog"
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) { // Close on outside click
            onClose();
        }
      }}
      className="app-dialog"
    >
      <div className="dialog-content">
        <h3 className="dialog-title">Page Properties</h3>
        <button
          type="button"
          className="icon-button dialog-close"
          onClick={() => dialogRef.current?.close()}
        >
          ×
        </button>
        <form method="dialog" onSubmit={handleSave} className="form-vertical">
          <input
            autoFocus
            type="text"
            value={pageName}
            onChange={e => setPageName(e.target.value)}
            placeholder="Page name"
            className="dialog-input"
          />
          {isNameTaken && <div className="dialog-error">This name is already taken.</div>}
          <div className="dialog-actions row-between">
            <button className="btn btn-danger" type="button" onClick={handleDelete}>
              Delete Page
            </button>
            <button className="btn btn-primary" type="submit" disabled={isNameTaken || !pageName.trim()}>
              Save
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
