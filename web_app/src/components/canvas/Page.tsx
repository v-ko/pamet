import { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import { observer } from 'mobx-react-lite';

import { NoteComponent } from '../note/Note';
import { DEFAULT_EYE_HEIGHT, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { NoteData } from '../../model/Note';
import { ArrowComponent, ArrowHeadComponent } from '../Arrow';
import { mapActions } from '../../actions/page';
import { TourComponent } from '../Tour';
import { PageMode, PageViewState } from './PageViewState';
import { Viewport } from '../Viewport';
import { getLogger } from '../../fusion/logging';
import { trace } from 'mobx';


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

  const [mousePosOnPress, setMousePosOnPress] = useState<Point2D>(new Point2D(0, 0));

  const [pinchStartDistance, setPinchStartDistance] = useState<number>(0);
  const [pinchInProgress, setPinchInProgress] = useState<boolean>(false);
  const [pinchStartViewportHeight, setPinchStartViewportHeight] = useState<number>(DEFAULT_EYE_HEIGHT);
  const [initialPinchCenter, setInitialPinchCenter] = useState<Point2D>(new Point2D(0, 0));

  // Define the superContainerRef as a ref callback setting a state ref
  // because I only get a null ref in the useEffect hook
  // https://reactjs.org/docs/hooks-faq.html#how-can-i-measure-a-dom-node
  const [superContainerRef, setSuperContainerRef] = useState<HTMLDivElement | null>(null);
  const superContainerRefCallback = useCallback((node: HTMLDivElement) => {
    if (node !== null) {
      // console.log("superContainerRefCallback", node);
      setSuperContainerRef(node);
    }
  }, []);

  const mapClientPointToSuperContainer = useCallback((point: Point2D): Point2D => {
    // Needed since the mapContainer is transformed and does not yield
    // correct coordinates. And for some reason offsetX and offsetY
    // are not relative to the superContainer but to mapContainer
    //(while the listener is on the former)
    if (superContainerRef === null) {
      console.log("[mapClientPointToSuperContainer] superContainerRef is null")
      return new Point2D(0, 0);
    }
    // map point to state.geometry
    let x = point.x - state.viewportGeometry[0];
    let y = point.y - state.viewportGeometry[1];
    return new Point2D(x, y);
  }, [state.viewportGeometry, superContainerRef]);

  const updateGeometry = useCallback(() => {
    if (superContainerRef === null) {
      console.log("[updateGeometry] mapContainerRef is null")
      return;
    }
    let container = superContainerRef;
    let boundingRect = container.getBoundingClientRect();
    mapActions.updateGeometry(
      state,
      [boundingRect.left, boundingRect.top, boundingRect.width, boundingRect.height]);
    // setGeometry([0, 0, container.clientWidth, container.clientHeight]);
    console.log("Resized to ", boundingRect.left, boundingRect.top, boundingRect.width, boundingRect.height);
  }, [state, superContainerRef]);

  // // Set the initial geometry
  // useLayoutEffect(() => {
  //   // console.log('ref changed', mapContainerRef)
  //   updateGeometry();
  // }, [updateGeometry]);

  // Update geometry on resize events
  useEffect(() => {
    // Use a resize observer to bind the updateGeometry function to resize events
    // of the superContainer
    if (superContainerRef === null) {
      console.log("[useEffect] superContainerRef is null")
      return;
    }
    let container = superContainerRef;
    const resizeObserver = new ResizeObserver(updateGeometry);
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [updateGeometry, superContainerRef]);

  // Should be a command
  const copySelectedToClipboard = useCallback(() => {
    let notesData = Array.from(state.noteViewStatesByOwnId.values()).map((noteVS) => noteVS.note.data());
    let selected_notes = notesData.filter((note) => state.selection.includes(note.id.toString()));
    let text = selected_notes.map((note) => note.content.text).join('\n\n');
    navigator.clipboard.writeText(text);
  }, [state.noteViewStatesByOwnId, state.selection]);

  // // Detect url anchor changes in order to update the viewport and note selection
  // // NOT TESTED
  // useEffect(() => {
  //   const handleHashChange = () => {
  //     // Schema /p/:id?eye_at=height/center_x/center_y&selection=note_id1,note_id2#note_id3
  //     let query = new URLSearchParams(window.location.search);
  //     let url_data = parsePametUrl(window.location.toString());
  //     let eye_at = query.get('eye_at');
  //     if (eye_at !== null) {
  //       let eye_at_params = eye_at.split('/');
  //       if (eye_at_params.length === 3) {
  //         let height = parseFloat(eye_at_params[0]);
  //         let center_x = parseFloat(eye_at_params[1]);
  //         let center_y = parseFloat(eye_at_params[2]);
  //         mapActions.updateViewport(state, new Point2D(center_x, center_y), height);
  //       }
  //       // TODO: selection
  //     }
  //     let hash = window.location.hash;
  //     if (hash !== '') {
  //       let note_id = hash.slice(1);
  //       let noteData = notesData.find((note) => note.id.toString() === note_id);
  //       if (noteData !== undefined) {
  //         // Go to note center
  //         let note = new Note(noteData);
  //         mapActions.updateViewport(state, note.rect.center(), viewportHeight);
  //       }
  //     };
  //   };

  //   window.addEventListener("hashchange", handleHashChange);
  //   return () => {
  //     window.removeEventListener("hashchange", handleHashChange);
  //   };
  // }, [notesData, state, viewportHeight]);


  // Mouse event handlers
  const handleMouseDown = useCallback((event) => {
    // setMouseDown(true);
    // console.log("mouse down");
    let mousePos = mapClientPointToSuperContainer(
      new Point2D(event.clientX, event.clientY));
    setMousePosOnPress(mousePos);
    // setViewportCenterOnModeStart(viewportCenter);
    mapActions.startDragNavigation(state, mousePos)
  }, [state, mapClientPointToSuperContainer]);

  const handleMouseMove = useCallback((event) => {
    // console.log('mouse move')
    let new_mouse_pos = mapClientPointToSuperContainer(
      new Point2D(event.clientX, event.clientY));
    // let new_mouse_pos = new Point2D(event.clientX, event.clientY);
    // setMousePos(new_mouse_pos);
    if (event.buttons === 1) {
      if (state.mode === PageMode.DragNavigation) {
        let delta = mousePosOnPress.subtract(new_mouse_pos);
        mapActions.dragNavigationMove(state, delta);
      }
    }
    // }, [mouseDown, mousePosOnPress, viewportCenterOnModeStart, viewport, viewportHeight, state]);
  }, [mousePosOnPress, state, mapClientPointToSuperContainer]);

  const handleMouseUp = useCallback((event) => {
    // setMouseDown(false);
    // console.log('mouse up')
    if (state.mode === PageMode.DragNavigation) {
      mapActions.endDragNavigation(state);
    }
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
      setMousePosOnPress(touchPos);
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
      let delta = mousePosOnPress.subtract(newTouchPos);
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
  }, [state, mousePosOnPress, pinchStartViewportHeight, pinchStartDistance,
    pinchInProgress, initialPinchCenter]);

  const handleTouchEnd = useCallback((event) => {
    // setMouseDown(false);
    if (state.mode === PageMode.DragNavigation) {
      mapActions.endDragNavigation(state);
    }
    setPinchInProgress(false);
  }, [state]);

  const handleClick = (event) => {
    if (event.target === event.currentTarget &&
      !(event.shiftKey || event.ctrlKey)) {
      mapActions.clearSelection(state);
    }
  };


  const handleNoteClick = (event: React.MouseEvent<HTMLAnchorElement, MouseEvent>, noteData: NoteData) => {
    // if control pressed or shift pressed, add to selection else
    // clear selection and select this note
    if (!(event.ctrlKey || event.shiftKey)) {
      mapActions.clearSelection(state);
    }
    mapActions.updateSelection(state, { [noteData.own_id]: true })
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

  //setup copy shortcut
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'c' && event.ctrlKey) {
        copySelectedToClipboard();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [copySelectedToClipboard]);


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
        ref={superContainerRefCallback}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        onMouseUp={handleMouseUp}
        onTouchEnd={handleTouchEnd}
        onMouseMove={handleMouseMove}
        onTouchMove={handeTouchMove}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >


        {/* This second onClick is hacky - I should check for a note under the
      mouse instad (to handle the cases when the click is on the MapContainer*/}
        <MapContainer
          onClick={handleClick}
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
              // selected={selection.includes(noteViewState.own_id)}
              handleClick={(event) => { handleNoteClick(event, noteViewState.note.data()) }} />
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
              />
            ))}
          </svg>
        </MapContainer>

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
