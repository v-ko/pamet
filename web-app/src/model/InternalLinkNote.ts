import { entityType, getEntityId } from "fusion/model/Entity";
import { Note } from "@/model/Note";
import { Page } from "@/model/Page";
import { elementId } from "@/model/Element";
import { currentTime, timestamp } from "fusion/util/base";
import { PametRoute } from "@/services/routing/route";



@entityType('InternalLinkNote')
export class InternalLinkNote extends Note {
    static createNew(page: Page): Note {
        let ownId = getEntityId();
        let id = elementId(page.id, ownId);
        let currentTimestamp = timestamp(currentTime());

        let note = new InternalLinkNote({
            id: id,
            content: {
                text: page.name,
                url: new PametRoute({pageId: page.id}).toProjectScopedURI(),
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
    targetPageId(): string | undefined {
        let url = this.content.url
        if (url === undefined){
            return undefined
        }
        return PametRoute.fromUrl(url).pageId // pamet:/p/<page_id>
    }
}
