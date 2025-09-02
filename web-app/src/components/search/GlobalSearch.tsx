import React, { useState, useEffect, useRef } from 'react';
import { observer } from 'mobx-react-lite';
import './GlobalSearch.css';
import { GlobalSearchViewState } from './GlobalSearchViewState';
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
    pageId: string;
    pageName: string;
}

interface GlobalSearchProps {
    state: GlobalSearchViewState;
}

export const GlobalSearch: React.FC<GlobalSearchProps> = observer(({ state }) => {
    const [query, setQuery] = useState(state.query);
    const [results, setResults] = useState<SearchResultItem[]>([]);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);

    // Search function
    const performSearch = (searchQuery: string) => {
        if (!searchQuery.trim()) {
            setResults([]);
            return;
        }

        // Search notes globally (no page filter)
        const highlightedResults = pamet.searchService.searchNotes(
            searchQuery,
            undefined, // No page filter for global search
            1000 // Max 1000 results
        );

        console.log(`GlobalSearch: Query "${searchQuery}" returned ${highlightedResults.length} results`);

        const searchResults: SearchResultItem[] = [];

        // Add highlighted note results
        for (const result of highlightedResults) {
            const note = pamet.note(result.id);
            if (note) {
                // Find the page containing this note
                const page = pamet.page(note.page_id);
                const pageName = page ? page.name : 'Unknown Page';

                searchResults.push({
                    id: result.id,
                    type: 'note',
                    title: result.highlight || note.text || 'Untitled Note',
                    pageId: note.page_id,
                    pageName: pageName
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
                appActions.closeGlobalSearch(pamet.appViewState);
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

    // Handle focus counter changes to focus and select input
    useEffect(() => {
        if (state.focusCounter > 0 && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [state.focusCounter]);

    const handleResultClick = (result: SearchResultItem) => {
        console.log('Global search result clicked:', result);

        // Navigate to the page containing the note first
        if (result.pageId !== pamet.appViewState.currentPageId) {
            appActions.setCurrentPage(pamet.appViewState, result.pageId);
        }

        // Get the note and navigate to its position
        const note = pamet.note(result.id);
        if (note && note.geometry) {
            // Calculate the center of the note
            const noteX = note.geometry[0] + note.geometry[2] / 2; // x + width/2
            const noteY = note.geometry[1] + note.geometry[3] / 2; // y + height/2
            const noteCenter = new Point2D([noteX, noteY]);

            // Get current page view state (may have changed after navigation)
            setTimeout(() => {
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
                    );                    // Select the note
                    let noteVS = currentPageVS.viewStateForElementId(note.id)
                    if (noteVS) {
                        pageActions.clearSelection(currentPageVS)
                        pageActions.updateSelection(currentPageVS, new Map([[noteVS, true]]));
                    }
                }
            }, 100); // Small delay to ensure page is loaded
        }
    };

    return (
        <div className="global-search">
            <div className="global-search-header">
                <input
                    ref={inputRef}
                    type="text"
                    className="global-search-input"
                    placeholder="Search in project..."
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    autoFocus
                />
                <button
                    className="global-search-close"
                    onClick={() => appActions.closeGlobalSearch(pamet.appViewState)}
                    title="Close search"
                >
                    ×
                </button>
            </div>

            {results.length > 0 && (
                <div className="global-search-result-count">
                    {results.length} result{results.length !== 1 ? 's' : ''} found
                    {results.length >= 1000 && ' (showing first 1000)'}
                </div>
            )}

            <ul className="global-search-results">
                {results.length === 0 && query.trim() ? (
                    <div className="global-search-no-results">No results found</div>
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
                                className="global-search-result-title"
                                dangerouslySetInnerHTML={{ __html: result.title }}
                            />
                            <div className="global-search-result-page">
                                in {result.pageName}
                            </div>
                        </li>
                    ))
                )}
            </ul>
        </div>
    );
});
