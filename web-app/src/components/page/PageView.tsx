import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { observer } from 'mobx-react-lite';

import { DEFAULT_EYE_HEIGHT, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE, PametTabIndex } from "@/core/constants";
import { Point2D } from 'fusion/primitives/Point2D';
import { pageActions } from "@/actions/page";
import { PageMode, PageViewState } from "@/components/page/PageViewState";
import { Viewport } from "@/components/page/Viewport";
import { getLogger } from 'fusion/logging';
import React from 'react';
import paper from 'paper';
import "@/components/page/PageView.css";
import { pamet } from "@/core/facade";

import { appActions } from "@/actions/app";
import { createNoteWithImageFromBlob } from '@/procedures/page';
import { MouseState } from '@/containers/app/WebAppState';
import { NoteCacheManager } from '../note/NoteCacheManager';
import { PageController } from '@/components/page/PageController';


export let log = getLogger('Page.tsx')


export const PageView = observer(({ state, mouseState }: { state: PageViewState, mouseState: MouseState }) => {
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [isDropAllowed, setIsDropAllowed] = useState(false);

  const [pinchStartDistance, setPinchStartDistance] = useState<number>(0);
  const [pinchInProgress, setPinchInProgress] = useState<boolean>(false);
  const [pinchStartViewportHeight, setPinchStartViewportHeight] = useState<number>(DEFAULT_EYE_HEIGHT);
  const [initialPinchCenter, setInitialPinchCenter] = useState<Point2D>(new Point2D([0, 0]));

  const superContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const paperCanvasRef = useRef<HTMLCanvasElement>(null);

  // Controller instance tied to current PageViewState
  const controller = useMemo(
    () => new PageController(state, mouseState, superContainerRef),
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

  // Geometry updates are handled by PageController.setupResizeObserver

  // ResizeObserver removed from React view (handled in controller)


  // Touch event handlers
  const handleTouchStart = useCallback((event: React.TouchEvent) => {
    // Only for single finger touch
    if (event.touches.length === 1) {
      let touchPos = new Point2D([event.touches[0].clientX, event.touches[0].clientY]);
      appActions.updateMouseState(pamet.appViewState, {
        positionOnPress: touchPos
      });
      pageActions.startDragSelection(state, touchPos)
    } else if (event.touches.length === 2) {
      // The pinch gesture navigation is a combination of dragging and zooming
      // so we enter DragNavigation mode and also update the viewport height

      console.log('pinch start')
      let touch1 = new Point2D([event.touches[0].clientX, event.touches[0].clientY]);
      let touch2 = new Point2D([event.touches[1].clientX, event.touches[1].clientY]);
      // touch1 = mapClientPointToSuperContainer(touch1); // NOT TESTED
      // touch2 = mapClientPointToSuperContainer(touch2);
      let distance = touch1.distanceTo(touch2);
      let initPinchCenter = touch1.add(touch2).divide(2)
      setPinchStartDistance(distance);
      setPinchStartViewportHeight(state.viewportHeight);
      setPinchInProgress(true);
      setInitialPinchCenter(initPinchCenter);
      console.log('Initial pinch center', initPinchCenter)

      pageActions.startDragNavigation(state)
    }
  }, [state, mouseState]);

  const handeTouchMove = useCallback((event: React.TouchEvent) => {
    if (event.touches.length === 1) {
      let newTouchPos = new Point2D([event.touches[0].clientX, event.touches[0].clientY]);
      pageActions.updateDragSelection(state, newTouchPos);

    } else if (event.touches.length === 2) {
      let touch1 = new Point2D([event.touches[0].clientX, event.touches[0].clientY]);
      let touch2 = new Point2D([event.touches[1].clientX, event.touches[1].clientY]);

      if (pinchInProgress) {
        // Calculate the new height
        let distance = touch1.distanceTo(touch2);
        let newPinchCenter = touch1.add(touch2).divide(2);
        let new_height = pinchStartViewportHeight * (pinchStartDistance / distance);
        new_height = Math.max(
          MIN_HEIGHT_SCALE,
          Math.min(new_height, MAX_HEIGHT_SCALE))

        // Move the center according to the pinch center
        let delta = initialPinchCenter.subtract(newPinchCenter);
        let delta_unproj = delta.divide(state.viewport.heightScaleFactor());
        let new_center = state.viewportCenterOnModeStart.add(delta_unproj);

        // Apply the correction to make the zoom focused on the pinch center
        // M - mouse pos (unprojected), C - viewport center. s - scale
        // M' = M * s, C' = C * s : M and C after the scale
        // V = (M - C) - (M' - C'): the vector of change for M
        // correction = - ( V ) = (M - C) - (M' - C') = (M - C) * (1 - s)
        let old_viewport = new Viewport(state.viewportGeometry, pinchStartViewportHeight);
        old_viewport.moveRealCenterTo(state.viewportCenterOnModeStart)
        let unprInitPinchCenter = old_viewport.unprojectPoint(initialPinchCenter);
        let focusDelta = unprInitPinchCenter.subtract(state.viewportCenterOnModeStart);
        let correction = focusDelta.multiply(
          1 - new_height / pinchStartViewportHeight);
        new_center = new_center.add(correction)

        pageActions.updateViewport(state, new_center, new_height);

      }
    }
  }, [state, pinchStartViewportHeight, pinchStartDistance,
    pinchInProgress, initialPinchCenter]);

  const handleTouchEnd = useCallback((event: React.TouchEvent) => {
    // setMouseDown(false);
    if (state.mode === PageMode.DragNavigation) {
      pageActions.endDragNavigation(state);
    }
    setPinchInProgress(false);
  }, [state]);



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

  return (
    <main
      className='page-view'  // index.css
      // Set cursor to cross if we're in arrow creation mode
      style={{ cursor: state.mode === PageMode.CreateArrow ? 'crosshair' : 'default' }}
      // style={{ width: '100%', height: '100%', overflow: 'hidden', touchAction: 'none' }}
      ref={superContainerRef}
      tabIndex={PametTabIndex.Page}  // To make the page focusable
      autoFocus={true}
      // onKeyDown={handleKeyDown}
      // we watch for mouse events here, to get them in pixel space coords
      // onWheel={handleWheel} << this is added with useEffect in order to use passve: false
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onTouchMove={handeTouchMove}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Mock components to register mobx reactions for cache invalidation with */}
      {noteViewStates.map(nvs =>
        <NoteCacheManager
          key={nvs._elementData.id}
          noteViewState={nvs}
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
  );
});
