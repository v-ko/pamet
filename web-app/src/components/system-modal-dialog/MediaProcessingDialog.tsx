import { useRef, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { MediaProcessingDialogState } from './state';
import './MediaProcessingDialog.css';

interface MediaProcessingDialogProps {
    state: MediaProcessingDialogState;
}

export const MediaProcessingDialog = observer(({ state }: MediaProcessingDialogProps) => {
    const dialogRef = useRef<HTMLDialogElement>(null);

    useEffect(() => {
        const dialog = dialogRef.current;
        if (dialog && !dialog.open) {
            dialog.showModal();
        }
    }, []);

    return (
        <dialog ref={dialogRef} className="system-modal-dialog">
            <h3 className="dialog-title">{state.title}</h3>
            <p className="task-description">{state.taskDescription}</p>
            {state.taskProgress < 0 ? (
                <div className="spinner"></div>
            ) : (
                <progress value={state.taskProgress} max="100"></progress>
            )}
        </dialog>
    );
});
