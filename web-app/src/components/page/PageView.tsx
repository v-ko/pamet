import { useState, useEffect, useRef, useMemo } from 'react';
import { observer } from 'mobx-react-lite';

import { PametTabIndex } from "@/core/constants";
import { Point2D } from 'fusion/primitives/Point2D';
import { PageMode, PageViewState } from "@/components/page/PageViewState";
import { getLogger } from 'fusion/logging';
import React from 'react';
import paper from 'paper';
import "@/components/page/PageView.css";

import { createNoteWithImageFromBlob } from '@/procedures/page';
import { MouseState } from '@/containers/app/WebAppState';
import { NoteVirtualComponent } from '../note/NoteVirtualComponent';
import { PageController } from '@/components/page/PageController';
import Menu, { MenuItem } from '@/components/menu/Menu';
import { ArrowVirtualComponent } from '@/components/arrow/ArrowVirtualComponent';


export let log = getLogger('Page.tsx')


export const PageView = observer(({ state, mouseState }: { state: PageViewState, mouseState: MouseState }) => {
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [isDropAllowed, setIsDropAllowed] = useState(false);


  const superContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const paperCanvasRef = useRef<HTMLCanvasElement>(null);

  // Controller instance tied to current PageViewState
  type CtxMenuState = { x: number, y: number, items: MenuItem[] } | null;
  const [contextMenu, setContextMenu] = useState<CtxMenuState>(null);

  const controller = useMemo(
    () => new PageController(state, mouseState, superContainerRef, setContextMenu),
    [state]
  );

  // Define effects

  // Focus the canvas when the component mounts
  useEffect(() => {
    if (!superContainerRef.current) {
      log.error('superContainerRef is null')
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) {
      log.error('canvasRef is null');
      return;
    }

    superContainerRef.current.focus()
    controller.bindEvents(canvas);

    return () => {
      controller.unbindEvents();
    }
  }, [controller]);

  // Connect the canvas element to paper.js exactly once per canvas mount
  useEffect(() => {
    const paperCanvas = paperCanvasRef.current;
    if (!paperCanvas) {
      log.error("[useEffect] paperCanvas is null");
      return;
    }

    // If paper is already set up for this canvas, skip re-initialization
    const currentView: any = (paper as any).view;
    if (currentView && currentView.element === paperCanvas) {
      return;
    }

    paper.setup(paperCanvas);
    paper.view.autoUpdate = false;

    // Cleanup on unmount to avoid accumulating listeners/state in paper.js
    return () => {
      try {
        (paper.project as any)?.clear?.();
        (paper.view as any)?.remove?.();
      } catch (e) {
        log.error("[useEffect] error cleaning up paper", e);
      }
    };
  }, [paperCanvasRef]);



  const handleDragEnter = (event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDraggingOver(true);

    // Check if the dragged items are files and if they are of a supported type
    const items = event.dataTransfer.items;
    if (items && items.length > 0) {
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === 'file' && items[i].type.startsWith('image/')) {
          setIsDropAllowed(true);
          return;
        }
      }
    }
    setIsDropAllowed(false);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDraggingOver(false);
    setIsDropAllowed(false);
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault(); // This is necessary to allow dropping
  };

  const handleDrop = async (event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDraggingOver(false);

    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      let position = state.viewport.unprojectPoint(new Point2D([event.clientX, event.clientY]));
      const imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));

      for (const imageFile of imageFiles) {
        try {
          position = await createNoteWithImageFromBlob(state.page().id, position, imageFile);
        } catch (error) {
          log.error('Error creating image note from dropped file:', error);
        }
      }
    }
    setIsDropAllowed(false);
  };


  // Rendering related

  // let rp = pamet.renderProfiler;
  // rp.setReactRender(state.renderId!);
  // rp.logTimeSinceMouseMove('React render', state.renderId!)

  const noteViewStates = Array.from(state.noteViewStatesById.values());
  const arrowViewStates = Array.from(state.arrowViewStatesById.values());

  return (
    <>
    <main
      className='page-view'  // index.css
      // Set cursor to cross if we're in arrow creation mode
      style={{ cursor: state.mode === PageMode.CreateArrow ? 'crosshair' : 'default' }}
      ref={superContainerRef}
      tabIndex={PametTabIndex.Page}  // To make the page focusable
      autoFocus={true}
      // onWheel={handleWheel} << this is added with useEffect in order to use passve: false
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Mock components to register mobx reactions for cache invalidation and arrow updates */}
      {noteViewStates.map(nvs =>
        <NoteVirtualComponent
          key={nvs._elementData.id}
          noteViewState={nvs}
          controller={controller}
        />)
      }
      {arrowViewStates.map(avs =>
        <ArrowVirtualComponent
          key={avs._elementData.id}
          arrowViewState={avs}
          controller={controller}
        />)
      }
      {isDraggingOver &&
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: isDropAllowed ? 'rgba(0, 255, 0, 0.1)' : 'rgba(255, 0, 0, 0.1)',
            zIndex: 10000,
            pointerEvents: 'none' // Make sure it doesn't interfere with drop events
          }}
        />
      }

      {/* Old pamet-canvas element rendering */}
      {/* <CanvasReactComponent state={state} /> */}

      {/* Canvas to do the direct rendering on */}
      <canvas
        id="render-canvas"
        style={{
          position: 'fixed',
          left: `0vw`,
          top: `0vh`,
          width: `100vw`,
          height: `100vh`,
          pointerEvents: 'none',
          zIndex: 1001,
        }}
        ref={canvasRef}
      />

      {/* Dummy canvas for paperjs */}
      <canvas
        id="paperjs-canvas"
        style={{
          position: 'fixed',
          left: `0vw`,
          top: `0vh`,
          width: `100vw`,
          height: `100vh`,
          pointerEvents: 'none',
          zIndex: 1000,
        }}
        ref={paperCanvasRef}
      />

    </main>
      {contextMenu && (
        <Menu
          items={contextMenu.items}
          x={contextMenu.x}
          y={contextMenu.y}
          variant='context'
          onDismiss={() => setContextMenu(null)}
        />
      )}
    </>
  );
});
