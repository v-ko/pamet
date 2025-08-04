// NoteEditView.tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Point2D } from '../../util/Point2D';
import { computed, makeObservable, observable } from 'mobx';
import { Rectangle } from '../../util/Rectangle';
import { Note, SerializedNote } from 'web-app/src/model/Note';
import { TextNote } from 'web-app/src/model/TextNote';
import { ImageNote } from 'web-app/src/model/ImageNote';
import { CardNote } from 'web-app/src/model/CardNote';
import { pamet } from '../../core/facade';
import { dumpToDict, loadFromDict } from 'fusion/libs/Entity';
import { currentTime, timestamp } from 'fusion/util';
import { getLogger } from 'fusion/logging';
import { PametTabIndex } from '../../core/constants';
import './NoteEditView.css';
import { ImageEditPropsWidget } from './edit-window/ImageEditPropsWidget';
import { MediaItemData } from 'web-app/src/model/MediaItem';

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
  const [uncommittedImage, setUncommittedImage] = useState<MediaItemData | null>(null);

  const [textButtonToggled, setTextButtonToggled] = useState(() => {
    const note = state.targetNote;
    return note instanceof TextNote || note instanceof CardNote;
  });
  const [imageButtonToggled, setImageButtonToggled] = useState(() => {
      const note = state.targetNote;
      return note instanceof ImageNote || note instanceof CardNote;
  });
  const [linkButtonToggled, setLinkButtonToggled] = useState(false);

  // Handle Note type changes
  useEffect(() => {
    let newNote: Note;
    const currentNote = loadFromDict(noteData) as Note;

    if (textButtonToggled && imageButtonToggled) {
      if (currentNote instanceof CardNote) return;
      newNote = new CardNote(noteData);
    } else if (textButtonToggled) {
      if (currentNote instanceof TextNote && !(currentNote instanceof CardNote)) return;
      newNote = new TextNote(noteData);
    } else if (imageButtonToggled) {
      if (currentNote instanceof ImageNote && !(currentNote instanceof CardNote)) return;
      newNote = new ImageNote(noteData);
    } else { // Should not happen with proper logic
      setTextButtonToggled(true);
      return;
    }
    setNoteData(dumpToDict(newNote) as SerializedNote);
  }, [textButtonToggled, imageButtonToggled, noteData]);

  // Update context on mount and setup cleanup for uncommitted media
  useEffect(() => {
    pamet.setContext('noteEditViewFocused', true);

    return () => {
      pamet.setContext('noteEditViewFocused', false);
      // If the component unmounts and there's an uncommitted item, delete it
      if (uncommittedImage) {
        const projectId = pamet.appViewState.currentProjectId;
        if (projectId) {
          log.info('Cleaning up uncommitted media item on unmount:', uncommittedImage);
          pamet.storageService.removeMedia(projectId, uncommittedImage.id, uncommittedImage.contentHash)
            .catch(err => log.error('Failed to clean up media item', err));
        }
      }
    };
  }, [uncommittedImage]);

  const setNoteImage = async (blob: Blob, path: string) => {
    const projectId = pamet.appViewState.currentProjectId;
    if (!projectId) {
      throw new Error('No project loaded');
    }

    // If there's an existing uncommitted item, remove it.
    if (uncommittedImage) {
      await pamet.storageService.removeMedia(projectId, uncommittedImage.id, uncommittedImage.contentHash);
    }

    const newMediaItem = await pamet.storageService.addMedia(projectId, blob, path);
    setUncommittedImage(newMediaItem);
    setNoteData({
      ...noteData,
      content: { ...noteData.content, image: newMediaItem }
    });
  };

  const bakeNoteAndSave = useCallback(() => {
    // Deep copy to avoid mutating state directly
    let data = JSON.parse(JSON.stringify(noteData));

    // Determine the definitive note type based on content
    const hasText = data.content.text && data.content.text.trim().length > 0;
    const hasImage = !!data.content.image;
    let FinalNoteClass: typeof Note;

    if (hasText && hasImage) {
        FinalNoteClass = CardNote;
    } else if (hasImage) {
        FinalNoteClass = ImageNote;
    } else { // Default to TextNote if only text is present, or if both are empty
        FinalNoteClass = TextNote;
    }

    // Apply the class change to the data object
    data.type_name = FinalNoteClass.name;

    // Clean the content object based on the definitive type
    const finalContent: any = {};
    if (FinalNoteClass === TextNote || FinalNoteClass === CardNote) {
        finalContent.text = data.content.text;
    }
    if (FinalNoteClass === ImageNote || FinalNoteClass === CardNote) {
        finalContent.image = data.content.image;
    }
    data.content = finalContent;

    // Apply timestamp logic
    if (state.creatingNote) {
      data.created = timestamp(currentTime());
    }
    let oldContent = state.targetNote.content;
    if (JSON.stringify(oldContent) !== JSON.stringify(data.content)) {
      data.modified = timestamp(currentTime());
    }

    let note = loadFromDict(data) as Note;
    onSave(note);

    // On successful save, the media item is committed. Clear the state.
    setUncommittedImage(null);

  }, [noteData, onSave, state.creatingNote, state.targetNote, setUncommittedImage]);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      onCancel();
    }
    if (event.code === 'KeyS' && event.ctrlKey) {
      event.preventDefault();
      bakeNoteAndSave();
    }
    event.stopPropagation();
    log.info("Key pressed: " + event.key);
  };

  // Setup geometry update handling on resize
  useEffect(() => {
    const updateGeometryHandler = () => {
      let wrapper = wrapperRef.current;
      if (wrapper === null) {
        log.warning("[resize handler] wrapperRef is null");
        return;
      }
      const rect = wrapper.getBoundingClientRect();
      setGeometry(new Rectangle(rect.left, rect.top, rect.width, rect.height));
    };

    // Use a resize observer to bind the updateGeometry function to resize events
    // of the superContainer
    let wrapper = wrapperRef.current;
    if (wrapper === null) {
      log.warning("[resize watch effect] wrapperRef is null");
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
          {state.creatingNote ? 'Create note' : 'Edit note'}
        </div>
      </div>

      {/* Tool buttons row */}
      <div className="tool-buttons">
        <button
          className={`tool-button ${textButtonToggled ? 'toggled' : ''}`}
          onClick={() => {
            if (!imageButtonToggled) return;
            setTextButtonToggled(!textButtonToggled)
          }}
        >T</button>
        <button className="tool-button">🔗</button>
        <button
          className={`tool-button ${imageButtonToggled ? 'toggled' : ''}`}
          onClick={() => setImageButtonToggled(!imageButtonToggled)}
        >🖼️</button>
        <button className="tool-button">🗑️</button>
        <button className="tool-button">⋮</button>
      </div>

      {/* Main content */}
      <div className="main-content">
        {imageButtonToggled && <ImageEditPropsWidget
          noteData={noteData}
          setNoteImage={setNoteImage}
        />}
        {textButtonToggled && <div className="text-container">
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
        </div>}
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
