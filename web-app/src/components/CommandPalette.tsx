import React, { useState, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import "@/components/CommandPalette.css";
import { pamet } from "@/core/facade";
import { appActions } from "@/actions/app";
import { switchToProject } from "@/procedures/app";
import { getLogger } from 'fusion/logging';
import { getCommands } from 'fusion/libs/Command';
import { PageAndCommandPaletteState, ProjectPaletteState } from "@/components/CommandPaletteState";

let log = getLogger('CommandPalette');


interface PaletteItemAttributes {
  id: string;
  title: string;
  action: () => void;
}

interface CommandPaletteProps {
    initialInput: string;
    updateItems: (text: string) => PaletteItemAttributes[];
    placeholder: string;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({initialInput, updateItems, placeholder}) => {
  const [inputValue, setInputValue] = useState(initialInput);
  const [filteredCommands, setFilteredCommands] = useState<PaletteItemAttributes[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    const newFilteredCommands = updateItems(inputValue);
    setFilteredCommands(newFilteredCommands);
    setSelectedIndex(0);
  }, [inputValue, updateItems]);

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                appActions.closeCommandPalette(pamet.appViewState);
            } else if (event.key === 'ArrowDown') {
                setSelectedIndex(prevIndex =>
                    Math.min(prevIndex + 1, filteredCommands.length - 1)
                );
            } else if (event.key === 'ArrowUp') {
                setSelectedIndex(prevIndex => Math.max(prevIndex - 1, 0));
            } else if (event.key === 'Enter') {
                if (filteredCommands[selectedIndex]) {
                    handleCommandClick(filteredCommands[selectedIndex]);
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [filteredCommands, selectedIndex]);

  const handleCommandClick = (command: PaletteItemAttributes) => {
    command.action();
  };

  return (
    <div className="command-palette" style={{zIndex: 2000}}>
        <input
          type="text"
          placeholder={placeholder}
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          autoFocus
          onBlur={() => appActions.closeCommandPalette(pamet.appViewState)}
        />
        <ul className="command-list">
          {filteredCommands.map((command, index) => (
            <li
                key={command.id}
                className={index === selectedIndex ? 'selected' : ''}
                onClick={() => handleCommandClick(command)}
                onMouseEnter={() => setSelectedIndex(index)}
            >
              {command.title}
            </li>
          ))}
        </ul>
    </div>
  );
};

// New components will return the original for now
export const PageAndCommandPalette: React.FC<{ state: PageAndCommandPaletteState }> = observer(({ state }) => {
    const updateItems = (text: string): PaletteItemAttributes[] => {
        const appState = pamet.appViewState;

        if (text.startsWith('>')) {
            const filterText = text.substring(1).toLowerCase();
            const allCommands = getCommands();
            let commandItems: PaletteItemAttributes[] = [];

            for (const cmd of allCommands) {
                if (cmd.title.toLowerCase().includes(filterText)) {
                    commandItems.push({
                        id: cmd.name,
                        title: cmd.title,
                        action: () => {
                            cmd.function();
                            appActions.closeCommandPalette(appState);
                        }
                    });
                }
            }
            return commandItems;

        } else {
            const pages = Array.from(pamet.pages());
            let pageCommands: PaletteItemAttributes[] = [];
            for (let page of pages) {
                if (page.id === appState.currentPageId) {
                    continue; // Skip the current page
                }
                if (!page.name.toLowerCase().includes(text.toLowerCase())) {
                    continue;
                }
                pageCommands.push({
                    id: page.id,
                    title: page.name,
                    action: () => {
                        // appActions.navigateToPage(page.id);
                        log.info(`Navigating to page ${page.name}`);
                        appActions.setCurrentPage(pamet.appViewState, page.id);
                        appActions.closeCommandPalette(appState);
                    }
                });
            }
            return pageCommands;
        }
    };
    return <CommandPalette initialInput={state.initialInput} updateItems={updateItems} placeholder="Search pages or type > for commands..." />;
});

export const ProjectPalette: React.FC<{ state: ProjectPaletteState }> = observer(({ state }) => {
    const updateItems = (text: string): PaletteItemAttributes[] => {
        const appState = pamet.appViewState;
        const projects = pamet.projects();
        let projectCommands: PaletteItemAttributes[] = [];
        for (let project of projects) {
            if (project.id === appState.currentProjectId) {
                continue; // Skip the current project
            }
            if (!project.title.toLowerCase().includes(text.toLowerCase())) {
                continue;
            }
            projectCommands.push({
                id: project.id,
                title: project.title,
                action: () => {
                    switchToProject(project.id).catch((error) => {
                        console.error(`Error switching to project ${project.title}:`, error);
                    });
                    appActions.closeCommandPalette(appState);
                }
            });
        }
        return projectCommands;
    };
    return <CommandPalette initialInput={state.initialInput} updateItems={updateItems} placeholder="Search projects..." />;
});
