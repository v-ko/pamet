import styled from 'styled-components';
import { Point2D } from '../../util/Point2D';
import { computed, makeObservable, observable } from 'mobx';
import { observer } from 'mobx-react-lite';
import { Rectangle } from '../../util/Rectangle';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Note, SerializedNote } from 'web-app/src/model/Note';
import { pamet } from '../../core/facade';
import { dumpToDict, loadFromDict } from 'fusion/libs/Entity';
import { currentTime, timestamp } from 'fusion/util';
import { getLogger } from 'fusion/logging';
import { PametTabIndex } from '../../core/constants';

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

  // Note content
  // _noteData: SerializedNote;

  constructor(centerAt: Point2D, note: Note) {
    this.center = centerAt; // Pixel space
    this.targetNote = note;
    // this._noteData = dumpToDict(note) as SerializedNote;

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

const ToolButton = styled.button`
    width: 1.8em;
    height: 1.8em;
    font-size: 1.3em;
    // center content
    display: flex;
    justify-content: center;
    align-items: center;
  background: #fff;
  border: 1px solid #000;
  border-radius: 2px;
  color: #000;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #000;
    color: #fff;
  }
`;

const NoteEditView: React.FC<EditComponentProps> = observer((
  { state,
    onTitlebarPress,
    onTitlebarRelease,
    onCancel,
    onSave
  }: EditComponentProps) => {

  const wrapperRef = useRef<HTMLDivElement>(null);
  const [geometry, setGeometry] = useState<Rectangle>(new Rectangle(state.center.x, state.center.y, 400, 400));
  const [noteData, setNoteData] = useState<SerializedNote>(dumpToDict(state.targetNote) as SerializedNote);

  // Update context on unmount
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
    log.info("Key pressed: " + event.key)
  }

  // Setup geometry update handling on resize
  useEffect(() => {
    const updateGeometryHandler = () => {
      let wrapper = wrapperRef.current;
      if (wrapper === null) {
        console.log("[resize handler] wrapperRef is null")
        return;
      }

      const rect = wrapper.getBoundingClientRect();
      setGeometry(new Rectangle(rect.left, rect.top, rect.width, rect.height));
    };

    // Use a resize observer to bind the updateGeometry function to resize events
    // of the superContainer
    let wrapper = wrapperRef.current;
    if (wrapper === null) {
      console.log("[resize watch effect] wrapperRef is null")
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

  console.log("Rendering NoteEditView", geometry)

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
      style={{
        left: left,
        top: top,
        // background: `rgba(255, 255, 255, ${state.isBeingDragged ? 0.6 : 1})`,
        pointerEvents: state.isBeingDragged ? 'none' : 'auto',

        position: 'absolute',
        width: '400px',
        height: '400px',
        background: '#fff',
        color: '#000',
        resize: 'both',
        overflow: 'auto',
        minHeight: '300px',
        minWidth: '300px',
        maxWidth: '95%',

        border: '1px solid #000',
        borderRadius: '2px',
        display: 'grid',
        gridTemplateColumns: '100%',
        gridTemplateRows: '36px 46px auto 50px',
        zIndex: 1003,
      }}
    >
      {/* Title bar */}
      <div
        style={{
          position: 'relative',
          background: '#000',
          color: '#fff',
          display: 'flex',
          alignItems: 'center',
          borderBottom: '1px solid #000',
        }}
      >
        {/* move icon area */}
        <div
          onMouseDown={onTitlebarPress}
          onMouseUp={onTitlebarRelease}
          style={{
            cursor: 'move',
            flexGrow: 1,
            // minimal “grab area” for moving the dialog
          }}
        />
        {/* Close button */}
        <button
          onClick={onCancel}
          style={{
            background: 'transparent',
            border: 'none',
            width: '36px',
            height: '36px',
            color: '#fff',
            fontSize: '18px',
            cursor: 'pointer',
            transition: '0.2s',
          }}
          onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#444')}
          onMouseOut={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          ×
        </button>
        <div // Display the title separately on top (there's probably a nicer way)
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            top: 0,
            left: 0,
            textAlign: 'center',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          {/* Set the text to 'Edit note' or 'Create note' */}
          {state.creatingNote ? 'Create note' : 'Edit note'}
        </div>
      </div>

      {/* Tool buttons row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '5px',
          gap: '2px',
        }}>
        <ToolButton>T</ToolButton>
        <ToolButton>🔗</ToolButton>
        <ToolButton>🖼️</ToolButton>
        <ToolButton>🗑️</ToolButton>
        <ToolButton>⋮</ToolButton>
      </div>

      {/* Main content */}
      <div
        className="main-content"
        style={{
          padding: '8px',
          overflow: 'none',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '10px',
        }}
      >
        {/* Main content */}
        {/* Text edit related */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            width: '100%',
            height: '100%',
            overflow: 'none',
          }}
        >
          <label
            style={{
              fontSize: '0.9em',
              fontWeight: 'bold',
              marginBottom: '5px',
            }}
          >
            Text:
          </label>
          <textarea
            // placeholder="Enter text here"
            tabIndex={PametTabIndex.NoteEditViewWidget1}
            autoFocus={true}
            defaultValue={state.targetNote.content.text}
            onChange={(e) => {
              setNoteData({
                ...noteData,
                content: {
                  ...noteData.content,
                  text: e.target.value,
                },
              });
            }}
            style={{
              flexGrow: 1,
              resize: 'none',
              border: '1px solid #000',
              borderRadius: '2px',
              padding: '8px',
              fontSize: '14px',
              color: '#000',
            }}
            onFocus={() => pamet.setContext('noteEditViewFocused', true)}
            onBlur={() => pamet.setContext('noteEditViewFocused', false)}
          />
        </div>
      </div>

      {/* Footer / actions */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '10px',
          padding: '8px',
          borderTop: '1px solid #000',
        }}
      >
        <button
          onClick={onCancel}
          style={{
            padding: '6px 12px',
            border: '1px solid #000',
            borderRadius: '2px',
            background: '#fff',
            color: '#000',
            cursor: 'pointer',
          }}
        >
          Cancel (Esc)</button>
        <button
          onClick={bakeNoteAndSave}
          style={{
            padding: '6px 12px',
            border: '1px solid #000',
            borderRadius: '2px',
            background: '#000',
            color: '#fff',
            cursor: 'pointer',
          }}
        >
          Save (Ctrl+S)</button>
      </div>
    </div>
  );
});

export default NoteEditView;
