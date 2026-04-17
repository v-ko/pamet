// LinkEditWidget.tsx
import React, { useState, useEffect, useRef } from 'react';
import { SerializedNote } from "@/model/Note";
import { PametTabIndex } from "@/core/constants";
import { Page } from '@/model/Page';
import { pamet } from '@/core/facade';
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

  // Sync local state from note data: show pill for internal page link
  useEffect(() => {
    const pageRef = noteData.content.page_ref;
    if (pageRef) {
      const page = pamet.page(pageRef.id);
      if (page) {
        setSelectedInternalLink(page);
        setInputValue('');
        return;
      }
    }
    setSelectedInternalLink(null);
    setInputValue(noteData.content.url || '');
  }, [noteData.content.page_ref, noteData.content.url]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputValue(value);

    // If there's an internal link set, input is for search only (don't touch url)
    if (!selectedInternalLink) {
      updateNoteData({ content: { ...noteData.content, url: value } });
    }

    // Offer page suggestions when typing (but not when it looks like a URL)
    if (value && !value.includes('://')) {
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
  };

  const handleSelectPage = (page: Page) => {
    updateNoteData({ content: { ...noteData.content, page_ref: { id: page.id, path: page.path }, text: page.name, url: undefined } });
    setSelectedInternalLink(page);
    setInputValue('');
    setSuggestions([]);
    setHighlightedIndex(-1);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const handleRemoveInternalLink = () => {
    updateNoteData({ content: { ...noteData.content, page_ref: undefined, text: '' } });
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
