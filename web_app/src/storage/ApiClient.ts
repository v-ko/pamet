import { DEFAULT_BACKGROUND_COLOR, DEFAULT_TEXT_COLOR } from "../constants";
import { PageQueryFilter } from "../facade";
import { Page, PageData } from "../model/Page";
import { Note } from "../model/Note";
import { Arrow } from "../model/Arrow";
import { getLogger } from "../fusion/logging";
import { BaseApiClient } from "../fusion/storage/BaseApiClient";
import { loadFromDict } from "../fusion/libs/Entity";

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
        function tmpDynamicMigration(childData) {
            let [page_id, own_id] = childData.id;
            if (page_id === undefined || own_id === undefined) {
                throw new Error('Bad id')
            }
            childData.page_id = page_id;
            childData.own_id = own_id;
            delete childData.id;

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
                    }
                }
            }

            // Set empty content where missing
            if (childData.content === undefined) {
                childData.content = {}
            }

            // Convert image metadata to the new schema
            let local_image_url = childData.content.local_image_url;
            if (local_image_url !== undefined) {
                delete childData.content.local_image_url;

                if (local_image_url.startsWith('pamet:/p')) { // local media
                    childData.content.image = {
                        url: local_image_url,
                        width: 0,
                        height: 0,
                    }
                } else {
                    childData.content.image = { // file system media
                        url: 'pamet:/desktop/fs' + local_image_url,
                        width: 0,
                        height: 0,
                    }
                }
            }
            if (childData.content.image_url === undefined) {
                delete childData.content.image_url
            }

            return childData;
        }

        let notes = notesData.map((noteData: any) => {
            return loadFromDict(tmpDynamicMigration(noteData));
        });
        let arrows = arrowsData.map((arrowData: any) => {
            return loadFromDict(tmpDynamicMigration(arrowData));
        })
        return {
            notes: notes,
            arrows: arrows,
        };
    }
}
