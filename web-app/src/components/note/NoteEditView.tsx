// NoteEditView.tsx
import React, { useEffect, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Rectangle } from '../../util/Rectangle';
import { Note, SerializedNote } from 'web-app/src/model/Note';
import { TextNote } from 'web-app/src/model/TextNote';
import { ImageNote } from 'web-app/src/model/ImageNote';
import { CardNote } from 'web-app/src/model/CardNote';
import { pamet } from '../../core/facade';
import { dumpToDict, loadFromDict } from 'fusion/libs/Entity';
import { currentTime, timestamp } from 'fusion/base-util';
import { getLogger } from 'fusion/logging';
import { PametTabIndex } from '../../core/constants';
import './NoteEditView.css';
import { ImageEditPropsWidget } from './edit-window/ImageEditPropsWidget';
import { MediaItem, MediaItemData } from 'fusion/libs/MediaItem';
import { NoteEditViewState } from './NoteEditViewState';

let log = getLogger('EditComponent');

interface EditComponentProps {
    state: NoteEditViewState;
    onTitlebarPress: (event: React.MouseEvent) => void;
    onTitlebarRelease: (event: React.MouseEvent) => void;
    onCancel: () => void; // added to avoid a dependency to the pageViewState
    onSave: (note: Note, addedMediaItem: MediaItem | null, removedMediaItem: MediaItem | null) => void;
}

