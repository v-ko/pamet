import { getLogger } from 'fusion/logging';

// Entity imports that are required to activate @entityType decorators
import { CardNote } from "@/model/CardNote";
import { OtherPageListNote } from "@/model/OtherPageListNote";
import { ScriptNote } from "@/model/ScriptNote";
import { Page } from "@/model/Page";
import { Arrow } from "@/model/Arrow";
import { MediaItem } from 'fusion/model/MediaItem';

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
        Page, Arrow, MediaItem
    ];

    log.info('Registered entity classes:', entityClasses.map(cls => cls.name));
}
