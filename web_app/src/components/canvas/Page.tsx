import { useState, useEffect, useCallback, useRef } from 'react';
import styled from 'styled-components';
import { observer } from 'mobx-react-lite';

import { DEFAULT_EYE_HEIGHT, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { mapActions } from '../../actions/page';
import { TourComponent } from '../Tour';
import { PageMode, PageViewState } from './PageViewState';
import { Viewport } from './Viewport';
import { getLogger } from '../../fusion/logging';
import { reaction } from 'mobx';
import { NoteViewState } from '../note/NoteViewState';
import React from 'react';
import paper from 'paper';
import { CanvasPageRenderer } from './canvasPageRenderer';
import { PageChildViewState } from './PageChildViewState';
import { pamet } from '../../facade';
import { NavigationDevice, NavigationDeviceAutoSwitcher } from './NavigationDeviceAutoSwitcher';
import { ArrowComponent, ArrowHeadComponent } from '../arrow/Arrow';
import { NoteComponent } from '../note/Note';


let log = getLogger('Page.tsx')

// const DEFAULT_VIEWPORT_TRANSITION_T = 0.05;
// type Status = 'loading' | 'error' | 'loaded';

export const MapLayoutContainer = styled.div`
width: 100%;
height: 100%;
overflow: hidden;
display: flex;
@media (max-width: 768px) {
  flex-direction: column;
  flex-flow: column-reverse;
}
`;

export const MapSuperContainer = styled.div`
content-visibility: auto;
flex-grow: 1;
flex-shrink: 1;
overflow: hidden;
touch-action: none;
min-width: 30px;
`

export const MapContainer = styled.div`

width: ${props => props.viewport.geometry[2]}px;
height: ${props => props.viewport.geometry[3]}px;
width: 100%;
height: 100%;

transform:  scale(var(--map-scale)) translate(var(--map-translate-x), var(--map-translate-y));
backface-visibility: hidden;  // Fixes rendering artefact bug

// Transitions are very inefficient (at small scale coefficients)
// So we disable them for now
/* ${props => props.transformTransitionDuration > 0 ?
    `transition: transform ${props.transformTransitionDuration}s;` : ''} */
touch-action: none;
user-select: none;
`;

export const MapPageComponent = observer(({ state }: { state: PageViewState }) => {
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
  const mapContainerRef = useRef<HTMLDivElement>(null);
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


    // Initial render
    setTimeout(() => {
      console.log("[useEffect.setTimeout] INTO TIMEOUT")
      let ctx = canvasCtx()
      if (ctx === null) {
        console.log("[useEffect] canvas context is null")
        return;
      }
      cacheService.renderPage(state, ctx);
    }, 1);

  }, [state, canvasCtx, paperCanvasRef, cacheService]);

  const updateGeometryHandler = useCallback(() => {
    console.log("[updateGeometry] called")
    let container = superContainerRef.current;
    if (container === null) {
      console.log("[updateGeometry] mapContainerRef is null")
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
    // let pixelSpaceRect = state.viewport.projectedBounds();
    canvas.width = boundingRect.width * dpr;
    canvas.height = boundingRect.height * dpr;

    // Update viewport geometry

    mapActions.updateGeometry(
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
      console.log("[updateGeometry] mapContainerRef is null")
      return;
    }

    const resizeObserver = new ResizeObserver(updateGeometryHandler);
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [updateGeometryHandler, superContainerRef]);


  // Render all non-component-based shapes on the canvas
  useEffect(() => {
    // const setupPaperProjectionMatrix = () => {
    //   let pixelSpaceRect = state.viewport.projectedBounds();
    //   paper.view.viewSize = new paper.Size(pixelSpaceRect.width(), pixelSpaceRect.height());
    //   // Update global transformation matrix
    //   // Reset the transformation matrix
    //   paper.view.matrix.reset();
    //   // Translate to the center of the canvas
    //   // paper.view.translate(new paper.Point(pixelSpaceRect.width() / 2, pixelSpaceRect.height() / 2));

    //   // Scale the canvas
    //   paper.view.scale(state.viewport.heightScaleFactor());
    //   // Translate to the center of the viewport
    //   paper.view.translate(new paper.Point(-state.viewport.xReal, -state.viewport.yReal));
    // }

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
        selectedChildren: state.selectedChildren.values(),
        dragSelectionRectData: state.dragSelectionRectData,
        mode: state.mode,
        dragSelectedChildren: state.dragSelectedChildren,
        arrowViewStatesByOwnId: state.arrowViewStatesByOwnId,
        noteViewStatesByOwnId: state.noteViewStatesByOwnId,
      }
    },
      () => {
        // let selectedc = state.selectedChildren.values();
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

    // // Test css navigation speed without rerender
    // if (mapContainerRef.current !== null) {
    //   mapContainerRef.current.style.setProperty('--map-translate-x', -new_mouse_pos.x * 3 + 'px');
    //   mapContainerRef.current.style.setProperty('--map-translate-y', -new_mouse_pos.y * 3 + 'px');
    //   // test scale too 100px mouse pos = x2 scale
    //   mapContainerRef.current.style.setProperty('--map-scale', 1 / (new_mouse_pos.y / 100) + '');
    //   // console.log('Mouse pos', new_mouse_pos.x, new_mouse_pos.y)
    // }

    // let mousePos = mapClientPointToSuperContainer(
    //   new Point2D(event.clientX, event.clientY));
    let mousePos = new Point2D(event.clientX, event.clientY);
    let pressPos = mousePosOnPress;
    let delta = pressPos.subtract(mousePos);
    let ctrlIsPressed = event.ctrlKey;
    let shiftIsPressed = event.shiftKey;

    // if (event.buttons === 1) {
    //   console.log('mouse move, left button', PageMode[state.mode])
    // }

    if (state.mode === PageMode.None) {
      if (rightMouseIsPressed) {
        mapActions.startDragNavigation(state, pressPos)
        mapActions.dragNavigationMove(state, delta)
        navDeviceAutoSwitcher.registerRightMouseDrag(new Point2D(event.movementX, event.movementY));
      } else if (leftMouseIsPressed) {
        // let nvs_underMouse = state.noteViewStateAt(mousePos)
        // let arrowVS_underMouse = state.arrowViewStateAt(mousePos)

        // // If there's just an arrow under the mouse (for moving?)
        // if (arrowVS_underMouse && !nvs_underMouse) {
        //   // Ignore arrows that are not free floating
        //   let arrow = arrowVS_underMouse.arrow
        //   if (arrow.tail_coords !== null && arrow.head_coords !== null) {
        //     // pass
        //   } else {
        //     arrowVS_underMouse = null
        //   }
        // }

        // // If there's a note - prefer it over the arrow
        // if (nvs_underMouse !== null || arrowVS_underMouse !== null) {
        //   let childUnderMouse = nvs_underMouse || arrowVS_underMouse
        //   if (!ctrlIsPressed && !shiftIsPressed && !state.selectedChildren.has(childUnderMouse!)){
        //     mapActions.clearSelection(state);
        //     mapActions.updateSelection(state, new Map([[childUnderMouse!, true]]));
        //   }

        //   //... this is needed for drag-move
        // }
        mapActions.clearSelection(state);
        mapActions.startDragSelection(state, pressPos);
        mapActions.updateDragSelection(state, mousePos);
      }
    } else if (state.mode === PageMode.DragNavigation) {
      mapActions.dragNavigationMove(state, delta);
    } else if (state.mode === PageMode.DragSelection) {
      mapActions.updateDragSelection(state, mousePos);
    }
    // }
  }, [leftMouseIsPressed, mousePosOnPress, navDeviceAutoSwitcher, rightMouseIsPressed, state]);

  const handleMouseUp = useCallback((event) => {
    // let mousePos = mapClientPointToSuperContainer(
    //   new Point2D(event.clientX, event.clientY));
    let mousePos = new Point2D(event.clientX, event.clientY);

    let pressPos = mousePosOnPress;
    let realPos = state.viewport.unprojectPoint(mousePos);
    let ctrlPressed = event.ctrlKey;
    let shiftPressed = event.shiftKey;

    let childUnderMouse: PageChildViewState | null = state.arrowViewStateAt(realPos)
    let noteVS_underMouse = state.noteViewStateAt(realPos)
    if (noteVS_underMouse !== null) {
      childUnderMouse = noteVS_underMouse;
    }

    console.log('Mouse up', PageMode[state.mode], 'button', event.button, childUnderMouse)

    event.preventDefault();
    if (event.button === 0) { // Left press
      setLeftMouseIsPressed(false);
      if (state.mode === PageMode.None) {
        if (ctrlPressed && !shiftPressed) { // Toggle selection
          if (childUnderMouse !== null) {
            let nvs_selected = state.selectedChildren.has(childUnderMouse);
            mapActions.updateSelection(state, new Map([[childUnderMouse, !nvs_selected]]));
          }
        } else if (shiftPressed || (ctrlPressed && shiftPressed)) { // Add to selection
          if (childUnderMouse !== null) {
            let nvs_selected = state.selectedChildren.has(childUnderMouse);
            if (!nvs_selected) {
              mapActions.updateSelection(state, new Map([[childUnderMouse, true]]));

            }
          }
        }

        if (!ctrlPressed && !shiftPressed) {
          // Clear selection (or reduce it to the note under the mouse)
          mapActions.clearSelection(state);
          if (childUnderMouse !== null) {
            let selectionMap = new Map([[childUnderMouse, true]]);
            mapActions.updateSelection(state, selectionMap);
          }
        }
      }

      else if (state.mode === PageMode.DragNavigation) {
        mapActions.endDragNavigation(state);
      } else if (state.mode === PageMode.DragSelection) {

        mapActions.endDragSelection(state);

      }
    }
    if (event.button === 2) { // Right press
      setRightMouseIsPressed(false);
      if (mousePos.equals(pressPos)) {
        alert('Context menu not implemented yet')
      }

      if (state.mode === PageMode.DragNavigation) {
        mapActions.endDragNavigation(state);
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

      mapActions.updateViewport(state, new_center, new_height);
    } else if (navDeviceAutoSwitcher.device === NavigationDevice.TOUCHPAD) {
      let delta = new Point2D(event.deltaX, event.deltaY);
      // mapActions.startDragNavigation(state, mousePos);
      // mapActions.dragNavigationMove(state, delta);
      // mapActions.endDragNavigation(state);
      let newViewportCenter = state.viewportCenter.add(delta.divide(state.viewport.heightScaleFactor()));
      mapActions.updateViewport(state, newViewportCenter, state.viewportHeight);
    }
  }, [state, navDeviceAutoSwitcher]);

  // Touch event handlers
  const handleTouchStart = useCallback((event) => {
    // Only for single finger touch
    if (event.touches.length === 1) {
      let touchPos = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      setMousePosOnPress(touchPos);
      mapActions.startDragSelection(state, touchPos)
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

      mapActions.startDragNavigation(state, initPinchCenter)
    }
  }, [state]);

  const handeTouchMove = useCallback((event) => {
    if (event.touches.length === 1) {
      let newTouchPos = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      // let delta = mousePosOnLeftPress.subtract(newTouchPos);
      mapActions.updateDragSelection(state, newTouchPos);

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

        mapActions.updateViewport(state, new_center, new_height);

      }
    }
  }, [state, pinchStartViewportHeight, pinchStartDistance,
    pinchInProgress, initialPinchCenter]);

  const handleTouchEnd = useCallback((event) => {
    // setMouseDown(false);
    if (state.mode === PageMode.DragNavigation) {
      mapActions.endDragNavigation(state);
    }
    setPinchInProgress(false);
  }, [state]);

  const handleClickOnPage = (event: React.MouseEvent) => {

  };

  const handleClickOnNote = (event: React.MouseEvent<HTMLAnchorElement, MouseEvent>, noteVS: NoteViewState) => {

  }

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
        mapActions.endDragNavigation(state);
      }
    }
  }

  const handleMouseLeave = (event: MouseEvent) => {
    // Clear the mode (for most modes), to avoid weird behavior
    // currently those are not implemented actually
  }
  useEffect(() => {
    // Existing keydown handler remains unchanged
    const handleKeyDown = (event) => {
      if (event.key === 'c' && event.ctrlKey) {
        // copySelectedToClipboard();
      }
      else if (event.ctrlKey && (event.key === '+' || event.key === '=')) { // Plus key (with or without Shift)
        event.preventDefault();
        // Zoom in
        mapActions.updateViewport(state, state.viewportCenter, state.viewportHeight / 1.1);
      } else if (event.ctrlKey && event.key === '-') { // Minus key
        event.preventDefault();
        // Zoom out
        mapActions.updateViewport(state, state.viewportCenter, state.viewportHeight * 1.1);
      } else if (event.ctrlKey && event.key === '0') { // Zero key
        event.preventDefault();
        // Reset zoom level
        console.log('Custom reset zoom logic');
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

  // Auto navigation animation effect
  useEffect(() => {
    if (state.mode === PageMode.AutoNavigation) {
      // console.log('Auto navigation mode activated')
      setTimeout(() => {
        mapActions.updateAutoNavigation(state);
      }, 0);
    }
  }, [state.mode, state.autoNavAnimation, state.autoNavAnimation?.lastUpdateTime, state]);

  // // Those are needed for the React note rendering
  // let vb_x = -100000;
  // let vb_y = -100000;
  // let vb_width = 200000;
  // let vb_height = 200000;

  // // Setup the transitions on navigation
  // let viewportTransitionDuration = DEFAULT_VIEWPORT_TRANSITION_T;
  // if (state.mode === MapPageMode.AutoNavigation) {
  //   viewportTransitionDuration = AUTO_NAVIGATE_TRANSITION_DURATION;
  // }

  // // Hacky fix: transitions hang on Chrome on large height values
  // if (state.viewport.height > 5) {
  //   viewportTransitionDuration = 0;  // Zero value removes the transition
  // }

  // debug info
  // log.info(`Rendering Page ${state.page.name} (id: ${state.page.id})`)
  // let noteCount = Array.from(state.noteViewStatesByOwnId.values()).length
  // let arrowCount = Array.from(state.arrowViewStatesByOwnId.values()).length
  // log.info(`Notes count: ${noteCount}, Arrows count: ${arrowCount}`)

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
    <MapLayoutContainer>
      <MapSuperContainer
        // style={{ width: '100%', height: '100%', overflow: 'hidden', touchAction: 'none' }}
        id="map-super-container"
        ref={superContainerRef}

        // we watch for mouse events here, to get them in pixel space coords
        // onWheel={handleWheel} << this is added with useEffect in order to use passve: false
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        onMouseUp={handleMouseUp}
        onTouchEnd={handleTouchEnd}
        onMouseMove={handleMouseMove}
        onTouchMove={handeTouchMove}
        onClick={handleClickOnPage}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onContextMenu={(event) => { event.preventDefault() }}
      >


        <MapContainer
          onClick={handleClickOnPage}
          viewport={state.viewport}
          ref={mapContainerRef}
          // transformTransitionDuration={viewportTransitionDuration}
          style={{
            '--map-scale': state.viewport.heightScaleFactor(),
            '--map-translate-x': -state.viewport.xReal + 'px',
            '--map-translate-y': -state.viewport.yReal + 'px',
            // '--map-translate-x': -state.viewport.center.x + 'px',
            // '--map-translate-y': -state.viewport.center.y + 'px',
          }}
        >

          {/* {Array.from(state.noteViewStatesByOwnId.values()).map((noteViewState) => (
            <NoteComponent
              key={noteViewState.note.id}
              noteViewState={noteViewState}
              handleClick={(event) => { handleClickOnNote(event, noteViewState) }} />
          ))}

          <svg
            viewBox={`${vb_x} ${vb_y} ${vb_width} ${vb_height}`}
            style={{
              position: 'absolute',
              left: `${vb_x}`,
              top: `${vb_y}`,
              width: `${vb_width}`,
              height: `${vb_height}`,
              pointerEvents: 'none',
              outline: '100px solid red',
            }}
          >
            <defs>
              {Array.from(state.arrowViewStatesByOwnId.values()).map((arrowVS) => (
                <ArrowHeadComponent key={arrowVS.arrow.id} arrowViewState={arrowVS} />
              ))}
            </defs>
            {Array.from(state.arrowViewStatesByOwnId.values()).map((arrowVS) => (
              <ArrowComponent
                key={arrowVS.arrow.id}
                arrowViewState={arrowVS}
                clickHandler={(event) => { console.log('Arrow clicked', arrowVS.arrow.id) }}
              />
            ))}
          </svg> */}


        </MapContainer>
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
      </MapSuperContainer> {/*  map container container */}

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

    </MapLayoutContainer>
  );
});
