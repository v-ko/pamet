import { entityType, getEntityId } from "sivkit/model/Entity";
import { currentTime, timestamp } from "sivkit/util/base";
import { Note, NoteData } from "@/model/Note";
import {
    DEFAULT_BACKGROUND_COLOR_ROLE,
    DEFAULT_NOTE_HEIGHT,
    DEFAULT_NOTE_WIDTH,
    DEFAULT_TEXT_COLOR_ROLE,
} from "@/app/constants";

/**
 * Content schema for ScriptNote. Independent of NoteContent — the
 * `content` slot on the base Note is a per-subtype payload.
 */
export interface ScriptContent {
    text?: string;              // display label on the note
    script_path?: string;       // absolute, or relative to project root
    command_args?: string;      // raw string; tokenized server-side via shlex
    run_in_terminal?: boolean;  // launch in external terminal (untracked, fire-and-forget)
    working_directory?: string; // optional; defaults to project root
}

export interface ScriptNoteData extends NoteData {
    content: ScriptContent;
}

@entityType('ScriptNote')
export class ScriptNote extends Note {
    declare _data: ScriptNoteData;

    static createNew(props: Partial<ScriptNoteData> & { pageId: string }): ScriptNote {
        const { pageId, ...overrides } = props;
        const now = timestamp(currentTime());
        const data: ScriptNoteData = {
            id: getEntityId(),
            parent_id: pageId,
            content: {},
            geometry: [0, 0, DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT],
            style: {
                background_color_role: DEFAULT_BACKGROUND_COLOR_ROLE,
                color_role: DEFAULT_TEXT_COLOR_ROLE,
            },
            created: now,
            modified: now,
            metadata: {},
        };
        return new ScriptNote(Object.assign(data, overrides));
    }

    get content(): ScriptContent {
        return this._data.content;
    }
    get scriptPath(): string {
        return this._data.content.script_path ?? '';
    }
    set scriptPath(value: string) {
        this._data.content.script_path = value;
    }
    get commandArgs(): string {
        return this._data.content.command_args ?? '';
    }
    set commandArgs(value: string) {
        this._data.content.command_args = value;
    }
    get runInTerminal(): boolean {
        return !!this._data.content.run_in_terminal;
    }
    set runInTerminal(value: boolean) {
        this._data.content.run_in_terminal = value;
    }
    get workingDirectory(): string {
        return this._data.content.working_directory ?? '';
    }
    set workingDirectory(value: string) {
        this._data.content.working_directory = value;
    }
}
