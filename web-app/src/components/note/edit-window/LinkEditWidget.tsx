// LinkEditWidget.tsx
import React, { useState, useEffect, useRef } from 'react';
import { SerializedNote } from "@/model/Note";
import { PametTabIndex } from "@/core/constants";
import { Page } from '@/model/Page';
import { pamet } from '@/core/facade';
import { PametRoute } from '@/services/routing/route';
import './LinkEditWidget.css';

interface SuggestionListProps {
    suggestions: Page[];
    onSelectPage: (page: Page) => void;
    highlightedIndex: number;
}

const SuggestionList: React.FC<SuggestionListProps> = ({ suggestions, onSelectPage, highlightedIndex }) => {
    if (suggestions.length === 0) {
        return null;
    }

    return (
        <ul className="suggestion-list">
            {suggestions.map((page, index) => (
                <li
                    key={page.id}
                    className={`suggestion-item ${index === highlightedIndex ? 'highlighted' : ''}`}
                    onMouseDown={(e) => { // Use onMouseDown to avoid input blur
                        e.preventDefault();
                        onSelectPage(page);
                    }}
                >
                    {page.name}
                </li>
            ))}
        </ul>
    );
};

interface LinkEditWidgetProps {
    noteData: SerializedNote;
    updateNoteData: (newData: Partial<SerializedNote>) => void;
    isDraggingOver: boolean;
}

export const LinkEditWidget: React.FC<LinkEditWidgetProps> = ({ noteData, updateNoteData, isDraggingOver }) => {
    const [inputValue, setInputValue] = useState(noteData.content.url || '');
    const [suggestions, setSuggestions] = useState<Page[]>([]);
    const [selectedInternalLink, setSelectedInternalLink] = useState<Page | null>(null);
    const [highlightedIndex, setHighlightedIndex] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);

    // Sync local state from note data; render pill + empty input for internal links
    useEffect(() => {
        const link = noteData.content.url || '';
        if (link.startsWith('project://')) {
            const route = PametRoute.fromUrl(link);
            if (route.pageId) {
                const page = pamet.page(route.pageId);
                if (page) {
                    setSelectedInternalLink(page);
                    setInputValue(''); // keep the text area empty while pill shows the link
                    return;
                }
            }
        }
        setSelectedInternalLink(null);
        setInputValue(link);
    }, [noteData.content.url]);

    useEffect(() => { inputRef.current?.focus(); }, []);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setInputValue(value);
        updateNoteData({ content: { ...noteData.content, url: value } });

        if (value.startsWith('project://')) {
            const route = PametRoute.fromUrl(value);
            if (route.pageId) {
                const page = pamet.page(route.pageId);
                setSelectedInternalLink(page ?? null);
            } else {
                setSelectedInternalLink(null);
            }
            setSuggestions([]);
        } else {
            setSelectedInternalLink(null);
            if (value) {
                const pages = Array.from(pamet.pages());
                const filtered = pages
                    .filter(p => p.name.toLowerCase().includes(value.toLowerCase()))
                    .slice(0, 10);
                setSuggestions(filtered);
                setHighlightedIndex(filtered.length ? 0 : -1);
            } else {
                setSuggestions([]);
                setHighlightedIndex(-1);
            }
        }
    };

    const handleSelectPage = (page: Page) => {
        const route = new PametRoute();
        route.pageId = page.id;
        const uri = route.toProjectScopedURI();
        updateNoteData({ content: { ...noteData.content, url: uri, text: page.name } });
        setSelectedInternalLink(page);
        setInputValue(''); // keep empty text; pill represents the link
        setSuggestions([]);
        setHighlightedIndex(-1);
        // keep focus for continued typing after the pill
        requestAnimationFrame(() => inputRef.current?.focus());
    };

    const handleRemoveInternalLink = () => {
        // Also clear the text property
        updateNoteData({ content: { ...noteData.content, url: '', text: '' } });
        setSelectedInternalLink(null);
        setInputValue('');
        requestAnimationFrame(() => inputRef.current?.focus());
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        // Remove pill on Backspace when input is empty and caret at start
        if (
            e.key === 'Backspace' &&
            selectedInternalLink &&
            inputRef.current &&
            inputRef.current.selectionStart === 0 &&
            inputRef.current.selectionEnd === 0 &&
            inputValue.length === 0
        ) {
            e.preventDefault();
            handleRemoveInternalLink();
            return;
        }

        if (suggestions.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setHighlightedIndex(prev => (prev + 1) % suggestions.length);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setHighlightedIndex(prev => (prev - 1 + suggestions.length) % suggestions.length);
        } else if (e.key === 'Enter') {
            if (highlightedIndex >= 0) {
                e.preventDefault();
                handleSelectPage(suggestions[highlightedIndex]);
            }
        } else if (e.key === 'Escape') {
            setSuggestions([]);
            setHighlightedIndex(-1);
        }
    };

    const showGetTitleButton = (inputValue.trim().length > 0) && !selectedInternalLink;

    return (
        <div className="link-container">
            <div className="link-input-wrapper" style={{ pointerEvents: isDraggingOver ? 'none' : 'auto' }}>
                {selectedInternalLink && (
                    <div className="pill pill--inline" title={selectedInternalLink.name}>
                        <span className="pill-text">{selectedInternalLink.name}</span>
                        <button
                            onClick={handleRemoveInternalLink}
                            className="remove-pill-button"
                            tabIndex={PametTabIndex.NoteEditView_InternalLinkRemoveButton}
                            aria-label="Remove internal link"
                        >
                            ×
                        </button>
                    </div>
                )}

                <input
                    ref={inputRef}
                    type="text"
                    placeholder="URL or type to search pages"
                    className="link-input"
                    tabIndex={PametTabIndex.NoteEditView_LinkInput}
                    value={inputValue}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    onBlur={() => setTimeout(() => setSuggestions([]), 100)}
                />
            </div>

            <SuggestionList
                suggestions={suggestions}
                onSelectPage={handleSelectPage}
                highlightedIndex={highlightedIndex}
            />

            <div
                className={`get-title-button-wrapper ${showGetTitleButton ? '' : 'is-hidden'}`}
                aria-hidden={!showGetTitleButton}
            >
                <button
                    className="get-title-button"
                    onClick={() => alert('No dice. Will be available on cloud account login and the desktop app.')}
                    tabIndex={PametTabIndex.NoteEditView_LinkGetTitleButton}
                >
                    Get title
                </button>
            </div>
        </div>
    );
};
