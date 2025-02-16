import * as Dialog from '@radix-ui/react-dialog';
import { pamet } from 'web-app/src/core/facade';
import { appActions } from 'web-app/src/actions/app';

interface ProjectsDialogProps {
  onClose: () => void;
}

export function ProjectsDialog({ onClose }: ProjectsDialogProps) {
  const projects = pamet.projects();
  console.log('projects', projects);
  return (
    <Dialog.Root open={true} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay style={{
          backgroundColor: 'rgba(0, 0, 0, 0.4)',
          position: 'fixed',
          inset: 0,
        }} />
        <Dialog.Content style={{
          backgroundColor: 'white',
          borderRadius: '4px',
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '90vw',
          maxWidth: '400px',
          padding: '16px',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Dialog.Title style={{ margin: 0 }}>Projects</Dialog.Title>
              <button
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '4px',
                  fontSize: '20px',
                  color: '#007bff'
                }}
                title="Create new project"
                onClick={() => {
                  appActions.openCreateProjectDialog(pamet.appViewState);
                }}
              >
                +
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {projects.map((project) => (
                <div
                  key={project.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px',
                    backgroundColor: '#f5f5f5',
                    borderRadius: '4px'
                  }}
                >
                  <span>{project.title}</span>
                  <button
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '4px',
                      fontSize: '16px'
                    }}
                    title="Project menu"
                  >
                    ⋮
                  </button>
                </div>
              ))}
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
