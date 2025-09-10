import { Charset, Document, Encoder } from 'flexsearch';
import { getLogger } from 'fusion/logging';
import { Note } from '@/model/Note';
import { Page } from '@/model/Page';
import slugify from 'slugify';

const log = getLogger('SearchService');

export interface NoteSearchResult {
    id: string;
    parentId: string;
    text: string;
    url?: string;
}

export interface PageSearchResult {
    id: string;
    name: string;
}

export interface NotesSearchFilter {
    pageId?: string; // Filter notes by parent page ID
}

export interface NoteSearchResultWithHighlight {
    id: string;
    textHighlight?: string;
    urlHighlight?: string;
    field: string; // Which field matched
}

// Document types for FlexSearch - need to have index signature for DocumentData
interface NoteDocument {
    id: string;
    parentId: string;
    content: string; // Combined text + url content
    [key: string]: any; // Required for DocumentData constraint
}

interface PageDocument {
    id: string;
    name: string;
    [key: string]: any; // Required for DocumentData constraint
}

export class SearchService {
    private _notesIndex: Document<NoteDocument> | null = null;
    private _pagesIndex: Document<PageDocument> | null = null;
    private _isInitialized = false;

    constructor() {
        // Initialize Document indices with appropriate configurations
        this._notesIndex = new Document<NoteDocument>({
            tokenize: 'forward',
            id: 'id',
            tag: 'parentId', // Use parentId as tag for page-specific filtering
            store: true, // Store documents for enriched results
            resolution: 9,
            index: ['content'], // Index the content field
        });

        const pageTitleEncoder = new Encoder({
            normalize: slugify
        }).assign(Charset.LatinSoundex)
        this._pagesIndex = new Document<PageDocument>({
            tokenize: 'forward', // More fuzzy for page titles
            // encoder: pageTitleEncoder,
            resolution: 9,
            document: {
                id: 'id',
                index: ['name'], // Index the name field
            }
        });
    }

    get isInitialized(): boolean {
        return this._isInitialized;
    }

    /**
     * Initialize or re-initialize the search indices with project data
     * This should be called when switching projects
     */
    async initializeIndices(notes: Note[], pages: Page[]): Promise<void> {
        log.info('Initializing search indices with', notes.length, 'notes and', pages.length, 'pages');

        // Clear existing indices
        this.clear();

        // Index all notes
        for (const note of notes) {
            this.addNote(note);
        }

        // Index all pages
        for (const page of pages) {
            this.addPage(page);
        }

        this._isInitialized = true;
        log.info('Search indices initialized successfully');
    }    /**
     * Add a single note to the search index
     */
    addNote(note: Note): void {
        if (!this._notesIndex) return;

        const document: NoteDocument = {
            id: note.id,
            parentId: note.parentId,
            content: this._buildCombinedContent(note)
        };

        // Debug logging for a specific note content
        if (document.content.toLowerCase().includes('glasgow') || document.content.toLowerCase().includes('coma')) {
            console.log('SearchService: Adding Glasgow/coma note to index:', document);
        }

        this._notesIndex.add(document);
    }

    /**
     * Update a note in the search index
     */
    updateNote(note: Note): void {
        if (!this._notesIndex) return;

        const document: NoteDocument = {
            id: note.id,
            parentId: note.parentId,
            content: this._buildCombinedContent(note)
        };
        this._notesIndex.update(document);
    }

    /**
     * Remove a note from the search index
     */
    removeNote(noteId: string): void {
        if (!this._notesIndex) return;
        this._notesIndex.remove(noteId);
    }

    /**
     * Add a single page to the search index
     */
    addPage(page: Page): void {
        if (!this._pagesIndex) return;

        const document: PageDocument = {
            id: page.id,
            name: slugify(page.name)
        };
        this._pagesIndex.add(document);
    }

    /**
     * Update a page in the search index
     */
    updatePage(page: Page): void {
        if (!this._pagesIndex) return;

        const document: PageDocument = {
            id: page.id,
            name: page.name
        };
        this._pagesIndex.update(document);
    }

    /**
     * Remove a page from the search index
     */
    removePage(pageId: string): void {
        if (!this._pagesIndex) return;
        this._pagesIndex.remove(pageId);
    }

    /**
     * Search pages by title
     */
    searchPages(query: string, limit: number = 20): string[] {
        query = slugify(query)

        if (!this._pagesIndex || !this._isInitialized) {
            log.warning('Pages index not initialized, returning empty results');
            return [];
        }

        const results = this._pagesIndex.search(query, {
            limit,
            suggest: true,
            enrich: false // We just want IDs for now
        });

        // Extract IDs from Document search results
        if (Array.isArray(results)) {
            const ids: string[] = [];
            for (const fieldResult of results) {
                if (fieldResult.result && Array.isArray(fieldResult.result)) {
                    ids.push(...fieldResult.result as string[]);
                }
            }
            return [...new Set(ids)]; // Remove duplicates
        }

        return [];
    }

    /**
     * Search notes with highlighting support
     */
    searchNotes(query: string, filter?: NotesSearchFilter, limit: number = 50): Array<{ id: string, highlight: string }> {
        if (!this._notesIndex || !this._isInitialized) {
            log.warning('Notes index not initialized, returning empty results');
            return [];
        }

        log.info(`Searching notes for query "${query}" with filter`, filter);

        const searchOptions: any = {
            limit: limit,
            suggest: true,
            enrich: true, // Need enriched results for highlighting
            highlight: {
                template: '<mark>$1</mark>', // Use <mark> tag for highlighting
                boundary: 200, // Limit total length to keep snippets reasonable
                merge: true // Merge consecutive matches
            }
        };

        // If pageId filter is specified, use tag search
        if (filter?.pageId) {
            searchOptions.tag = { parentId: filter.pageId };
        }

        const results = this._notesIndex.search(query, searchOptions);

        // Extract highlighted results from Document search results
        const highlightedResults: Array<{ id: string, highlight: string }> = [];

        if (!Array.isArray(results)) {
            log.warning('Unexpected search results format:', results);
            return [];
        }
        log.info(`Search returned ${results.length} field results`);
        for (const fieldResult of results) {
            if (!fieldResult.result || !Array.isArray(fieldResult.result)) {
                log.warning('Unexpected fieldResult format:', fieldResult);
                continue;
            }
            for (const item of fieldResult.result) {
                // Use any type to handle FlexSearch's dynamic result structure
                const resultItem = item as any;
                if (!resultItem || !(typeof resultItem === 'object') || !resultItem.id || !resultItem.highlight) {
                    log.warning('Unexpected result item format:', resultItem);
                    continue;
                }
                highlightedResults.push({
                    id: String(resultItem.id),
                    highlight: String(resultItem.highlight)
                });
            }
        }

        return highlightedResults;
    }

    /**
     * Build combined content from note text and URL
     */
    private _buildCombinedContent(note: Note): string {
        const parts: string[] = [];

        if (note.text) {
            parts.push(note.text);
        }

        if (note.content.url) {
            parts.push(note.content.url);
        }

        return parts.join('\n'); // Separate text and URL with newline
    }

    /**
     * Clear all search indices
     */
    clear(): void {
        if (this._notesIndex) {
            this._notesIndex.clear();
        }
        if (this._pagesIndex) {
            this._pagesIndex.clear();
        }
        this._isInitialized = false;
        log.info('Search indices cleared');
    }
}
