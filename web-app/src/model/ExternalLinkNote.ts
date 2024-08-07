import { entityType } from "fusion/libs/Entity";
import { Note } from "./Note";

@entityType('ExternalLinkNote')
export class ExternalLinkNote extends Note {
    url(): string {
        return this.content.url || '';
    }
}