const NoteEditView: React.FC<EditComponentProps> = observer((
  { state,
    onTitlebarPress,
    onTitlebarRelease,
    onCancel,
    onSave
  }: EditComponentProps) => {

  const wrapperRef = useRef<HTMLDivElement>(null);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const committed = useRef(false);
  const [geometry, setGeometry] = useState<Rectangle>(
    new Rectangle(state.center.x, state.center.y, 400, 400)
  );
  const noteData = useRef(
    dumpToDict(state.targetNote) as SerializedNote
  );
  const [, setForceUpdate] = useState(0);

  const updateNoteData = (newData: Partial<SerializedNote>) => {
    noteData.current = { ...noteData.current, ...newData };
    setForceUpdate(x => x + 1);
  };

  const [uncommitedImage, setUncommitedImage] = useState<MediaItemData | null>(null);
  const [originalImageForTrashing, setOriginalImageForTrashing] = useState<MediaItemData | null>(null);

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
    const currentNote = loadFromDict(noteData.current) as Note;

    if (textButtonToggled && imageButtonToggled) {
      if (currentNote instanceof CardNote) return;
      newNote = new CardNote(noteData.current);
    } else if (textButtonToggled) {
      if (currentNote instanceof TextNote && !(currentNote instanceof CardNote)) return;
      newNote = new TextNote(noteData.current);
    } else if (imageButtonToggled) {
      if (currentNote instanceof ImageNote && !(currentNote instanceof CardNote)) return;
      newNote = new ImageNote(noteData.current);
    } else { // Should not happen with proper logic
      setTextButtonToggled(true);
      return;
    }
    updateNoteData(dumpToDict(newNote) as SerializedNote);
  }, [textButtonToggled, imageButtonToggled]);

  useEffect(() => {
    // Focus the text area on mount if it's visible
    if (textButtonToggled) {
        textAreaRef.current?.focus();
    }
  }, [textButtonToggled]);

  // Effect for cleaning up uncommitted media on component unmount
  useEffect(() => {
    return () => {
      // If the component unmounts and there's an uncommitted item, delete it
      if (uncommitedImage && !committed.current) {
        const projectId = pamet.appViewState.currentProjectId;
        if (projectId) {
          log.info('Cleaning up uncommitted media item on unmount:', uncommitedImage);
          pamet.storageService.removeMedia(projectId, uncommitedImage.id, uncommitedImage.contentHash)
            .catch(err => log.error('Failed to clean up media item', err));
        }
      }
    };
  }, []);

  const removeNoteImage = async () => {
    const currentImageId = noteData.current.content.image_id;
    if (!currentImageId) {
        throw new Error("removeOriginalImage called when there is no image.");
    }

    const projectid = pamet.appViewState.currentProjectId;
    if (!projectid) {
      throw new Error('No project loaded');
    }

    // If removing the original image
    if (!originalImageForTrashing) {
      const originalMediaItem = pamet.mediaItem(currentImageId);
      if (!originalMediaItem) {
        throw new Error("Original media item not found for the image.");
      }
      setOriginalImageForTrashing(originalMediaItem.data());
    } else { // If there is an original image for trashing, then the current image has been added in this editing session
      // If removing an image added in the editing session - delete it from the store permanently
      // Get the set media item from the state
      if (!uncommitedImage) {
        throw new Error("No uncommitted image to remove.");
      } else if (uncommitedImage.id !== currentImageId) {
        throw new Error("Uncommitted image ID does not match the current image ID.");
      }
      await pamet.deleteMediaFromStore(new MediaItem(uncommitedImage))
    }

    // Clear the image from the note data state
    updateNoteData({ content: { ...noteData.current.content, image_id: undefined } });
  };

  const setNoteImage = async (blob: Blob, path: string) => {
    const projectId = pamet.appViewState.currentProjectId;
    if (!projectId) {
      throw new Error('No project loaded');
    }

    if (noteData.current.content.image_id) {
        throw new Error("setNoteImage called when there is already an image.");
    }

    const newMediaItem = await pamet.storageService.addMedia(projectId, blob, path, noteData.current.id);
    setUncommitedImage(newMediaItem);
    updateNoteData({ content: { ...noteData.current.content, image_id: newMediaItem.id } });
  };

  const bakeNoteAndSave = () => {
    // Deep copy to avoid mutating state directly
    let data = noteData.current

    // Determine the definitive note type based on content
    const hasText = data.content.text && data.content.text.trim().length > 0;
    const hasImage = !!data.content.image_id;
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
        finalContent.image_id = data.content.image_id;
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
    committed.current = true;
    const addedMediaItem = uncommitedImage ? new MediaItem(uncommitedImage) : null;
    const removedMediaItem = originalImageForTrashing ? new MediaItem(originalImageForTrashing) : null;
    onSave(note, addedMediaItem, removedMediaItem);

    // On successful save, the media items are committed. Clear the state.
    setUncommitedImage(null);
    setOriginalImageForTrashing(null);

  };

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
        <button
          className="close-button"
          onClick={onCancel}
        >×</button>
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
          tabIndex={PametTabIndex.NoteEditViewWidget1 + 3}
        >T</button>
        <button className="tool-button" tabIndex={PametTabIndex.NoteEditViewWidget1 + 4}>🔗</button>
        <button
          className={`tool-button ${imageButtonToggled ? 'toggled' : ''}`}
          onClick={() => setImageButtonToggled(!imageButtonToggled)}
          tabIndex={PametTabIndex.NoteEditViewWidget1 + 5}
        >🖼️</button>
        <button className="tool-button" tabIndex={PametTabIndex.NoteEditViewWidget1 + 6}>⋮</button>
      </div>

      {/* Main content */}
      <div className="main-content">
        {imageButtonToggled && <ImageEditPropsWidget
          noteData={noteData.current}
          uncommitedMediaItem={uncommitedImage}
          setNoteImage={setNoteImage}
          removeNoteImage={removeNoteImage}
        />}
        {textButtonToggled && <div className="text-container">
          <textarea
            ref={textAreaRef}
            placeholder="Note text"
            tabIndex={PametTabIndex.NoteEditViewWidget1}
            defaultValue={state.targetNote.content.text}
            onChange={(e) => {
                updateNoteData({ content: { ...noteData.current.content, text: e.target.value } });
            }}
          />
        </div>}
      </div>

      {/* Footer / actions */}
      <div className="footer">
        <button
          className="cancel-button"
          onClick={onCancel}
          tabIndex={PametTabIndex.NoteEditViewWidget1 + 2}
        >
          Cancel (Esc)
        </button>
        <button
          className="save-button"
          onClick={bakeNoteAndSave}
          tabIndex={PametTabIndex.NoteEditViewWidget1 + 1}
        >
          Save (Ctrl+S)
        </button>
      </div>
    </div>
  );
});

export default NoteEditView;
