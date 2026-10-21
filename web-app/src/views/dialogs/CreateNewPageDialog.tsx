import { useState, useEffect, useRef, useMemo, FormEvent } from 'react';
import { pamet } from "@/app/facade";
import { getLogger } from 'sivkit/logging';
import { DEFAULT_NEW_PAGE_PREFIX, PametTabIndex } from '@/app/constants';
import { isPagePathTaken, normalizePageName, pagePath } from '@/model/pageNames';
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
    const pages = Array.from(pamet.pages());
    let newName = DEFAULT_NEW_PAGE_PREFIX;
    let i = 1;
    while (isPagePathTaken(pages, pagePath('', newName))) {
      newName = `${DEFAULT_NEW_PAGE_PREFIX} ${i++}`;
    }
    setPageName(newName);

    // Open dialog
    if (!dialog.open) {
      dialog.showModal();
    }
  }, []);

  const { name, error } = useMemo(() => normalizePageName(pageName), [pageName]);

  // Not memoized: other tabs may add pages while the dialog is open
  const nameTaken = () => !error && isPagePathTaken(pamet.pages(), pagePath('', name));
  const isNameTaken = nameTaken();

  function handleCreate(e: FormEvent) {
    if (nameTaken() || error) {
      e.preventDefault();
      return;
    }
    log.info(`Creating new page: ${name}`);
    onCreate(name);
    onClose();
  }

  const mouseDownOnBackdrop = useRef(false);

  return (
    <dialog
      ref={dialogRef}
      onCancel={onClose}
      onMouseDown={(e) => { mouseDownOnBackdrop.current = e.target === dialogRef.current; }}
      onClick={(e) => {
        if (e.target === dialogRef.current && mouseDownOnBackdrop.current) {
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
            tabIndex={PametTabIndex.CreatePageDialog_NameInput}
          />
          {isNameTaken && <div className="dialog-error">This name is already taken.</div>}
          {error && <div className="dialog-error">{error}</div>}
          <div className="dialog-actions">
            <button className="btn btn-primary" type="submit" disabled={isNameTaken || !!error} tabIndex={PametTabIndex.CreatePageDialog_Create}>
              Create
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
