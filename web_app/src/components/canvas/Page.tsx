import { useState, useEffect, useCallback, useRef } from 'react';
import styled from 'styled-components';
import { observer } from 'mobx-react-lite';

import { NoteComponent } from '../note/Note';
import { ARROW_SELECTION_THICKNESS_DELTA, DEFAULT_EYE_HEIGHT, DRAG_SELECT_COLOR, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE, SELECTION_OVERLAY_COLOR } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { ArrowComponent, ArrowHeadComponent } from '../Arrow';
import { mapActions } from '../../actions/page';
import { TourComponent } from '../Tour';
import { PageMode, PageViewState } from './PageViewState';
import { Viewport } from '../Viewport';
import { getLogger } from '../../fusion/logging';
import { autorun, set, trace } from 'mobx';
import { NoteViewState } from '../note/NoteViewState';
import React from 'react';
import paper from 'paper';
import { Color } from 'paper/dist/paper-core';
import { PageChildViewState } from './PageChildViewState';
import { ArrowViewState } from '../ArrowViewState';
import { color_to_css_rgba_string } from '../../util';
import { Rectangle } from '../../util/Rectangle';


let log = getLogger('Page.tsx')

const selectionColor = color_to_css_rgba_string(SELECTION_OVERLAY_COLOR);
const dragSelectRectColor = color_to_css_rgba_string(DRAG_SELECT_COLOR);
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

