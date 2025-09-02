import { useRef, useEffect } from 'react';
import { pamet } from '@/core/facade';
import { appActions } from '@/actions/app';
import { PametRoute } from "@/services/routing/route";
import { getLogger } from 'fusion/logging';
import "@/components/dialogs/Dialog.css";

let log = getLogger('ProjectsDialog')

interface ProjectsDialogProps {
  onClose: () => void;
}

export function ProjectsDialog({ onClose }: ProjectsDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const projects = pamet.projects();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }
  }, []);

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
        <div className="row-between">
          <h3 className="dialog-title">Projects</h3>
          <button
            className="icon-button"
            title="Create new project"
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
