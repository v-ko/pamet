import { useState, useEffect, useCallback, useRef } from 'react';
import styled from 'styled-components';
import { observer } from 'mobx-react-lite';

import { DEFAULT_EYE_HEIGHT, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE, PametTabIndex } from '../../core/constants';
import { Point2D } from '../../util/Point2D';
import { pageActions } from '../../actions/page';
import { PageMode, PageViewState } from './PageViewState';
import { Viewport } from './Viewport';
import { getLogger } from 'fusion/logging';
import { reaction } from 'mobx';
import React from 'react';
import paper from 'paper';
import { ElementViewState } from './ElementViewState';
import { pamet } from '../../core/facade';
import { NavigationDevice, NavigationDeviceAutoSwitcher } from './NavigationDeviceAutoSwitcher';

import { arrowActions } from '../../actions/arrow';
import { noteActions } from '../../actions/note';
import { InternalLinkNote } from '../../model/InternalLinkNote';
import { appActions } from '../../actions/app';


let log = getLogger('Page.tsx')

// const DEFAULT_VIEWPORT_TRANSITION_T = 0.05;
// type Status = 'loading' | 'error' | 'loaded';


export const PageOverlay = styled.main`
content-visibility: auto;
flex-grow: 1;
flex-shrink: 1;
overflow: hidden;
touch-action: none;
min-width: 30px;
`


export class MouseState {
  buttons: number = 0;
  position: Point2D = new Point2D(0, 0);
  positionOnPress: Point2D = new Point2D(0, 0);
  buttonsOnLeave: number = 0;

  get rightIsPressed() {
    return (this.buttons & 2) !== 0;
  }
  get leftIsPressed() {
    return (this.buttons & 1) !== 0;
  }
  applyPressEvent(event: React.MouseEvent) {
    this.positionOnPress = new Point2D(event.clientX, event.clientY);
    this.buttons = event.buttons;
  }
  applyMoveEvent(event: React.MouseEvent) {
    this.position = new Point2D(event.clientX, event.clientY);
  }
  applyReleaseEvent(event: React.MouseEvent) {
    this.buttons = event.buttons;
  }
}

