import { useState, useEffect, useCallback, useRef } from 'react';
import styled from 'styled-components';
import { observer } from 'mobx-react-lite';

import { DEFAULT_EYE_HEIGHT, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { pageActions } from '../../actions/page';
import { TourComponent } from '../Tour';
import { PageMode, PageViewState } from './PageViewState';
import { Viewport } from './Viewport';
import { getLogger } from '../../fusion/logging';
import { reaction } from 'mobx';
import React from 'react';
import paper from 'paper';
import { CanvasPageRenderer } from './DirectRenderer';
import { ElementViewState } from './ElementViewState';
import { pamet } from '../../facade';
import { NavigationDevice, NavigationDeviceAutoSwitcher } from './NavigationDeviceAutoSwitcher';
import { CanvasReactComponent } from './ReactRenderingComponent';


let log = getLogger('Page.tsx')

// const DEFAULT_VIEWPORT_TRANSITION_T = 0.05;
// type Status = 'loading' | 'error' | 'loaded';

export const PageViewStyled = styled.div`
width: 100%;
height: 100%;
overflow: hidden;
display: flex;
@media (max-width: 768px) {
  flex-direction: column;
  flex-flow: column-reverse;
}
`;

export const PageOverlay = styled.div`
content-visibility: auto;
flex-grow: 1;
flex-shrink: 1;
overflow: hidden;
touch-action: none;
min-width: 30px;
`

export const PageView = observer(({ state }: { state: PageViewState }) => {
  /**  */
  // trace(true)

  const [mousePosOnPress, setMousePosOnPress] = useState<Point2D>(new Point2D(0, 0));

  const [leftMouseIsPressed, setLeftMouseIsPressed] = useState<boolean>(false);
  const [mousePosOnLeftPress, setMousePosOnLeftPress] = useState<Point2D>(new Point2D(0, 0));

  const [rightMouseIsPressed, setRightMouseIsPressed] = useState<boolean>(false);

  const [pinchStartDistance, setPinchStartDistance] = useState<number>(0);
  const [pinchInProgress, setPinchInProgress] = useState<boolean>(false);
  const [pinchStartViewportHeight, setPinchStartViewportHeight] = useState<number>(DEFAULT_EYE_HEIGHT);
  const [initialPinchCenter, setInitialPinchCenter] = useState<Point2D>(new Point2D(0, 0));

  const superContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const paperCanvasRef = useRef<HTMLCanvasElement>(null);

  const [cacheService, setCacheService] = useState(new CanvasPageRenderer());
  const [navDeviceAutoSwitcher, setNavDeviceAutoSwitcher] = useState(new NavigationDeviceAutoSwitcher());

  const canvasCtx = useCallback(() => {
    const canvas = canvasRef.current;
    if (canvas === null) {
      console.log("[useEffect] canvas is null")
      return null;
    }

    const ctx = canvas.getContext('2d');

    if (ctx === null) {
      console.log("[useEffect] canvas context is null")
      return null;
    }
    return ctx;
  }
    , [canvasRef]);

  // Initial setup - init paperjs
  useEffect(() => {
    console.log("[useEffect] INTO INIT")
    const paperCanvas = paperCanvasRef.current;
    if (paperCanvas === null) {
      console.log("[useEffect] canvas is null")
      return;
    }
    paper.setup(paperCanvas);
    paper.view.autoUpdate = false;


    // // Initial render
    // setTimeout(() => {
    //   console.log("[useEffect.setTimeout] INTO TIMEOUT")
    //   let ctx = canvasCtx()
    //   if (ctx === null) {
    //     console.log("[useEffect] canvas context is null")
    //     return;
    //   }
    //   cacheService.renderPage(state, ctx);
    // }, 1);

  }, [state, canvasCtx, paperCanvasRef, cacheService]);

  const updateGeometryHandler = useCallback(() => {
    console.log("[updateGeometry] called")
    let container = superContainerRef.current;
    if (container === null) {
      console.log("[updateGeometry] superContainerRef is null")
      return;
    }
    let boundingRect = container.getBoundingClientRect();

    //Adjust canvas size
    const canvas = canvasRef.current;
    if (canvas === null) {
      console.log("[useEffect] canvas is null")
      return;
    }

    const ctx = canvas.getContext('2d');

    if (ctx === null) {
      console.log("[useEffect] canvas context is null")
      return;
    }

    // Adjust for device pixel ratio, otherwise small objects will be blurry
    let dpr = window.devicePixelRatio || 1;

    // Set the canvas size in real coordinates
    canvas.width = boundingRect.width * dpr;
    canvas.height = boundingRect.height * dpr;

    // Update viewport geometry

    pageActions.updateGeometry(
      state,
      [boundingRect.left, boundingRect.top, boundingRect.width, boundingRect.height]);
    console.log("Resized to ", boundingRect.left, boundingRect.top, boundingRect.width, boundingRect.height);

  }, [state, superContainerRef]);


  // Setup geometry update handling on resize
  useEffect(() => {

    // Use a resize observer to bind the updateGeometry function to resize events
    // of the superContainer
    let container = superContainerRef.current;
    if (container === null) {
      console.log("[updateGeometry] superContainerRef is null")
      return;
    }

    const resizeObserver = new ResizeObserver(updateGeometryHandler);
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [updateGeometryHandler, superContainerRef]);


  // Call the direct renderer on the relevant state changes
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas === null) {
      console.log("[useEffect] canvas is null")
      return;
    }

    const ctx = canvas.getContext('2d');

    if (ctx === null) {
      console.log("[useEffect] canvas context is null")
      return;
    }

    const renderDisposer = reaction(() => {
      // Trigger on all of these
      return {
        viewport: state.viewport,
        selectedElements: state.selectedElements.values(),
        dragSelectionRectData: state.dragSelectionRectData,
        mode: state.mode,
        dragSelectedElements: state.dragSelectedElements,
        arrowViewStatesByOwnId: state.arrowViewStatesByOwnId,
        noteViewStatesByOwnId: state.noteViewStatesByOwnId,
      }
    },
      () => {
        cacheService.renderPage(state, ctx);
      });

    return () => {
      renderDisposer();
      // imgRefUpdateDisposer();
    }
  }, [state, cacheService, canvasRef]);

  // // Should be a command
  // const copySelectedToClipboard = useCallback(() => {
  //   let notesData = Array.from(state.noteViewStatesByOwnId.values()).map((noteVS) => noteVS.note.data());
  //   // this is broken, selected children has noteVS objects
  //   // let selected_notes = notesData.filter((note) => state.selectedChildren.has(note.id.toString()));
  //   let text = selected_notes.map((note) => note.content.text).join('\n\n');
  //   navigator.clipboard.writeText(text);
  // }, [state.noteViewStatesByOwnId, state.selectedChildren]);


  // Mouse event handlers
  const handleMouseDown = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    // let mousePos = mapClientPointToSuperContainer(new Point2D(event.clientX, event.clientY));
    let mousePos = new Point2D(event.clientX, event.clientY);

    setMousePosOnPress(mousePos);
    if (event.button === 2) {
      setRightMouseIsPressed(true);
    }
    if (event.button === 0) {
      setLeftMouseIsPressed(true);
      setMousePosOnLeftPress(mousePos);
    }
    log.info('[handleMouseDown] Mouse down: ', mousePos.x, mousePos.y)

  }, []);

  const handleMouseMove = useCallback((event) => {
    let mousePos = new Point2D(event.clientX, event.clientY);
    let pressPos = mousePosOnPress;
    let delta = pressPos.subtract(mousePos);

    // if (event.buttons === 1) {
    //   console.log('mouse move, left button', PageMode[state.mode])
    // }

    if (state.mode === PageMode.None) {
      if (rightMouseIsPressed) {
        pageActions.startDragNavigation(state, pressPos)
        pageActions.dragNavigationMove(state, delta)
        navDeviceAutoSwitcher.registerRightMouseDrag(new Point2D(event.movementX, event.movementY));
      } else if (leftMouseIsPressed) {

        pageActions.clearSelection(state);
        pageActions.startDragSelection(state, pressPos);
        pageActions.updateDragSelection(state, mousePos);
      }
    } else if (state.mode === PageMode.DragNavigation) {
      pageActions.dragNavigationMove(state, delta);
    } else if (state.mode === PageMode.DragSelection) {
      pageActions.updateDragSelection(state, mousePos);
    }
    // }
  }, [leftMouseIsPressed, mousePosOnPress, navDeviceAutoSwitcher, rightMouseIsPressed, state]);

  const handleMouseUp = useCallback((event) => {
    let mousePos = new Point2D(event.clientX, event.clientY);

    let pressPos = mousePosOnPress;
    let realPos = state.viewport.unprojectPoint(mousePos);
    let ctrlPressed = event.ctrlKey;
    let shiftPressed = event.shiftKey;

    let elementUnderMouse: ElementViewState | null = state.arrowViewStateAt(realPos)
    let noteVS_underMouse = state.noteViewStateAt(realPos)
    if (noteVS_underMouse !== null) {
      elementUnderMouse = noteVS_underMouse;
    }

    console.log('Mouse up', PageMode[state.mode], 'button', event.button, elementUnderMouse)

    event.preventDefault();
    if (event.button === 0) { // Left press
      setLeftMouseIsPressed(false);
      if (state.mode === PageMode.None) {
        if (ctrlPressed && !shiftPressed) { // Toggle selection
          if (elementUnderMouse !== null) {
            let nvs_selected = state.selectedElements.has(elementUnderMouse);
            pageActions.updateSelection(state, new Map([[elementUnderMouse, !nvs_selected]]));
          }
        } else if (shiftPressed || (ctrlPressed && shiftPressed)) { // Add to selection
          if (elementUnderMouse !== null) {
            let nvs_selected = state.selectedElements.has(elementUnderMouse);
            if (!nvs_selected) {
              pageActions.updateSelection(state, new Map([[elementUnderMouse, true]]));

            }
          }
        }

        if (!ctrlPressed && !shiftPressed) {
          // Clear selection (or reduce it to the note under the mouse)
          pageActions.clearSelection(state);
          if (elementUnderMouse !== null) {
            let selectionMap = new Map([[elementUnderMouse, true]]);
            pageActions.updateSelection(state, selectionMap);
          }
        }
      }

      else if (state.mode === PageMode.DragNavigation) {
        pageActions.endDragNavigation(state);
      } else if (state.mode === PageMode.DragSelection) {

        pageActions.endDragSelection(state);

      }
    }
    if (event.button === 2) { // Right press
      setRightMouseIsPressed(false);
      if (mousePos.equals(pressPos)) {
        alert('Context menu not implemented yet')
      }

      if (state.mode === PageMode.DragNavigation) {
        pageActions.endDragNavigation(state);
      }
    }
    // console.log('mouse up')


  }, [state, mousePosOnPress]);

  const handleWheel = useCallback((event) => {
    event.preventDefault();
    navDeviceAutoSwitcher.registerScrollEvent(new Point2D(event.deltaX, event.deltaY));

    let new_height = state.viewportHeight * Math.exp((event.deltaY / 120) * 0.1);
    new_height = Math.max(
      MIN_HEIGHT_SCALE,
      Math.min(new_height, MAX_HEIGHT_SCALE))

    let mousePos = new Point2D(event.clientX, event.clientY);

    // console.log(mouse_pos)
    let mouse_pos_unproj = state.viewport.unprojectPoint(mousePos)

    if (navDeviceAutoSwitcher.device === NavigationDevice.MOUSE) {
      let new_center = state.viewportCenter.add(
        mouse_pos_unproj.subtract(state.viewportCenter).multiply(
          1 - new_height / state.viewportHeight))

      pageActions.updateViewport(state, new_center, new_height);
    } else if (navDeviceAutoSwitcher.device === NavigationDevice.TOUCHPAD) {
      let delta = new Point2D(event.deltaX, event.deltaY);
      // mapActions.startDragNavigation(state, mousePos);
      // mapActions.dragNavigationMove(state, delta);
      // mapActions.endDragNavigation(state);
      let newViewportCenter = state.viewportCenter.add(delta.divide(state.viewport.heightScaleFactor()));
      pageActions.updateViewport(state, newViewportCenter, state.viewportHeight);
    }
  }, [state, navDeviceAutoSwitcher]);

  // Touch event handlers
  const handleTouchStart = useCallback((event) => {
    // Only for single finger touch
    if (event.touches.length === 1) {
      let touchPos = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      setMousePosOnPress(touchPos);
      pageActions.startDragSelection(state, touchPos)
    } else if (event.touches.length === 2) {
      // The pinch gesture navigation is a combination of dragging and zooming
      // so we enter DragNavigation mode and also update the viewport height

      console.log('pinch start')
      let touch1 = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      let touch2 = new Point2D(event.touches[1].clientX, event.touches[1].clientY);
      // touch1 = mapClientPointToSuperContainer(touch1); // NOT TESTED
      // touch2 = mapClientPointToSuperContainer(touch2);
      let distance = touch1.distanceTo(touch2);
      let initPinchCenter = touch1.add(touch2).divide(2)
      setPinchStartDistance(distance);
      setPinchStartViewportHeight(state.viewportHeight);
      setPinchInProgress(true);
      setInitialPinchCenter(initPinchCenter);
      console.log('Initial pinch center', initPinchCenter)

      pageActions.startDragNavigation(state, initPinchCenter)
    }
  }, [state]);

  const handeTouchMove = useCallback((event) => {
    if (event.touches.length === 1) {
      let newTouchPos = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      pageActions.updateDragSelection(state, newTouchPos);

    } else if (event.touches.length === 2) {
      let touch1 = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      let touch2 = new Point2D(event.touches[1].clientX, event.touches[1].clientY);

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
        let new_center = state.viewportCenterOnModeStart?.add(delta_unproj) as Point2D;

        // Apply the correction to make the zoom focused on the pinch center
        // M - mouse pos (unprojected), C - viewport center. s - scale
        // M' = M * s, C' = C * s : M and C after the scale
        // V = (M - C) - (M' - C'): the vector of change for M
        // correction = - ( V ) = (M - C) - (M' - C') = (M - C) * (1 - s)
        let old_viewport = new Viewport(state.viewportCenterOnModeStart as Point2D, pinchStartViewportHeight, state.viewportGeometry);
        let unprInitPinchCenter = old_viewport.unprojectPoint(initialPinchCenter);
        let focusDelta = unprInitPinchCenter.subtract(state.viewportCenterOnModeStart as Point2D);
        let correction = focusDelta.multiply(
          1 - new_height / pinchStartViewportHeight);
        new_center = new_center.add(correction)

        pageActions.updateViewport(state, new_center, new_height);

      }
    }
  }, [state, pinchStartViewportHeight, pinchStartDistance,
    pinchInProgress, initialPinchCenter]);

  const handleTouchEnd = useCallback((event) => {
    // setMouseDown(false);
    if (state.mode === PageMode.DragNavigation) {
      pageActions.endDragNavigation(state);
    }
    setPinchInProgress(false);
  }, [state]);


  const handleMouseEnter = (event: MouseEvent) => {
    // If the mouse is not pressed and we're in some mode, then
    // in most cases the user has moved the mouse out of the page and back
    // and if the button was released outside of the page - we won't know.
    // So we need to infer what to do on reentry.
    // Currently only dragging navigation/selection can be resumed on reentry.
    // Everything else should be cancelled on mouseleave
    if (state.mode === PageMode.DragNavigation ||
      state.mode === PageMode.DragSelection) {
      if (event.buttons === 0) {
        // Clear the state
        pageActions.endDragNavigation(state);
      }
    }
  }

  const handleMouseLeave = (event: MouseEvent) => {
    // Clear the mode (for most modes), to avoid weird behavior
    // currently those are not implemented actually
  }

  // Add native handlers for key/shortcut and wheel events
  useEffect(() => {
    // Existing keydown handler remains unchanged
    const handleKeyDown = (event) => {

      if (event.key === 'c' && event.ctrlKey) {
        // event.preventDefault();
        // copySelectedToClipboard();
      }
      else if (event.ctrlKey && (event.key === '+' || event.key === '=')) { // Plus key (with or without Shift)
        // Zoom in
        pageActions.updateViewport(state, state.viewportCenter, state.viewportHeight / 1.1);
        event.preventDefault();
      } else if (event.ctrlKey && event.key === '-') { // Minus key
        // Zoom out
        pageActions.updateViewport(state, state.viewportCenter, state.viewportHeight * 1.1);
        event.preventDefault();
      } else if (event.ctrlKey && event.key === '0') { // Zero key
        // Reset zoom level
        // event.preventDefault();
      } else if (event.key === 'n') {
        // Start note creation
        pageActions.startNoteCreation(state, state.viewportCenter);
        event.preventDefault();
      }
    };

    // Add both event listeners
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("wheel", handleWheel, { passive: false }); // Set passive to false to allow preventDefault

    // Cleanup function to remove both event listeners
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("wheel", handleWheel);
    };
  }, [state, handleWheel]);

  // Rendering related

  // We'll crate hidden img elements for notes with images and use them in the
  // canvas renderer
  let imageUrls: string[] = []
  for (let noteVS of state.noteViewStatesByOwnId.values()) {
    let note = noteVS.note
    if (note.content.image !== undefined) {
      let url = note.content.image.url;
      imageUrls.push(pamet.pametSchemaToHttpUrl(url));
    }
  }

  return (
    <PageViewStyled>
      <PageOverlay
        // style={{ width: '100%', height: '100%', overflow: 'hidden', touchAction: 'none' }}
        ref={superContainerRef}

        // we watch for mouse events here, to get them in pixel space coords
        // onWheel={handleWheel} << this is added with useEffect in order to use passve: false
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        onMouseUp={handleMouseUp}
        onTouchEnd={handleTouchEnd}
        onMouseMove={handleMouseMove}
        onTouchMove={handeTouchMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onContextMenu={(event) => { event.preventDefault() }}
      >

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
            zIndex: 1000,
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
      </PageOverlay> {/*  map container container */}

      {state.page.tour_segments &&
        <TourComponent
          parentPageViewState={state}
          segments={state.page.tour_segments}
        />
      }

      {/* Image elements (to be used by the cache renderer)
      pamet.parseMediaUrl(url!)
      */}
      {Array.from(imageUrls)
        .map((url) => (
          <img
            key={url}
            src={url}
            alt=""
            style={{ display: 'none' }}
            onError={(event) => {
              log.error('Image load error', event)
            }}
          />
        ))}

    </PageViewStyled>
  );
});
