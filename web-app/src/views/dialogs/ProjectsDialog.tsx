import { useRef, useEffect } from 'react';
import { pamet } from '@/app/facade';
import { appActions } from '@/actions/app';
import { PametRoute } from "@/services/routing/PametRoute";
import { PametTabIndex } from '@/app/constants';
import { getLogger } from 'sivkit/logging';
import "@/views/dialogs/Dialog.css";

let log = getLogger('ProjectsDialog')

interface ProjectsDialogProps {
  onClose: () => void;
}

export function ProjectsDialog({ onClose }: ProjectsDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const projects = pamet.appViewState.trackedProjects;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }
  }, []);

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
        <div className="row-between">
          <h3 className="dialog-title">Projects</h3>
          <button
            className="icon-button"
            title="Create new project"
            tabIndex={PametTabIndex.ProjectsDialog_CreateButton}
            onClick={() => {
              appActions.openCreateProjectDialog(pamet.appViewState);
            }}
          >
            +
          </button>
        </div>
        <div className="list">
          {projects.map((project) => (
            <div
              key={project.id}
              className="list-item"
            >
              <a
                href={(() => {
                  const userId = pamet.appViewState.userId;
                  if (!userId) {
                    log.error('Trying to open projects dialog with no userId set')
                    return;
                  }
                  const route = new PametRoute(({
                    userId: userId,
                    projectId: project.id}));
                  return route.toRelativeReference();
                })()}
                onClick={onClose}
              >
                {project.title}
              </a>
              <button className="icon-button" title="Project menu">⋮</button>
            </div>
          ))}
        </div>
      </div>
    </dialog>
  );
}
