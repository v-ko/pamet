import { useState, useEffect, useRef, useMemo, FormEvent } from 'react';
import { pamet } from 'web-app/src/core/facade';
import { Page } from 'web-app/src/model/Page';

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

  // Close helper
  function handleClose() {
    const dialog = dialogRef.current;
    if (dialog?.open) {
      dialog.close();
    }
    onClose();
  }

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
      handleClose();
    }
  }

  function handleDelete() {
      onDelete(page);
      handleClose();
  }

  // Close dialog on background click
  function handleBackgroundClick(event: React.MouseEvent) {
    if (event.target === dialogRef.current) {
      handleClose();
    }
  }

  return (
    <dialog
      ref={dialogRef}
      onCancel={handleClose}
      onClick={handleBackgroundClick}
      className="page-properties-dialog"
    >
      <div className="content-wrapper">
        <h3>Page Properties</h3>
        <form onSubmit={handleSave}>
          <div className="form-group">
            <input
              autoFocus
              type="text"
              value={pageName}
              onChange={e => setPageName(e.target.value)}
              placeholder="Page name"
              className="page-name-input"
            />
            {isNameTaken && <div className="error-message">This name is already taken.</div>}
          </div>
          <div className="button-group">
            <button
              type="submit"
              disabled={isNameTaken || !pageName.trim()}
              className="save-button"
            >
              Save
            </button>
            <button
              type="button"
              onClick={handleDelete}
              className="delete-button"
            >
              Delete Page
            </button>
          </div>
        </form>
      </div>
      <style jsx>{`
        .page-properties-dialog {
          border: none;
          border-radius: 8px;
          padding: 0;
          background: white;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .page-properties-dialog::backdrop {
          background: rgba(0, 0, 0, 0.5);
        }

        .content-wrapper {
          padding: 24px;
          min-width: 320px;
        }

        h3 {
          margin: 0 0 20px 0;
          font-size: 1.2rem;
          color: #333;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .page-name-input {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 1rem;
          outline: none;
          transition: border-color 0.2s;
        }

        .page-name-input:focus {
          border-color: #007bff;
        }

        .error-message {
          color: #dc3545;
          font-size: 0.875rem;
          margin-top: 6px;
        }

        .button-group {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
        }

        button {
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          font-size: 0.875rem;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .save-button {
          background: #007bff;
          color: white;
        }

        .save-button:hover:not(:disabled) {
          background: #0056b3;
        }

        .delete-button {
          background: #dc3545;
          color: white;
        }

        .delete-button:hover {
          background: #c82333;
        }
      `}</style>
    </dialog>
  );
}
