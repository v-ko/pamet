import { useEffect } from 'react';
import { reaction } from 'mobx';
import { observer } from 'mobx-react-lite';
import { NoteViewState } from './NoteViewState';
import { PageController } from '../page/PageView';
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
    });


    return () => {
      disposer();
    };
  }, [noteViewState, controller]);

  return null; // This component does not render anything
});
