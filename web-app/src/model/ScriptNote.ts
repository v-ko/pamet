import { entityType, getEntityId } from "sivkit/model/Entity";
import { currentTime, timestamp } from "sivkit/util/base";
import { Note, NoteData } from "@/model/Note";

@entityType('ScriptNote')
export class ScriptNote extends Note {

}
