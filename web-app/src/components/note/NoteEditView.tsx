// NoteEditView.tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Point2D } from '../../util/Point2D';
import { computed, makeObservable, observable } from 'mobx';
import { Rectangle } from '../../util/Rectangle';
import { Note, SerializedNote } from 'web-app/src/model/Note';
import { pamet } from '../../core/facade';
import { dumpToDict, loadFromDict } from 'fusion/libs/Entity';
import { currentTime, timestamp } from 'fusion/util';
import { getLogger } from 'fusion/logging';
import { PametTabIndex } from '../../core/constants';
import './NoteEditView.css';

let log = getLogger('EditComponent');

interface EditComponentProps {
  state: NoteEditViewState;
  onTitlebarPress: (event: React.MouseEvent) => void;
  onTitlebarRelease: (event: React.MouseEvent) => void;
  onCancel: () => void; // added to avoid a dependency to the pageViewState
  onSave: (note: Note) => void;
}

export class NoteEditViewState {
  targetNote: Note;
  center: Point2D;

  // Drag-by-title-bar related
  isBeingDragged: boolean = false;
  topLeftOnDragStart: Point2D = new Point2D(0, 0);
  dragStartClickPos: Point2D = new Point2D(0, 0);

  constructor(centerAt: Point2D, note: Note) {
    this.center = centerAt; // Pixel space
    this.targetNote = note;

    makeObservable(this, {
      center: observable,
      targetNote: observable,
      isBeingDragged: observable,
      creatingNote: computed,
    });
  }

  get creatingNote() {
    return pamet.note(this.targetNote.id) === undefined;
  }
}

const NoteEditView: React.FC<EditComponentProps> = observer((
  { state,
    onTitlebarPress,
    onTitlebarRelease,
    onCancel,
    onSave
  }: EditComponentProps) => {

  const wrapperRef = useRef<HTMLDivElement>(null);
  const [geometry, setGeometry] = useState<Rectangle>(
    new Rectangle(state.center.x, state.center.y, 400, 400)
  );
  const [noteData, setNoteData] = useState<SerializedNote>(
    dumpToDict(state.targetNote) as SerializedNote
  );

  // Update context on mount/unmount
  useEffect(() => {
    pamet.setContext('noteEditViewFocused', true);
    return () => pamet.setContext('noteEditViewFocused', false);
  }, []);

  const bakeNoteAndSave = useCallback(() => {
    /**
     * Returns a note object with the changes from the editing actions applied
     */
    let data = noteData;
    if (state.creatingNote) {
      data.created = timestamp(currentTime());
    }

    // Update the modified time if the content has changed
    // Do a deep comparison of the content objects
    let oldContent = state.targetNote.content;
    let newContent = data.content;
    if (JSON.stringify(oldContent) !== JSON.stringify(newContent)) {
      data.modified = timestamp(currentTime());
    }

    let note = loadFromDict(data) as Note;
    onSave(note);
  }, [noteData, onSave, state.creatingNote, state.targetNote]);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      onCancel();
    }
    if (event.code === 'KeyS' && event.ctrlKey) {
      event.preventDefault();
      bakeNoteAndSave();
    }

    // TODO: Add exceptions for global key bindings
    event.stopPropagation();
    log.info("Key pressed: " + event.key);
  };

  // Setup geometry update handling on resize
  useEffect(() => {
    const updateGeometryHandler = () => {
      let wrapper = wrapperRef.current;
      if (wrapper === null) {
        console.log("[resize handler] wrapperRef is null");
        return;
      }

      const rect = wrapper.getBoundingClientRect();
      setGeometry(new Rectangle(rect.left, rect.top, rect.width, rect.height));
    };

    // Use a resize observer to bind the updateGeometry function to resize events
    // of the superContainer
    let wrapper = wrapperRef.current;
    if (wrapper === null) {
      console.log("[resize watch effect] wrapperRef is null");
      return;
    }

    const resizeObserver = new ResizeObserver(updateGeometryHandler);
    resizeObserver.observe(wrapper);
    return () => resizeObserver.disconnect();
  }, [wrapperRef]);

  // Limit the position of the window to the screen
  let width = geometry.width;
  let height = geometry.height;

  let left = state.center.x - width / 2;
  let top = state.center.y - height / 2;

  console.log("Rendering NoteEditView", geometry);

  // Check if the window is outside the screen on the bottom and right
  if (left + width > window.innerWidth) {
    left = window.innerWidth - width;
  }
  if (top + height > window.innerHeight) {
    top = window.innerHeight - height;
  }

  // Check if the window is outside the screen on the top and left
  if (left < 0) {
    left = 0;
  }
  if (top < 0) {
    top = 0;
  }

  return (
    <div
      ref={wrapperRef}
      onKeyDown={handleKeyDown}
      className={`note-edit-view${state.isBeingDragged ? ' dragged' : ''}`}
      style={{ left, top }}
    >
      {/* Title bar */}
      <div className="title-bar">
        {/* move icon area */}
        <div
          onMouseDown={onTitlebarPress}
          onMouseUp={onTitlebarRelease}
          className="move-area"
        />
        {/* Close button */}
        <button className="close-button" onClick={onCancel}>×</button>
        <div className="title-text">
          {/* Set the text to 'Edit note' or 'Create note' */}
          {state.creatingNote ? 'Create note' : 'Edit note'}
        </div>
      </div>

      {/* Tool buttons row */}
      <div className="tool-buttons">
        <button className="tool-button">T</button>
        <button className="tool-button">🔗</button>
        <button className="tool-button">🖼️</button>
        <button className="tool-button">🗑️</button>
        <button className="tool-button">⋮</button>
      </div>

      {/* Main content */}
      <div className="main-content">
        {/* Text edit related */}
        <div className="text-container">
          <textarea
            placeholder="Note text"
            tabIndex={PametTabIndex.NoteEditViewWidget1}
            autoFocus
            defaultValue={state.targetNote.content.text}
            onChange={(e) => setNoteData({
              ...noteData,
              content: { ...noteData.content, text: e.target.value }
            })}
            onFocus={() => pamet.setContext('noteEditViewFocused', true)}
            onBlur={() => pamet.setContext('noteEditViewFocused', false)}
          />
        </div>
      </div>

      {/* Footer / actions */}
      <div className="footer">
        <button className="cancel-button" onClick={onCancel}>
          Cancel (Esc)
        </button>
        <button className="save-button" onClick={bakeNoteAndSave}>
          Save (Ctrl+S)
        </button>
      </div>
    </div>
  );
});

export default NoteEditView;
