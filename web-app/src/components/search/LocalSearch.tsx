import React, { useState, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import './LocalSearch.css';
import { LocalSearchViewState } from './LocalSearchViewState';
import { pamet } from '@/core/facade';
import { appActions } from '@/actions/app';
import { pageActions } from '@/actions/page';
import { Point2D } from 'fusion/primitives/Point2D';
import { PageAnimation } from '@/components/page/render-utils';
import { SEARCH_RESULT_ANIMATION_TIME } from '@/core/constants';

interface SearchResultItem {
    id: string;
    type: 'note';
    title: string;
    snippet?: string;
}

interface LocalSearchProps {
    state: LocalSearchViewState;
}

export const LocalSearch: React.FC<LocalSearchProps> = observer(({ state }) => {
    const [query, setQuery] = useState(state.query);
    const [results, setResults] = useState<SearchResultItem[]>([]);
    const [selectedIndex, setSelectedIndex] = useState(0);

    // Search function
    const performSearch = (searchQuery: string) => {
        if (!searchQuery.trim()) {
            setResults([]);
            return;
        }

        // Get current page ID for local search filtering
        const currentPageId = pamet.appViewState.currentPageId;

        // Search notes with highlighting - filter by current page if available
        const highlightedResults = pamet.searchService.searchNotes(
            searchQuery,
            currentPageId ? { pageId: currentPageId } : undefined,
            20
        );

        console.log(`LocalSearch: Query "${searchQuery}" returned ${highlightedResults.length} results`);

        console.log('LocalSearch: Got', highlightedResults.length, 'highlighted results for query:', JSON.stringify(searchQuery));

        const searchResults: SearchResultItem[] = [];

        // Add highlighted note results
        for (const result of highlightedResults) {
            const note = pamet.note(result.id);
            if (note) {
                searchResults.push({
                    id: result.id,
                    type: 'note',
                    title: result.highlight || note.text || 'Untitled Note', // Use highlighted content as title
                    snippet: note.content.url ? `URL: ${note.content.url}` : undefined
                });
            }
        }

        setResults(searchResults);
        setSelectedIndex(0);
    };

    // Update search when query changes
    useEffect(() => {
        const debounceTimer = setTimeout(() => {
            performSearch(query);
        }, 300);

        return () => clearTimeout(debounceTimer);
    }, [query]);

    // Handle keyboard navigation
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                appActions.closeLocalSearch(pamet.appViewState);
            } else if (event.key === 'ArrowDown') {
                event.preventDefault();
                setSelectedIndex(prevIndex => Math.min(prevIndex + 1, results.length - 1));
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                setSelectedIndex(prevIndex => Math.max(prevIndex - 1, 0));
            } else if (event.key === 'Enter') {
                event.preventDefault();
                if (results[selectedIndex]) {
                    handleResultClick(results[selectedIndex]);
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [results, selectedIndex]);

    const handleResultClick = (result: SearchResultItem) => {
        console.log('Search result clicked:', result);

        // Since this is notes-only search, we only handle note results
        if (result.type === 'note') {
            console.log('Navigate to note:', result.id);

            // Get the note and navigate to its position
            const note = pamet.note(result.id);
            if (note && note.geometry) {
                // Calculate the center of the note
                const noteX = note.geometry[0] + note.geometry[2] / 2; // x + width/2
                const noteY = note.geometry[1] + note.geometry[3] / 2; // y + height/2
                const noteCenter = new Point2D([noteX, noteY]);

                // Get current page view state
                const currentPageVS = pamet.appViewState.currentPageViewState;
                if (currentPageVS) {
                    // Store current viewport state for animation
                    const currentCenter = currentPageVS.viewportCenter.copy();
                    const currentHeight = currentPageVS.viewportHeight;

                    // Update viewport to center on the note (this is the main state change)
                    pageActions.updateViewport(currentPageVS, noteCenter, currentHeight);

                    // Add smooth animation overlay using the animation service
                    // This will smoothly transition FROM the old state TO the new state
                    PageAnimation.viewportChangeAnimation(
                        currentPageVS.page().id,
                        currentCenter, // start from the old viewport center
                        currentHeight,
                        noteCenter, // animate to the new center
                        currentHeight, // keep same zoom level
                        SEARCH_RESULT_ANIMATION_TIME
                    );

                    // Select the note
                    let noteVS = currentPageVS.viewStateForElementId(note.id)
                    if (noteVS) {
                        pageActions.clearSelection(currentPageVS)
                        pageActions.updateSelection(currentPageVS, new Map([[noteVS, true]]));
                    }
                }
            }
        }

        appActions.closeLocalSearch(pamet.appViewState);
    };

    return (
        <div className="local-search">
            <input
                type="text"
                className="local-search-input"
                placeholder="Search notes in this page..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                autoFocus
                onBlur={() => {
                    // Close search when clicked outside
                    setTimeout(() => {
                        if (pamet.appViewState.localSearchViewState !== null) {
                            appActions.closeLocalSearch(pamet.appViewState);
                        }
                    }, 200);
                }}
            />

            <ul className="local-search-results">
                {results.length === 0 && query.trim() ? (
                    <div className="local-search-no-results">No results found</div>
                ) : (
                    results.map((result, index) => (
                        <li
                            key={result.id}
                            className={index === selectedIndex ? 'selected' : ''}
                            onClick={(e) => {
                                e.stopPropagation();
                                handleResultClick(result);
                            }}
                            onMouseEnter={() => setSelectedIndex(index)}
                        >
                            <div
                                className="local-search-result-title"
                                dangerouslySetInnerHTML={{ __html: result.title }}
                            />
                            {result.snippet && (
                                <div className="local-search-result-snippet">{result.snippet}</div>
                            )}
                        </li>
                    ))
                )}
            </ul>
        </div>
    );
});
