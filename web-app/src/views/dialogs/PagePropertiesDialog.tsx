import { useState, useEffect, useRef, useMemo, FormEvent } from 'react';
import { pamet } from '@/app/facade';
import "@/views/dialogs/Dialog.css";
import { Page } from '@/model/Page';
import { PametTabIndex } from '@/app/constants';
import { isPagePathTaken, normalizePageName, pagePath } from '@/model/pageNames';

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

  const { name, error } = useMemo(() => {
    const normalized = normalizePageName(pageName);
    // An unchanged name is kept even if it isn't portable
    if (pageName.trim() === page.name || normalized.name === page.name) {
      return { name: page.name, error: null };
    }
    return normalized;
  }, [pageName, page.name]);

  // Not memoized: other tabs may add pages while the dialog is open
  const nameTaken = () => name !== page.name && !error &&
    isPagePathTaken(pamet.pages(), pagePath(page.folder, name), page.id);
  const isNameTaken = nameTaken();

  function handleSave(e: FormEvent) {
    if (nameTaken() || error) {
      e.preventDefault();
      return;
    }
    const updatedPage = page;
    // Update path: replace the stem (name), keep folder and extension
    updatedPage.path = pagePath(updatedPage.folder, name);
    onSave(updatedPage);
    // Allow default submit to close the dialog (method="dialog")
  }

  function handleDelete() {
      onDelete(page);
      // The dialog will close automatically because of the form method="dialog"
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
        <h3 className="dialog-title">Page Properties</h3>
        <form method="dialog" onSubmit={handleSave} className="form-vertical">
          <input
            autoFocus
            type="text"
            value={pageName}
            onChange={e => setPageName(e.target.value)}
            placeholder="Page name"
            className="dialog-input"
            tabIndex={PametTabIndex.PagePropertiesDialog_NameInput}
          />
          {isNameTaken && <div className="dialog-error">This name is already taken.</div>}
          {error && <div className="dialog-error">{error}</div>}
          <div className="dialog-actions row-between">
            <button className="btn btn-danger" type="button" onClick={handleDelete} tabIndex={PametTabIndex.PagePropertiesDialog_Delete}>
              Delete Page
            </button>
            <button className="btn btn-primary" type="submit" disabled={isNameTaken || !!error} tabIndex={PametTabIndex.PagePropertiesDialog_Save}>
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
      </div>
    </dialog>
  );
}
