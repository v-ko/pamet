import { entityType } from "fusion/model/Entity";
import { Note } from "@/model/Note";

@entityType('ExternalLinkNote')
export class ExternalLinkNote extends Note {
    url(): string {
        return this.content.url || '';
    }
}
