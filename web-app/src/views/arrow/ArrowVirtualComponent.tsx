import { useEffect } from 'react';
import { reaction } from 'mobx';
import { observer } from 'mobx-react-lite';
import { ArrowViewState } from './ArrowViewState';
import { PageController } from '../page/PageController';
import { getLogger } from 'fusion/logging';

let log = getLogger('ArrowVirtualComponent.tsx');

interface ArrowVirtualComponentProps {
  arrowViewState: ArrowViewState;
  controller: PageController;
}

/**
 * Lightweight, non-visual component that subscribes to ArrowViewState changes
 * and triggers a canvas re-render. Mirrors NoteVirtualComponent responsibilities
 * for arrows.
 */
export const ArrowVirtualComponent = observer(({ arrowViewState, controller }: ArrowVirtualComponentProps) => {
  useEffect(() => {
    // Track arrow properties that affect rendering
    const disposer = reaction(
      () => {
        const d = arrowViewState._elementData;
        // Access all relevant observable subfields to ensure mobx tracks changes
        return {
          tail: d.tail,
          head: d.head,
          mid_points: d.mid_points,
          style: d.style,
        };
      },
      () => {
        // No cache to invalidate for arrows; just re-render
        controller.renderer?.renderCurrentPage();
      }
    );

    return () => {
      disposer();
    };
  }, [arrowViewState, controller]);

  // No DOM; purely a reaction hook
  return null;
});
