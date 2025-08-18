import React, { useEffect } from 'react';
import { reaction } from 'mobx';
import { observer } from 'mobx-react-lite';
import { NoteViewState } from './NoteViewState';
import { PageController } from '../page/PageController';
import { getLogger } from 'fusion/logging';

let log = getLogger('NoteCacheManager.tsx');

interface NoteCacheManagerProps {
  noteViewState: NoteViewState;
  controller: PageController;
}

export const NoteCacheManager = observer(({ noteViewState, controller }: NoteCacheManagerProps) => {
  useEffect(() => {
    const disposer = reaction(() => {
        return {content: noteViewState._elementData.content, style: noteViewState._elementData.style}
    }, () => {
        log.info('Cache invalidation for', noteViewState._elementData.id)
         controller.renderer?.deleteNvsCache(noteViewState);
         controller.renderer?.renderCurrentPage();
    });


    return () => {
      disposer();
    };
  }, [noteViewState, controller]);

  // Per-note hidden image element to drive image loading lifecycle.
  // When the image loads, invalidate this note's cache and request a re-render.
  const imageId = noteViewState.note().content.image_id;
  const url = imageId ? noteViewState.pageViewState.mediaUrlsByItemId.get(imageId) : undefined;

  if (!url) {
    return null;
  }

  return (
    <img
      key={url}
      src={url}
      alt=""
      style={{ display: 'none' }}
      onLoad={() => {
        // Image became available -> refresh this note's cached bitmap
        controller.renderer?.deleteNvsCache(noteViewState);
        controller.renderer?.renderCurrentPage();
      }}
      onError={(event) => {
        log.error('Image load error', event, url);
      }}
    />
  );
});
