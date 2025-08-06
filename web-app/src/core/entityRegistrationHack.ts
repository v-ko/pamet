import { getLogger } from 'fusion/logging';

// Entity imports that are required to activate @entityType decorators
import { TextNote } from '../model/TextNote';
import { CardNote } from '../model/CardNote';
import { ImageNote } from '../model/ImageNote';
import { OtherPageListNote } from '../model/OtherPageListNote';
import { ScriptNote } from '../model/ScriptNote';
import { InternalLinkNote } from '../model/InternalLinkNote';
import { ExternalLinkNote } from '../model/ExternalLinkNote';
import { Page } from '../model/Page';
import { Arrow } from '../model/Arrow';
import { MediaItem } from 'fusion/libs/MediaItem';

const log = getLogger('entityRegistration');

/**
 * Registers all entity classes by importing them, which triggers the @entityType decorators.
 * This function must be called in both the main thread and service worker contexts
 * to ensure entity deserialization works properly.
 */
export function registerEntityClasses(): void {
    // Ensure the imports are not tree-shaken by referencing them
    const entityClasses = [
        TextNote, CardNote, ImageNote, OtherPageListNote, ScriptNote,
        InternalLinkNote, ExternalLinkNote, Page, Arrow, MediaItem
    ];

    log.info('Registered entity classes:', entityClasses.map(cls => cls.name));
}
