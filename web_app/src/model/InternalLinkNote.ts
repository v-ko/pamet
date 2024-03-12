import { entityType } from "../fusion/libs/Entity";
import { Note } from "./Note";

@entityType('InternalLinkNote')
export class InternalLinkNote extends Note {
    targetPageId(): string | undefined {
        let url = this.content.url
        if (url === undefined){
            return undefined
        }
        return url.split("/")[2] // pamet:/p/<page_id>
    }
}
