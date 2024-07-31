import { DEFAULT_BACKGROUND_COLOR, DEFAULT_TEXT_COLOR } from "../core/constants";
import { PageQueryFilter } from "../core/facade";
import { Page, PageData } from "../model/Page";
import { Note } from "../model/Note";
import { Arrow } from "../model/Arrow";
import { getLogger } from "pyfusion/logging";
import { BaseApiClient } from "pyfusion/storage/BaseApiClient";
import { SerializedEntityData, loadFromDict } from "pyfusion/libs/Entity";
import { elementId } from "../model/Element";

let log = getLogger('ApiClient');


export class ApiClient extends BaseApiClient {
    // Get pages metadata
    async pages(filter: PageQueryFilter = {}): Promise<Array<Page>> {
        let url = this.endpointUrl('pages');
        let query = '';
        // If filter is not empty, add it to the query
        if (Object.keys(filter).length !== 0) {
            query = '?' + new URLSearchParams(filter);
        }
        let data = await this.get(url + query);

        let pages = data.map((pageData: PageData) => {
            return new Page(pageData);
        });
        return pages;
    }
    async children(pageId: string): Promise<{ notes: Note[], arrows: Arrow[] }> {
        let url = this.endpointUrl(`/p/${pageId}/children`);
        let data = await this.get(url);

        let notesData = data.notes;
        let arrowsData = data.arrows;

        // TODO: synchronize that with the python implementation
        // Convert the id in format [page_id, own_id] to
        // page_id and own_id to be compatible with the
        // Note and Arrow data structures
        // Convert notes to internal links where needed.

        // This should be translated to a db migration when the main web
        // app is finished and the final integration begins.
        function tmpDynamicMigration(childData: Record<string, any>) {
            // Additional tasks for the migration:
            // - Add size metadata for images where it's missing

            let [page_id, own_id] = childData.id;
            if (page_id === undefined || own_id === undefined) {
                throw new Error('Bad id')
            }
            childData.id = elementId(page_id, own_id);

            // Fill style where missing
            if (childData.style === undefined) {
                childData.style = {}
            }
            if (childData.style.color === undefined) {
                childData.style.color = [...DEFAULT_TEXT_COLOR]
            }
            if (childData.style.background_color === undefined) {
                childData.style.background_color = [...DEFAULT_BACKGROUND_COLOR]
            }

            // Convert notes to internal links where needed.
            if (['TextNote', 'CardNote', 'ImageNote'].includes(childData.type_name)) {
                if (childData.content === undefined) {
                    throw new Error('Content is missing')
                } else if (childData.content.url) {
                    let url: string = childData.content.url
                    if (url.startsWith('pamet:/p')) {
                        childData.type_name = 'InternalLinkNote'
                    } else {
                        childData.type_name = 'ExternalLinkNote'
                    }
                }
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
                    log.error('Unexpected: note with local_image_url has no image_size', childData)
                    image_width = 0;
                    // This would cause bad rendering if the image is a card note, but that's
                    // a very rare case. During the migration those should be covered
                }
                if (image_height === undefined) {
                    image_height = 0;
                }

                if (local_image_url.startsWith('pamet:/p')) { // local media
                    childData.content.image = {
                        url: local_image_url,
                        width: image_width,
                        height: image_height,
                    }
                } else {
                    childData.content.image = { // file system media
                        url: 'pamet:/desktop/fs' + local_image_url,
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

            return childData;
        }

        let notes = notesData.map((noteData: any) => {
            return loadFromDict(tmpDynamicMigration(noteData) as SerializedEntityData);
        });
        let arrows = arrowsData.map((arrowData: any) => {
            return loadFromDict(tmpDynamicMigration(arrowData) as SerializedEntityData);
        })
        return {
            notes: notes,
            arrows: arrows,
        };
    }
}