transform:  scale(var(--map-scale)) translate(var(--map-translate-x), var(--map-translate-y)) translate(50%, 50%); //
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

  const [leftMouseIsPressed, setLeftMouseIsPressed] = useState<boolean>(false);
  const [mousePosOnLeftPress, setMousePosOnLeftPress] = useState<Point2D>(new Point2D(0, 0));

  const [pinchStartDistance, setPinchStartDistance] = useState<number>(0);
  const [pinchInProgress, setPinchInProgress] = useState<boolean>(false);
  const [pinchStartViewportHeight, setPinchStartViewportHeight] = useState<number>(DEFAULT_EYE_HEIGHT);
  const [initialPinchCenter, setInitialPinchCenter] = useState<Point2D>(new Point2D(0, 0));

  const superContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const mapClientPointToSuperContainer = useCallback((point: Point2D): Point2D => {
    // Needed since the mapContainer is transformed and does not yield
    // correct coordinates. And for some reason offsetX and offsetY
    // are not relative to the superContainer but to mapContainer
    //(while the listener is on the former)

    // map point to state.geometry
    let x = point.x - state.viewportGeometry[0];
    let y = point.y - state.viewportGeometry[1];
    return new Point2D(x, y);
  }, [state.viewportGeometry]); // superContainerRef

  // Initial setup - init paperjs
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas === null) {
      console.log("[useEffect] canvas is null")
      return;
    }
    paper.setup(canvas);
  }, []);

  const updateGeometryHandler = useCallback(() => {
    let container = superContainerRef.current;
    if (container === null) {
      console.log("[updateGeometry] mapContainerRef is null")
      return;
    }
    let boundingRect = container.getBoundingClientRect();

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
    const setupProjectionMatrix = () => {
      let pixelSpaceRect = state.viewport.pixelSpaceRect;
      paper.view.viewSize = new paper.Size(pixelSpaceRect.width(), pixelSpaceRect.height());
      // Update global transformation matrix
      // Reset the transformation matrix
      paper.view.matrix.reset();
      // Translate to the center of the canvas
      paper.view.translate(new paper.Point(pixelSpaceRect.width() / 2, pixelSpaceRect.height() / 2));

      // Scale the canvas
      paper.view.scale(state.viewport.heightScaleFactor());
      // Translate to the center of the viewport
      paper.view.translate(new paper.Point(-state.viewport.center.x, -state.viewport.center.y));
    }

    const disposer = autorun(() => {
      // console.log('Rendering non-component-based shapes overlay', state.selectedChildren)

      // Clear the canvas
      paper.project.clear();
      paper.view.matrix.reset();
      setupProjectionMatrix();

      // Draw elements in pixel space. We have to unproject them explicitly
      // Otherwise we'd have to setup paperjs Groups and specify parents for
      // each element

      // Draw drag selection rectangle
      if (state.mode === PageMode.DragSelection && state.dragSelectionRectData !== null) {
        let [x, y, width, height] = state.dragSelectionRectData
        let selectionRect = state.viewport.unprojectRect(new Rectangle(x, y, width, height));
        let paperRect = new paper.Rectangle(...selectionRect.data());
        let selectionRectPath = new paper.Path.Rectangle(paperRect);
        selectionRectPath.fillColor = new Color(dragSelectRectColor);
      }

      // Draw elemnts in real space

      // Draw selected children
      const drawSelectionOverlay = (childVS: PageChildViewState) => {
        if (childVS instanceof NoteViewState) {
          let noteVS = childVS;
          let noteRect = noteVS.note.rect();
          let rect = new paper.Path.Rectangle(
            new paper.Rectangle(
              new paper.Point(noteRect.x, noteRect.y),
              new paper.Size(noteRect.width(), noteRect.height())
            )
          );
          rect.fillColor = new Color(selectionColor);
        } else if (childVS instanceof ArrowViewState) {
          let arrowVS = childVS;
          let path = arrowVS.paperPath
          path.strokeWidth = arrowVS.arrow.line_thickness + ARROW_SELECTION_THICKNESS_DELTA;
          path.strokeColor = new Color(selectionColor);
        }
      }

      // If drag selection is active - add drag selected children to the selection
      if (state.mode === PageMode.DragSelection) {
        for (const childVS of state.dragSelectedChildren) {
          drawSelectionOverlay(childVS);
        }
      }

      for (const childVS of state.selectedChildren) {
        drawSelectionOverlay(childVS);
      }
    });

    return () => disposer();
  }, [state.viewport, state.selectedChildren, state.dragSelectionRectData, state.mode, state.dragSelectedChildren]);

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
    let mousePos = mapClientPointToSuperContainer(new Point2D(event.clientX, event.clientY));
    setLeftMouseIsPressed(true);
    setMousePosOnLeftPress(mousePos);
    log.info('[handleMouseDown] Mouse down: ', mousePos.x, mousePos.y)

    let unprojMousePos = state.viewport.unprojectPoint(
      mapClientPointToSuperContainer(new Point2D(mousePos.x, mousePos.y)));

    let childUnderMouse: PageChildViewState | null = state.arrowViewStateAt(unprojMousePos)
    let noteVS_underMouse = state.noteViewStateAt(unprojMousePos)
    if (noteVS_underMouse !== null) { // Note priority on selection
      childUnderMouse = noteVS_underMouse;
    }
    // resize_nv = self.resize_circle_intersect(...

    if (childUnderMouse !== null) {
      console.log('Child under mouse', childUnderMouse)
    }

    // if create arrow mode
    // ..

    // If either ctrl or shift are pressed - start the drag-select
    // But if it's just a click - clear the selection and select only the
    // child under the mouse
    if (event.ctrlKey && event.shiftKey) {
      console.log('Ctrl and shift pressed, starting drag selection')
      mapActions.startDragSelection(state, mousePos);
    }

    // If ctrl is pressed - toggle selection of the child under the mouse
    if (event.ctrlKey && !event.shiftKey ) {
      if (childUnderMouse !== null) {
        let nvs_selected = state.selectedChildren.has(childUnderMouse);
        mapActions.updateSelection(state, new Map([[childUnderMouse, !nvs_selected]]));
      }
    }

    // Clear selection (or reduce it to the note under the mouse)
    if (!event.ctrlKey && !event.shiftKey) {
      console.log('No ctrl or shift pressed, clearing selection')
      // if resize_nv:
      //   child_under_mouse = resize_nv

      mapActions.clearSelection(state);

      if (childUnderMouse !== null) {
        let selectionMap = new Map([[childUnderMouse, true]]);
        console.log('[Page] Selecting child', selectionMap)
        mapActions.updateSelection(state, selectionMap);
      }
    }

    // mapActions.startDragNavigation(state, mousePos)
  }, [state, mapClientPointToSuperContainer]);

  const handleMouseMove = useCallback((event) => {
    let new_mouse_pos = mapClientPointToSuperContainer(
      new Point2D(event.clientX, event.clientY));

    if (event.buttons === 1) {
      // console.log('mouse move, left button', PageMode[state.mode])
      if (state.mode === PageMode.None) {
        if (leftMouseIsPressed) {
          mapActions.startDragNavigation(state, mousePosOnLeftPress)
          let delta = new_mouse_pos.subtract(mousePosOnLeftPress)
          mapActions.dragNavigationMove(state, delta)
        }
      } else if (state.mode === PageMode.DragNavigation) {
        let delta = mousePosOnLeftPress.subtract(new_mouse_pos);
        mapActions.dragNavigationMove(state, delta);
      } else if (state.mode === PageMode.DragSelection) {
        mapActions.updateDragSelection(state, new_mouse_pos);
      }
    }
  }, [leftMouseIsPressed, mousePosOnLeftPress, state, mapClientPointToSuperContainer]);

  const handleMouseUp = useCallback((event) => {
    // console.log('mouse up')
    if (state.mode === PageMode.DragNavigation) {
      mapActions.endDragNavigation(state);
    } else if (state.mode === PageMode.DragSelection) {
      mapActions.endDragSelection(state);
    }
    setLeftMouseIsPressed(false);
  }, [state]);

  const handleWheel = (event) => {
    let new_height = state.viewportHeight * Math.exp((event.deltaY / 120) * 0.1);
    new_height = Math.max(
      MIN_HEIGHT_SCALE,
      Math.min(new_height, MAX_HEIGHT_SCALE))

    let mouse_pos = mapClientPointToSuperContainer(
      new Point2D(event.clientX, event.clientY));
    // console.log(mouse_pos)
    let mouse_pos_unproj = state.viewport.unprojectPoint(mouse_pos)
    let new_center = state.viewportCenter.add(
      mouse_pos_unproj.subtract(state.viewportCenter).multiply(
        1 - new_height / state.viewportHeight))

    mapActions.updateViewport(state, new_center, new_height);
  };

  // Touch event handlers
  const handleTouchStart = useCallback((event) => {
    // Only for single finger touch
    if (event.touches.length === 1) {
      // setMouseDown(true);
      let touchPos = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      setMousePosOnLeftPress(touchPos);
      // setViewportCenterOnModeStart(viewportCenter);
      mapActions.startDragNavigation(state, touchPos)
    } else if (event.touches.length === 2) {
      // The pinch gesture navigation is a combination of dragging and zooming
      // so we enter DragNavigation mode and also update the viewport height

      // setViewportCenterOnModeStart(viewportCenter);
      console.log('pinch start')
      let touch1 = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      let touch2 = new Point2D(event.touches[1].clientX, event.touches[1].clientY);
      touch1 = mapClientPointToSuperContainer(touch1); // NOT TESTED
      touch2 = mapClientPointToSuperContainer(touch2);
      let distance = touch1.distanceTo(touch2);
      setPinchStartDistance(distance);
      setPinchStartViewportHeight(state.viewportHeight);
      setPinchInProgress(true);
      let initPinchCenter = touch1.add(touch2).divide(2)
      setInitialPinchCenter(initPinchCenter);
      console.log('Initial pinch center', initPinchCenter)

      mapActions.startDragNavigation(state, initPinchCenter)
    }
  }, [state, mapClientPointToSuperContainer]);

  const handeTouchMove = useCallback((event) => {
    if (event.touches.length === 1) {
      let newTouchPos = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      let delta = mousePosOnLeftPress.subtract(newTouchPos);
      mapActions.dragNavigationMove(state, delta);

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
  }, [state, mousePosOnLeftPress, pinchStartViewportHeight, pinchStartDistance,
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

  // //setup copy shortcut
  // useEffect(() => {
  //   const handleKeyDown = (event) => {
  //     if (event.key === 'c' && event.ctrlKey) {
  //       copySelectedToClipboard();
  //     }
  //   };

  //   window.addEventListener("keydown", handleKeyDown);

  //   return () => {
  //     window.removeEventListener("keydown", handleKeyDown);
  //   };
  // }, [copySelectedToClipboard]);


  // Auto navigation animation effect
  useEffect(() => {
    if (state.mode === PageMode.AutoNavigation) {
      // console.log('Auto navigation mode activated')
      setTimeout(() => {
        mapActions.updateAutoNavigation(state);
      }, 0);
    }
  }, [state.mode, state.autoNavAnimation, state.autoNavAnimation?.lastUpdateTime, state]);

  // // Rendering phase
  // if (status === 'loading') {
  //   return <p>(Page) Loading...</p>;
  // }

  // if (status === 'error') {
  //   return <p>Error loading data. Message: {errorString}</p>;
  // }

  // TODO: setup min/max viewport position.
  let vb_x = -100000;
  let vb_y = -100000;
  let vb_width = 200000;
  let vb_height = 200000;

  // // Setup the transitions on navigation
  // let viewportTransitionDuration = DEFAULT_VIEWPORT_TRANSITION_T;
  // if (state.mode === MapPageMode.AutoNavigation) {
  //   viewportTransitionDuration = AUTO_NAVIGATE_TRANSITION_DURATION;
  // }

  // // Hacky fix: transitions hang on Chrome on large height values
  // if (state.viewport.height > 5) {
  //   viewportTransitionDuration = 0;  // Zero value removes the transition
  // }

  // log.info(`Rendering Page ${state.page.name} (id: ${state.page.id})`)
  let noteCount = Array.from(state.noteViewStatesByOwnId.values()).length
  let arrowCount = Array.from(state.arrowViewStatesByOwnId.values()).length
  // log.info(`Notes count: ${noteCount}, Arrows count: ${arrowCount}`)

  return (
    <MapLayoutContainer>
      <MapSuperContainer
        // style={{ width: '100%', height: '100%', overflow: 'hidden', touchAction: 'none' }}
        id="map-super-container"
        ref={superContainerRef}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        onMouseUp={handleMouseUp}
        onTouchEnd={handleTouchEnd}
        onMouseMove={handleMouseMove}
        onTouchMove={handeTouchMove}
        onClick={handleClickOnPage}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >

        {/* This second onClick is hacky - I should check for a note under the
      mouse instad (to handle the cases when the click is on the MapContainer*/}
        <MapContainer
          onClick={handleClickOnPage}
          viewport={state.viewport}
          // transformTransitionDuration={viewportTransitionDuration}
          style={{
            '--map-scale': state.viewport.heightScaleFactor(),
            '--map-translate-x': -state.viewport.center.x + 'px',
            '--map-translate-y': -state.viewport.center.y + 'px',
          }}
        >


          {Array.from(state.noteViewStatesByOwnId.values()).map((noteViewState) => (
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
          </svg>


        </MapContainer>
        {/* A canvas with the size vb (large) on which the selection overlays  will be drawn */}
        <canvas
          id="selection-overlay"
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
      </MapSuperContainer> {/*  map container container */}

      {state.page.tour_segments &&
        <TourComponent
          parentPageViewState={state}
          segments={state.page.tour_segments}
        />
      }
      {/* A caption for diagnostics showing note and arrow count at the top-left */}
      <p
        style={{
          position: 'absolute',
          margin: '10px',
          fontSize: '15px',
          fontFamily: 'sans-serif',
          pointerEvents: 'none',
        }}
      >
        {`Note views: ${noteCount}, Arrow views: ${arrowCount}`}
      </p>
    </MapLayoutContainer>
  );
});
