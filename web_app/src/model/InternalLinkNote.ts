import { pamet } from "../facade";
import { entityType } from "../fusion/libs/Entity";
import { Note } from "./Note";
import { Page } from "./Page";

const MISSING_PAGE_TITLE = '(missing)'

@entityType('InternalLinkNote')
export class InternalLinkNote extends Note {
    get text(): string {
        let page = this.targetPage()
        if (page !== undefined) {
            return page!.name
        } else {
            return MISSING_PAGE_TITLE
        }
    }
    targetPageId(): string | undefined {
        let url = this.content.url
        if (url === undefined){
            return undefined
        }
        return url.split("/")[2] // pamet:/p/<page_id>
    }
    targetPage(): Page | undefined {
        let pageId = this.targetPageId()
        if (pageId === undefined) {
            return undefined
        }
        return pamet.page(pageId)
    }
}
