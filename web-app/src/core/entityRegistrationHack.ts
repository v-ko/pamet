import { getLogger } from 'fusion/logging';

// Entity imports that are required to activate @entityType decorators
import { CardNote } from "@/model/CardNote";
import { OtherPageListNote } from "@/model/OtherPageListNote";
import { ScriptNote } from "@/model/ScriptNote";
import { Page } from "@/model/Page";
import { Arrow } from "@/model/Arrow";
import { ImageItem } from 'fusion/model/ImageItem';
import { ScriptNoteCanvasView } from '@/components/note/ScriptNoteCanvasView';
import { CardNoteCanvasView } from '@/components/note/CardNoteCanvasView';

const log = getLogger('entityRegistration');

/**
 * Registers all entity classes by importing them, which triggers the @entityType decorators.
 * This function must be called in both the main thread and service worker contexts
 * to ensure entity deserialization works properly.
 */
export function registerEntityClasses(): void {
    // Ensure the imports are not tree-shaken by referencing them
    const entityClasses = [
        CardNote, OtherPageListNote, ScriptNote,
        Page, Arrow, ImageItem, ScriptNoteCanvasView, CardNoteCanvasView
    ];

    log.info('Registered entity classes:', entityClasses.map(cls => cls.name));
}
