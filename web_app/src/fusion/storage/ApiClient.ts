import { RepositoryClient } from "./BaseRepositoryClient";
import { getLogger } from "../logging";
import { PageQueryFilter } from "../../facade";
import { Page, PageData } from "../../model/Page";
import { Note } from "../../model/Note";
import { Arrow } from "../../model/Arrow";
import { DEFAULT_BACKGROUND_COLOR, DEFAULT_TEXT_COLOR } from "../../constants";

let log = getLogger('ApiClient');

export class ApiClient extends RepositoryClient {
    host: string; //
    port?: number;
    path: string; // Url path with a leading slash

    constructor(host: string = 'http://localhost', port?: number, path: string = '') {
        super();

        //Handle trailing slashes in host and path
        if (host.endsWith('/')) {
            host = host.slice(0, -1);
        }
        if (path.endsWith('/')) {
            path = path.slice(0, -1);
        }

        // Handle missing slash in path
        if (!path.startsWith('/')) {
            if (path !== ''){
                log.warning(`ApiClient: path "${path}" missing leading slash, adding /`);
            }
            path = '/' + path;
        }

        // Handle missing protocol
        if (!host.startsWith('http')) {
            host = 'http://' + host;
            log.warning(`ApiClient: host ${host} missing protocol, adding http://`);
        }

        // Set default port based on protocol if port is not provided
        if (!port) {
            const url = new URL(host);
            this.port = url.protocol === 'https:' ? 443 : 80;
        } else {
            this.port = port;
        }

        this.host = host;
        this.port = port;
        this.path = path;
    }

    // Form a url from the endpoint
    endpointUrl(endpoint: string): string {
        if (endpoint.startsWith('/')) {
            endpoint = endpoint.slice(1);
        }
        let path = this.path;
        if (!path.endsWith('/')) {
            path = path + '/';
        }
        let url = `${this.host}:${this.port}${this.path}${endpoint}`
        // log.info('host, port, path, endpoint, url', this.host, this.port, path, endpoint, url)
        return url;
    }

    async fetchData(url: string): Promise<any> {
        // let responce = await fetch(url);
        // nocache!!
        let responce = await fetch(url, {cache: "no-cache"});
        if (responce.ok) {
            let responceJson = await responce.json();
            let responceData = responceJson.data;
            return responceData;
        } else {
            throw new Error(responce.statusText);
        }
    }

    // Get pages metadata
    async pages(filter: PageQueryFilter = {}): Promise<Array<Page>> {
        let url = this.endpointUrl('pages');
        let query = '';
        // If filter is not empty, add it to the query
        if (Object.keys(filter).length !== 0) {
            query = '?' + new URLSearchParams(filter);
        }
        let data = await this.fetchData(url + query);
        let pages = data.map((pageData: PageData) => {
            return new Page(pageData);
        });
        return pages;
    }
    async children(pageId: string): Promise<{ notes: Note[], arrows: Arrow[] }> {
        let url = this.endpointUrl(`/p/${pageId}/children`);
        let data = await this.fetchData(url);
        let notesData = data.notes;
        let arrowsData = data.arrows;

        // TODO: synchronize that with the python implementation
        // Convert the id in format [page_id, own_id] to
        // page_id and own_id to be compatible with the
        // Note and Arrow data structures
        function convertIdAndFillStyle(childData) {
            let [page_id, own_id] = childData.id;
            if (page_id === undefined || own_id === undefined) {
                throw new Error('FUCK')
            }
            childData.page_id = page_id;
            childData.own_id = own_id;
            delete childData.id;

            // Fill style where missing
            if (childData.style === undefined){
                childData.style = {}
            }
            if (childData.style.color === undefined){
                childData.style.color = [...DEFAULT_TEXT_COLOR]
            }
            if (childData.style.background_color === undefined){
                childData.style.background_color = [...DEFAULT_BACKGROUND_COLOR]
            }

            return childData;
        }

        let notes = notesData.map((noteData: any) => {
            return new Note(convertIdAndFillStyle(noteData));
        });
        let arrows = arrowsData.map((arrowData: any) => {
            return new Arrow(convertIdAndFillStyle(arrowData));
        })
        return {
            notes: notes,
            arrows: arrows,
        };
    }
}
