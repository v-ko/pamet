import { entityType, getEntityId } from "fusion/libs/Entity";
import { Note } from "@/model/Note";
import { Page } from "@/model/Page";
import { elementId } from "@/model/Element";
import { currentTime, timestamp } from "fusion/base-util";
import { PametRoute } from "@/services/routing/route";

const MISSING_PAGE_TITLE = '(missing)'

@entityType('InternalLinkNote')
export class InternalLinkNote extends Note {
    static createNew(parentPageId: string, targetPageId: string): Note {
        let ownId = getEntityId();
        let id = elementId(parentPageId, ownId);
        let currentTimestamp = timestamp(currentTime());

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
        return PametRoute.fromUrl(url).pageId // pamet:/p/<page_id>
    }
    targetPage(): Page | undefined {
        let pageId = this.targetPageId()
        if (pageId === undefined) {
            return undefined
        }
        return pamet.page(pageId)
    }
}
