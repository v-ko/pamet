import { getLogger } from "fusion/logging";
import { BaseApiClient } from "fusion/storage/BaseApiClient";
import { SerializedEntityData, loadFromDict } from "fusion/model/Entity";
// import { elementId } from "@/model/Element";
import { DEFAULT_BACKGROUND_COLOR_ROLE, DEFAULT_TEXT_COLOR_ROLE } from "@/core/constants";
import { old_color_to_role } from "fusion/primitives/Color";
import { pamet } from "@/core/facade";
import { PametRoute } from "@/services/routing/route";
import { MediaItem } from "fusion/model/MediaItem";

let log = getLogger('ApiClient');

export class DesktopImporter extends BaseApiClient {
    public async importAllInProject(progressCallback: (progress: number, message: string) => void) {
        progressCallback(0, 'Starting import...');

        // This is the original migration function, unmodified, nested here for use.
        function tmpDynamicMigration(childData: Record<string, any>) {
            // No composite id anymore , for old ones where the id can be the same for different pages - keep the composite and treat it as unique plain id
            
            // let [page_id, own_id] = childData.id;
            // if (page_id === undefined || own_id === undefined) {
            //     throw new Error('Bad id')
            // }
            // childData.id = own_id //elementId(page_id, own_id);

            // Fill style where missing and convert colors to roles
            if (childData.style === undefined) {
                childData.style = {}
            }

            // This migration should be applied only to data with the old schema
            if (childData.style.color_role !== undefined) {
                throw new Error('Unexpected: color_role is already set')
            }
            if (childData.style.background_color_role !== undefined) {
                throw new Error('Unexpected: background_color_role is already set')
            }

            // Convert colors to roles (or fill with defaults)
            if (childData.style.color === undefined) {
                childData.style.color_role = DEFAULT_TEXT_COLOR_ROLE
            } else {
                childData.style.color_role = old_color_to_role(childData.style.color)
            }
            if (childData.style.background_color === undefined) {
                childData.style.background_color_role = DEFAULT_BACKGROUND_COLOR_ROLE
            } else {
                childData.style.background_color_role = old_color_to_role(childData.style.background_color)
            }

            // Convert notes to internal links where needed.
            if (['TextNote', 'CardNote', 'ImageNote'].includes(childData.type_name)) {
                if (childData.content === undefined) {
                    throw new Error('Content is missing')
                } else if (childData.content.url) {
                    let url: string = childData.content.url
                    if (url.startsWith('pamet:/p')) {
                        childData.content.url = url.replace('pamet:/p', 'project:/page')
                    }
                }
                childData.type_name = 'CardNote'
            }

            // Set empty content where missing
            if (childData.content === undefined) {
                childData.content = {}
            }

            // Set empty metadata where missing
            if (childData.metadata === undefined) {
                childData.metadata = {}
            }

            // Convert image metadata to the new schema
            // Load image metadata and delete the field
            let image_size = childData.metadata.image_size
            let image_md5 = childData.metadata.image_md5

            let image_width: number | undefined = undefined;
            let image_height: number | undefined = undefined;

            if (image_size !== undefined) {
                [image_width, image_height] = image_size;
                delete childData.metadata.image_size;
            }

            if (image_md5 !== undefined) {
                delete childData.metadata.image_md5;
            }

            // Local image url is either an internal url or a fs path
            let local_image_url = childData.content.local_image_url;
            if (local_image_url !== undefined) {
                delete childData.content.local_image_url;

                if (image_width === undefined) {
                    log.warning('Unexpected: note with local_image_url has no image_size', childData)
                    image_width = 0;
                    // This would cause bad rendering if the image is a card note, but that's
                    // a very rare case. During the migration those should be covered
                }
                if (image_height === undefined) {
                    image_height = 0;
                }

                if (local_image_url.startsWith('pamet:/p')) { // local media
                    childData.content.image = {
                        url: local_image_url.replace('pamet:/p', 'project:/p'),
                        width: image_width,
                        height: image_height,
                    }
                } else {
                    childData.content.image = { // file system media
                        url: 'project:/desktop/fs' + local_image_url,
                        width: image_width,
                        height: image_height,
                    }
                }
            }

            // Image url (in the v4 schema) is either a local path or a remote url

            if (childData.content.image_url !== undefined) {
                if (childData.content.image === undefined) {
                    log.error('Unexpected: note with image_url has no local_image_url')
                }
                delete childData.content.image_url
            }

            // Convert arrows to the new format
            if (childData.type_name === 'Arrow') {
                // Convert tail and head to EndPointProps format
                childData.tail = {
                    position: childData.tail_coords ? [childData.tail_coords[0], childData.tail_coords[1]] : null,
                    noteAnchorId: childData.tail_note_id || null,
                    noteAnchorType: childData.tail_anchor ? childData.tail_anchor.toLowerCase() : 'none'
                };
                delete childData.tail_coords;
                delete childData.tail_note_id;
                delete childData.tail_anchor;

                childData.head = {
                    position: childData.head_coords ? [childData.head_coords[0], childData.head_coords[1]] : null,
                    noteAnchorId: childData.head_note_id || null,
                    noteAnchorType: childData.head_anchor ? childData.head_anchor.toLowerCase() : 'none'
                };
                delete childData.head_coords;
                delete childData.head_note_id;
                delete childData.head_anchor;

                // Convert mid points
                const midPointCoords = childData.mid_point_coords || [];
                childData.mid_points = [];
                for (const coords of midPointCoords) {
                    if (!Array.isArray(coords) || coords.length < 2) {
                        log.warning('Invalid mid point coordinates', coords);
                        childData.mid_points.push([0, 0]);
                    } else {
                        childData.mid_points.push([coords[0], coords[1]]);
                    }
                }
                delete childData.mid_point_coords;

                // Convert style properties
                childData.style = {
                    color_role: old_color_to_role(childData.color),
                    line_type: childData.line_type || 'solid',
                    thickness: childData.line_thickness || 1,
                    line_function: childData.line_function_name || 'bezier_cubic',
                    head_shape: childData.head_shape || 'arrow',
                    tail_shape: childData.tail_shape || 'arrow'
                };
                delete childData.color;
                delete childData.line_type;
                delete childData.line_thickness;
                delete childData.line_function_name;
                delete childData.head_shape;
                delete childData.tail_shape;
            }

            return childData;
        }


        // 1. Fetch raw data
        progressCallback(-1, 'Fetching repository data...');
        const pagesUrl = this.endpointUrl('pages');
        const rawPagesData: any[] = await this.get(pagesUrl);

        let allMigratedEntities: any[] = [];

        // Push the raw page data directly, as it doesn't need color migration.
        // The tmpDynamicMigration function doesn't apply to pages anyway.
        for (const pageData of rawPagesData) {
            allMigratedEntities.push(pageData);
        }

        // Fetch children for each page and migrate them
        let pageCount = rawPagesData.length;
        let pagesProcessed = 0;
        for (const pageData of rawPagesData) {
            pagesProcessed++;
            progressCallback(20 + 30 * (pagesProcessed / pageCount), `Fetching page content ${pagesProcessed}/${pageCount}...`);
            const childrenUrl = this.endpointUrl(`/p/${pageData.id}/children`);
            const childrenData = await this.get(childrenUrl);
            allMigratedEntities.push(...childrenData.notes.map(tmpDynamicMigration));
            allMigratedEntities.push(...childrenData.arrows.map(tmpDynamicMigration));
        }

        // Create a map of pageId to pageData for fixing internal links
        const pageIdToName: Record<string, string> = {};
        for (const pageData of rawPagesData) {
            pageIdToName[pageData.id] = pageData.name;
            log.info(`Page ${pageData.id} (${pageData.name}) added to pageIdToName map`);
        }

        // Fix internal links to include the page name as .text
        for (const entityData of allMigratedEntities) {
            if (entityData?.content?.url?.startsWith('project:/page/')) {
                let pageId: string | undefined;
                // Extract pageId from the URL
                const urlParts = entityData.content.url.split('/');
                if (urlParts.length < 3) {
                    log.error(`Invalid internal link URL: ${entityData.content.url}`);
                    continue;
                }
                pageId = urlParts[2]; // e.g. 'p/12345' -> '12345'
                if (pageId && pageIdToName[pageId]) {
                    entityData.content.text = pageIdToName[pageId];
                    entityData.content.url = new PametRoute({ pageId: pageId }).toProjectScopedURI();
                } else {
                    log.warning(`Internal link note ${entityData.id} points to unknown page from url ${entityData.content.url} parts: ${JSON.stringify(entityData.content.url.split('/'))}`);
                    entityData.content.text = '(missing page)';
                    entityData.content.url = '';
                }
            }
        }

        // 3. Separate image notes from others
        const imageNoteDatas: Record<string, any>[] = [];
        const otherEntityDatas: Record<string, any>[] = [];

        for (const entityData of allMigratedEntities) {
            if (entityData.content?.image?.url?.startsWith('project:/desktop/fs')) {
                imageNoteDatas.push(entityData);
            } else {
                otherEntityDatas.push(entityData);
            }
        }

        // 4. Process entities
        progressCallback(50, 'Processing entities...');
        for (const entityData of otherEntityDatas) {
            const entity = loadFromDict(entityData as SerializedEntityData);
            pamet.insertOne(entity);
        }

        // 5. Process image notes
        progressCallback(50, 'Processing image notes...');
        let imageNoteCounter = 0
        let imageRelatedEntities = []
        for (const imageData of imageNoteDatas) {
            const imageUrl = imageData.content.image.url; // e.g. 'project:/desktop/fs/C:/Users/user/image.png'
            const fsPath = imageUrl.replace('project:/desktop/fs', '');

            // Fetch image blob from desktop server
            const blobUrl = this.endpointUrl(`desktop/fs${fsPath}`);
            let mediaItem: MediaItem;
            try {
                const blob = await this.getBlob(blobUrl);
                mediaItem = await pamet.addMediaToStore(blob, fsPath, imageData.id);
            } catch (e) {
                log.error(`Failed to import image for note ${imageData.id} from path ${fsPath}`, e);
                continue
            }

            imageRelatedEntities.push(mediaItem);

            // Update imageNoteData
            imageData.content.image_id = mediaItem.id;
            delete imageData.content.image; // remove the old image url structure
            const imageNote = loadFromDict(imageData as SerializedEntityData);
            imageRelatedEntities.push(imageNote);

            imageNoteCounter++;
            progressCallback(50 + 50 * (imageNoteCounter / imageNoteDatas.length), `Importing media files... ${imageNoteCounter}/${imageNoteDatas.length}`);
        }

        // Add image related entities to the store
        for (const entity of imageRelatedEntities) {
            pamet.insertOne(entity);
        }

        progressCallback(1, 'Import complete.');
    }

    public async getBlob(url: string, timeout = 20000): Promise<Blob> {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);

        const requestRepr = `'GET ${url}' (blob)`;

        const options: RequestInit = {
            method: 'GET',
            signal: controller.signal,
        };

        let response: Response;
        try {
            response = await Promise.race([
                fetch(url, options),
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error(`Request ${requestRepr} timed out`)), timeout)
                )
            ]) as Response;
        } catch (error: any) {
            if (error.name === 'AbortError') {
                throw new Error(`Request ${requestRepr} timed out`);
            }
            throw error;
        }
        clearTimeout(id);

        if (response.ok) {
            return await response.blob();
        } else {
            log.error(`Request to ${response.url} for blob failed with status ${response.status}: ${response.statusText}`);
            throw new Error(response.statusText);
        }
    }
}
