import { useState, useEffect, useRef, useMemo, FormEvent } from 'react';
import { pamet } from '@/core/facade';
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
    e.preventDefault();
    const trimmed = pageName.trim();
    if (!isNameTaken && trimmed) {
      const updatedPage = page;
      updatedPage.name = trimmed;
      onSave(updatedPage);
      // The dialog will close automatically because of the form method="dialog"
    }
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
      style={{
        border: 'none',
        borderRadius: '4px',
        padding: '16px',
        maxWidth: '300px'
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h3 style={{ margin: 0 }}>Page Properties</h3>
        <form method="dialog" onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <input
            autoFocus
            type="text"
            value={pageName}
            onChange={e => setPageName(e.target.value)}
            placeholder="Page name"
            style={{ padding: '4px' }}
          />
          {isNameTaken && <div style={{ color: 'red', fontSize: '14px' }}>This name is already taken.</div>}
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
            <button type="submit" disabled={isNameTaken || !pageName.trim()}>
              Save
            </button>
            <button type="button" onClick={handleDelete} style={{ backgroundColor: '#dc3545', color: 'white', border: 'none' }}>
              Delete Page
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
