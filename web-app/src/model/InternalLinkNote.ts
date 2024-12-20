import { entityType, getEntityId } from "fusion/libs/Entity";
import { Note } from "./Note";
import { Page } from "./Page";
import { elementId } from "./Element";
import { currentTime, timestamp } from "fusion/util";
import { pamet } from "../core/facade";
import { parseUrl } from "../services/routing/route";

const MISSING_PAGE_TITLE = '(missing)'

@entityType('InternalLinkNote')
export class InternalLinkNote extends Note {
    static createNew(parentPageId: string, targetPageId: string): Note {
        let ownId = getEntityId();
        let id = elementId(parentPageId, ownId);
        let currentTimestamp = timestamp(currentTime());

        let targetPage = pamet.page(targetPageId)
        if (targetPage === undefined) {
            throw new Error(`Target page ${targetPageId} not found`)
        }

        let note = new InternalLinkNote({
            id: id,
            content: {
                url: targetPage.url()
            },
            geometry: [0, 0, 200, 100],
            style: {
                background_color_role: 'primary',
                color_role: 'onPrimary',
            },
            created: currentTimestamp,
            modified: currentTimestamp,
            metadata: {},
            tags: []
        });
        return note;
    }
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
        return parseUrl(url).pageId // pamet:/p/<page_id>
    }
    targetPage(): Page | undefined {
        let pageId = this.targetPageId()
        if (pageId === undefined) {
            return undefined
        }
        return pamet.page(pageId)
    }
}
