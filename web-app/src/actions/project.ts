import { action } from "pyfusion/libs/Action";
import type { RepoUpdate } from "../../../fusion/js-src/src/storage/BaseRepository";
import { WebAppState } from "../containers/app/App";
import { pamet } from "../core/facade";
import { Page, PageData } from "../model/Page";
import { createId, currentTime, timestamp } from "pyfusion/util";
import { Note } from "../model/Note";
import { minimalNonelidedSize } from "../components/note/util";
import { TextNote } from "../model/TextNote";


class ProjectActions {
    @action({issuer: 'service'})
    createDefaultPage(appState: WebAppState) {
        // Create the page
        let pageData: PageData = {
            name: 'Home Page',
            id: createId(),
            created: timestamp(currentTime()),
            modified: timestamp(currentTime()),
        }
        let page = new Page(pageData)
        pamet.frontendDomainStore.insertPage(page)

        // Add a "Press H for help" note in the center
        let note = TextNote.createNew(page.id)
        note.content.text = 'Press H for help'
        let noteRect = note.rect()
        noteRect.setSize(minimalNonelidedSize(note))
        note.setRect(noteRect)
        pamet.frontendDomainStore.insertNote(note)

        // Set page as default for the project
        let projectData = appState.currentProject
        if (!projectData) {
            throw Error('No current project')
        }
        projectData.defaultPageId = page.id
        pamet.updateProject(projectData)
    }
}

export const projectActions = new ProjectActions();