export const PageView = observer(({ state }: { state: PageViewState }) => {
  /**  */
  // trace(true)

  // const [mouse] = useState(new MouseState());
  const mouse = pamet.appViewState.mouse;

  const [pinchStartDistance, setPinchStartDistance] = useState<number>(0);
  const [pinchInProgress, setPinchInProgress] = useState<boolean>(false);
  const [pinchStartViewportHeight, setPinchStartViewportHeight] = useState<number>(DEFAULT_EYE_HEIGHT);
  const [initialPinchCenter, setInitialPinchCenter] = useState<Point2D>(new Point2D(0, 0));

  const superContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const paperCanvasRef = useRef<HTMLCanvasElement>(null);

  const [navDeviceAutoSwitcher] = useState(new NavigationDeviceAutoSwitcher());

  const canvasCtx = useCallback(() => {
    const canvas = canvasRef.current;
    if (canvas === null) {
      log.error("[canvasCtx] canvas is null")
      return null;
    }

    const ctx = canvas.getContext('2d');

    if (ctx === null) {
      log.error("[canvasCtx] canvas context is null")
      return null;
    }
    return ctx;
  }
    , [canvasRef]);

  const updateGeometryHandler = useCallback(() => {
    let container = superContainerRef.current;
    if (container === null) {
      log.error("[updateGeometry] superContainerRef is null")
      return;
    }
    let boundingRect = container.getBoundingClientRect();

    //Adjust canvas size
    const canvas = canvasRef.current;
    if (canvas === null) {
      log.error("[useEffect] canvas is null")
      return;
    }

    const ctx = canvas.getContext('2d');

    if (ctx === null) {
      log.error("[useEffect] canvas context is null")
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

  }, [state, superContainerRef]);

  // Define effects

  // Initial setup
  useEffect(() => {
    if (!superContainerRef.current) {
      log.error('superContainerRef is null')
      return;
    }
    superContainerRef.current.focus()
  }, [superContainerRef]);

  // init paperjs
  useEffect(() => {
    const paperCanvas = paperCanvasRef.current;
    if (paperCanvas === null) {
      log.error("[useEffect] canvas is null")
      return;
    }
    paper.setup(paperCanvas);
    paper.view.autoUpdate = false;

  }, [state, canvasCtx, paperCanvasRef]);

  // Setup geometry update handling on resize
  useEffect(() => {

    // Use a resize observer to bind the updateGeometry function to resize events
    // of the superContainer
    let container = superContainerRef.current;
    if (container === null) {
      log.error("[updateGeometry] superContainerRef is null")
      return;
    }

    const resizeObserver = new ResizeObserver(updateGeometryHandler);
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [updateGeometryHandler, superContainerRef]);


  // Setup the rendering mobx reaction
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas === null) {
      log.error("[useEffect] canvas is null")
      return;
    }

    const ctx = canvas.getContext('2d');

    if (ctx === null) {
      log.error("[useEffect] canvas context is null")
      return;
    }

    const renderDisposer = reaction(() => {
      // Get note and arrow changes by accessing the computed elements
      let notes = Array.from(state.noteViewStatesByOwnId.values()).map((noteVS) => noteVS._noteData)
      let arrows = Array.from(state.arrowViewStatesByOwnId.values()).map((arrowVS) => arrowVS._arrowData);

      let mousePosIfRelevant: Point2D | null = null;
      // Trigger rendering if the mouse pos has changed AND it's
      // in a mode where that's significant.
      if (state.mode === PageMode.CreateArrow) {
        mousePosIfRelevant = state.projectedMousePosition;
      } else {
        mousePosIfRelevant = null;
      }

      // Trigger on changes in all of the below
      return {
        viewport: state.viewport,
        selectedElements: state.selectedElementsVS.values(),
        dragSelectionRectData: state.dragSelectionRectData,
        mode: state.mode,
        dragSelectedElements: state.dragSelectedElementsVS,
        notes: notes,
        arrows: arrows,
        mousePosIfRelevant: mousePosIfRelevant,
      }
    },
      () => {
        try {
          state.renderer.renderPage(state, ctx);
        } catch (e) {
          log.error('Error rendering page:', e)
        }
      });

    return () => {
      renderDisposer();
      // imgRefUpdateDisposer();
    }
  }, [state, canvasRef]);

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
    mouse.applyPressEvent(event);

    if (event.button === 0) { // left mouse
      if (state.mode === PageMode.None) {
        let realClickPos = state.viewport.unprojectPoint(mousePos)
        // Resize related
        // Get noteVS whose riseze circle is clicked if any
        let resizedNoteVS = state.resizeCircleAt(realClickPos)
        if (resizedNoteVS) {
          // If the note is not selected - deselect all and select it
          if (!state.selectedElementsVS.has(resizedNoteVS)) {
            pageActions.clearSelection(state)
            pageActions.updateSelection(state, new Map([[resizedNoteVS, true]]))
          }
          // Start resize mode
          noteActions.startNotesResize(state, resizedNoteVS, mousePos);
        }
      } else if (state.mode === PageMode.CreateArrow) {
        arrowActions.arrowCreationClick(state, mousePos);
      }
    } else if (event.button === 2) { // right mouse
    }
    log.info('[handleMouseDown] Mouse down: ', mousePos.x, mousePos.y)

  }, [mouse]);

  const handleMouseMove = useCallback((event: React.MouseEvent) => {
    let mousePos = new Point2D(event.clientX, event.clientY);
    let pressPos = mouse.positionOnPress;
    let delta = pressPos.subtract(mousePos);

    pageActions.updateMousePosition(state, mousePos);

    if (state.mode === PageMode.None) {
      if (mouse.rightIsPressed) {
        pageActions.startDragNavigation(state)
        pageActions.dragNavigationMove(state, delta)
        navDeviceAutoSwitcher.registerRightMouseDrag(new Point2D(event.movementX, event.movementY));
      } else if (mouse.leftIsPressed) {
        console.log('Mouse move', PageMode[state.mode], 'left button')

        // If a single arrow is selected - its control points are visible
        // If the user drags a suggested control point - we create it
        // In any case - we start the arrow control point drag
        let editableArrow = state.arrowVS_withVisibleControlPoints()
        if (editableArrow !== null) {
          // Check if we've clicked on an arrow control point
          // Go through all arrows
          let realPressPos = state.viewport.unprojectPoint(pressPos);
          let controlPointIndex = editableArrow.controlPointAt(realPressPos);
          if (controlPointIndex !== null) {
            if (controlPointIndex % 1 !== 0) {
              // Whole indices are control points (.5 are suggested ones)
              arrowActions.createControlPointAndStartDrag(state, realPressPos, controlPointIndex);
            } else {
              // Dragging an existing control point
              arrowActions.startControlPointDrag(state, controlPointIndex);
            }
            // Update the drag position
            arrowActions.controlPointDragMove(state, mousePos);
            return;  // If user clicked on a control point - don't do anythin else
          }
        }

        // If there was a note on the initial position - select and move it
        let noteVS_underMouse = state.noteViewStateAt(state.viewport.unprojectPoint(pressPos))
        let arrowVS_underMouse = state.arrowViewStateAt(state.viewport.unprojectPoint(pressPos))
        let elementUnderMouse = noteVS_underMouse || arrowVS_underMouse;
        if (elementUnderMouse !== null) {
          if (!state.selectedElementsVS.has(elementUnderMouse)) {
            pageActions.clearSelection(state)
            pageActions.updateSelection(state, new Map([[elementUnderMouse, true]]))
          }
          noteActions.startMovingElements(state, pressPos);
          noteActions.elementsMoveUpdate(state, mousePos);
        } else {
          // If there was no note under the mouse - start drag selection
          pageActions.clearSelection(state);
          pageActions.startDragSelection(state, pressPos);
          pageActions.updateDragSelection(state, mousePos);
        }
      }
    } else if (state.mode === PageMode.DragNavigation) {
      pageActions.dragNavigationMove(state, delta);
    } else if (state.mode === PageMode.DragSelection) {
      pageActions.updateDragSelection(state, mousePos);
    } else if (state.mode === PageMode.DraggingEditWindow) {
      pageActions.updateEditWindowDrag(state, mousePos);
    } else if (state.mode === PageMode.ArrowControlPointDrag) {
      arrowActions.controlPointDragMove(state, mousePos);
    } else if (state.mode === PageMode.NoteResize) {
      noteActions.notesResizeMove(state, mousePos);
    } else if (state.mode === PageMode.MoveElements) {
      noteActions.elementsMoveUpdate(state, mousePos);
    }
  }, [mouse.leftIsPressed, mouse.positionOnPress, navDeviceAutoSwitcher, mouse.rightIsPressed, state]);

  const handleMouseUp = useCallback((event: React.MouseEvent) => {
    let mousePos = new Point2D(event.clientX, event.clientY);

    let pressPos = mouse.positionOnPress;
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
    mouse.buttons = event.buttons;

    if (event.button === 0) { // Left press (different from the .buttons left button index, because fu)
      console.log()
      if (state.mode === PageMode.None) {
        if (ctrlPressed && !shiftPressed) { // Toggle selection
          if (elementUnderMouse !== null) {
            let nvs_selected = state.selectedElementsVS.has(elementUnderMouse);
            pageActions.updateSelection(state, new Map([[elementUnderMouse, !nvs_selected]]));
          }
        } else if (shiftPressed || (ctrlPressed && shiftPressed)) { // Add to selection
          if (elementUnderMouse !== null) {
            let nvs_selected = state.selectedElementsVS.has(elementUnderMouse);
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
      } else if (state.mode === PageMode.DraggingEditWindow) {
        pageActions.endEditWindowDrag(state);
      } else if (state.mode === PageMode.ArrowControlPointDrag) {
        arrowActions.endControlPointDrag(state, mousePos);
      } else if (state.mode === PageMode.NoteResize) {
        noteActions.endNotesResize(state, mousePos);
      } else if (state.mode === PageMode.MoveElements) {
        noteActions.endElementsMove(state, mousePos);
      }
    }
    if (event.button === 2) { // Right press
      if (state.mode === PageMode.DragNavigation) {
        pageActions.endDragNavigation(state);
      }

      // If it's a click - show context menu
      if (mousePos.equals(pressPos)) {
        alert('Context menu not implemented yet')
      }
    }
  }, [state, mouse.positionOnPress, mouse]);

  const handleWheel = useCallback((event: WheelEvent) => {
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
      let newViewportCenter = state.viewportCenter.add(delta.divide(state.viewport.heightScaleFactor()));
      pageActions.updateViewport(state, newViewportCenter, state.viewportHeight);
    }
  }, [state, navDeviceAutoSwitcher]);

  // Touch event handlers
  const handleTouchStart = useCallback((event: React.TouchEvent) => {
    // Only for single finger touch
    if (event.touches.length === 1) {
      let touchPos = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      mouse.positionOnPress = touchPos;  // Revize this
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

      pageActions.startDragNavigation(state)
    }
  }, [state, mouse]);

  const handeTouchMove = useCallback((event: React.TouchEvent) => {
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

  const handleMouseLeave = (event: React.MouseEvent) => {
    // Clear the mode (for most modes), to avoid weird behavior
    // currently those are not implemented actually
    pageActions.updateMousePosition(state, null);
    mouse.buttonsOnLeave = event.buttons;
  }

  const handleMouseEnter = (event: React.MouseEvent) => {
    // If the mouse is not pressed and we're in some mode, then
    // in most cases the user has moved the mouse out of the page and back
    // and if the button was released outside of the page - we won't know.
    // So we need to infer what to do on reentry.
    // Currently only dragging navigation/selection can be resumed on reentry.
    // Everything else should be cancelled on mouseleave

    console.log('MOUSE ENTER!!')

    // Update the mouse position in the state
    pageActions.updateMousePosition(state, new Point2D(event.clientX, event.clientY));

    // If the mouse was released outside of the page, we need to clear the mode
    if (mouse.buttonsOnLeave > event.buttons) {
      log.info('Mouse buttons released off-window. Clearing mode')
      pageActions.clearMode(state);
      mouse.buttons = 0;
    }
  }

  // Add native handlers for key/shortcut and wheel events
  useEffect(() => {
    // Existing keydown handler remains unchanged


    // Add both event listeners
    window.addEventListener("wheel", handleWheel, { passive: false }); // Set passive to false to allow preventDefault

    // Cleanup function to remove both event listeners
    return () => {
      window.removeEventListener("wheel", handleWheel);
    };
  }, [state, handleWheel]);

  const handleDoubleClick = (event: React.MouseEvent) => {
    let mousePos = new Point2D(event.clientX, event.clientY);
    let realPos = state.viewport.unprojectPoint(mousePos);

    // If an arrow is selected and a control point is under the mouse - delete it
    let editableArrowVS = state.arrowVS_withVisibleControlPoints()
    if (editableArrowVS !== null) {
      let controlPointIndex = editableArrowVS.controlPointAt(realPos);
      // Whole indices are control points (.5 are suggested ones)
      if (controlPointIndex !== null && controlPointIndex % 1 === 0) {
        arrowActions.deleteControlPoint(editableArrowVS, controlPointIndex);
        return;
      }
    }

    let noteVS_underMouse = state.noteViewStateAt(realPos)
    if (noteVS_underMouse !== null) {
      // If it's a link note - open the link
      let note = noteVS_underMouse.note();
      // For an internal link - follow it
      if (note instanceof InternalLinkNote) {
        let targetPage = note.targetPage();
        if (targetPage !== undefined) {
          appActions.setCurrentPage(pamet.appViewState, targetPage.id)
          return;
        }
      }
      // For an external link - open in new tab
      pageActions.startEditingNote(state, noteVS_underMouse.note());
    } else {
      let realMousePos = state.viewport.unprojectPoint(mousePos);
      pageActions.startNoteCreation(state, realMousePos);
    }
  }


  // Rendering related

  // We'll crate hidden img elements for notes with images and use them in the
  // canvas renderer
  let imageUrls: Set<string> = new Set();
  for (let noteVS of state.noteViewStatesByOwnId.values()) {
    let note = noteVS.note()
    if (note.content.image !== undefined) {
      let url = note.content.image.url;
      imageUrls.add(pamet.apiClient.projectScopedUrlToGlobal(url));
    }
  }

  return (
      <PageOverlay
      className='page-view'  // index.css
      // Set cursor to cross if we're in arrow creation mode
      style={{ cursor: state.mode === PageMode.CreateArrow ? 'crosshair' : 'default' }}
        // style={{ width: '100%', height: '100%', overflow: 'hidden', touchAction: 'none' }}
        ref={superContainerRef}
        tabIndex={PametTabIndex.Page}  // To make the page focusable
        autoFocus={true}
        // onKeyDown={handleKeyDown}
        onDoubleClick={handleDoubleClick}
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
        onFocus={() => { pamet.setContext('canvasFocus', true) }}
        onBlur={() => { pamet.setContext('canvasFocus', false) }}
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

      </PageOverlay>
  );
});
