import { useState, useEffect, useCallback, useRef } from 'react';
import { observer } from 'mobx-react-lite';

import { DEFAULT_EYE_HEIGHT, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE, PametTabIndex } from "@/core/constants";
import { Point2D } from 'fusion/primitives/Point2D';
import { pageActions } from "@/actions/page";
import { PageMode, PageViewState } from "@/components/page/PageViewState";
import { Viewport } from "@/components/page/Viewport";
import { getLogger } from 'fusion/logging';
import { reaction } from 'mobx';
import React from 'react';
import paper from 'paper';
import "@/components/page/PageView.css";
import { ElementViewState } from "@/components/page/ElementViewState";
import { pamet } from "@/core/facade";
import { NavigationDevice, NavigationDeviceAutoSwitcher } from "@/components/page/NavigationDeviceAutoSwitcher";

import { arrowActions } from "@/actions/arrow";
import { noteActions } from "@/actions/note";
import { appActions } from "@/actions/app";
import { Page } from '@/model/Page';
import { createNoteWithImageFromBlob } from '@/procedures/page';
import { CardNote } from '@/model/CardNote';
import { MouseState } from '@/containers/app/WebAppState';
import { CanvasPageRenderer } from './DirectRenderer';
import { NoteCacheManager } from '../note/NoteCacheManager';


let log = getLogger('Page.tsx')


export class PageController {
  navDeviceAutoSwitcher: NavigationDeviceAutoSwitcher = new NavigationDeviceAutoSwitcher();
  private pageVS: PageViewState;
  private mouseState: MouseState;
  private superContainerRef: React.RefObject<HTMLDivElement>;
  private mobxReactionRegistration?: () => void;
  private _renderer?: CanvasPageRenderer;

  public get renderer(): CanvasPageRenderer | undefined {
    return this._renderer;
  }

  constructor(
    state: PageViewState,
    mouseState: MouseState,
    superContainerRef: React.RefObject<HTMLDivElement>
  ) {
    this.pageVS = state;
    this.mouseState = mouseState;
    this.superContainerRef = superContainerRef;

  }

  handleMouseLeave = (event: MouseEvent) => {
    // Clear the mode (for most modes), to avoid weird behavior
    // currently those are not implemented actually
    appActions.updateMouseState(pamet.appViewState, {
      position: null,
      buttonsOnLeave: event.buttons,
    });
  }

  handleMouseEnter = (event: MouseEvent) => {
    // If the mouse is not pressed and we're in some mode, then
    // in most cases the user has moved the mouse out of the page and back
    // and if the button was released outside of the page - we won't know.
    // So we need to infer what to do on reentry.
    // Currently only dragging navigation/selection can be resumed on reentry.
    // Everything else should be cancelled on mouseleave

    // Update the mouse position in the state
    appActions.updateMouseState(pamet.appViewState, {
      position: new Point2D([event.clientX, event.clientY]),
    });

    // If the mouse was released outside of the page, we need to clear the mode
    if (this.mouseState.buttonsOnLeave > event.buttons) {
      log.info('Mouse buttons released off-window. Clearing mode')
      pageActions.clearMode(this.pageVS);
      appActions.updateMouseState(pamet.appViewState, {
        buttons: 0
      });
    }
  }

  handleMouseDown = (event: MouseEvent) => {
    // let mousePos = mapClientPointToSuperContainer(new Point2D(event.clientX, event.clientY));
    let mousePos = new Point2D([event.clientX, event.clientY]);
    // mouseState.applyPressEvent(event);
    appActions.updateMouseState(pamet.appViewState, {
      positionOnPress: mousePos,
      buttons: event.buttons
    });

    if (event.button === 0) { // left mouse
      if (this.pageVS.mode === PageMode.None) {
        let realClickPos = this.pageVS.viewport.unprojectPoint(mousePos)
        // Resize related
        // Get noteVS whose riseze circle is clicked if any
        let resizedNoteVS = this.pageVS.resizeCircleAt(realClickPos)
        if (resizedNoteVS) {
          // If the note is not selected - deselect all and select it
          if (!this.pageVS.selectedElementsVS.has(resizedNoteVS)) {
            pageActions.clearSelection(this.pageVS)
            pageActions.updateSelection(this.pageVS, new Map([[resizedNoteVS, true]]))
          }
          // Start resize mode
          noteActions.startNotesResize(this.pageVS, resizedNoteVS, mousePos);
        }
      } else if (this.pageVS.mode === PageMode.CreateArrow) {
        arrowActions.arrowCreationClick(this.pageVS, mousePos);
      }
    } else if (event.button === 2) { // right mouse
    }
    log.info('[handleMouseDown] Mouse down: ', mousePos.x, mousePos.y)

  }

  handleMouseUp = (event: MouseEvent) => {
    let mousePos = new Point2D([event.clientX, event.clientY]);

    let pressPos = this.mouseState.positionOnPress;
    let realPos = this.pageVS.viewport.unprojectPoint(mousePos);
    let ctrlPressed = event.ctrlKey;
    let shiftPressed = event.shiftKey;

    let elementUnderMouse: ElementViewState | null = this.pageVS.arrowViewStateAt(realPos)
    let noteVS_underMouse = this.pageVS.noteViewStateAt(realPos)
    if (noteVS_underMouse !== null) {
      elementUnderMouse = noteVS_underMouse;
    }

    console.log('Mouse up', PageMode[this.pageVS.mode], 'button', event.button, elementUnderMouse)

    appActions.updateMouseState(pamet.appViewState, {
      buttons: event.buttons
    });

    if (event.button === 0) { // Left press (different from the .buttons left button index, because fu)
      console.log()
      if (this.pageVS.mode === PageMode.None) {
        if (ctrlPressed && !shiftPressed) { // Toggle selection
          if (elementUnderMouse !== null) {
            let nvs_selected = this.pageVS.selectedElementsVS.has(elementUnderMouse);
            pageActions.updateSelection(this.pageVS, new Map([[elementUnderMouse, !nvs_selected]]));
          }
        } else if (shiftPressed || (ctrlPressed && shiftPressed)) { // Add to selection
          if (elementUnderMouse !== null) {
            let nvs_selected = this.pageVS.selectedElementsVS.has(elementUnderMouse);
            if (!nvs_selected) {
              pageActions.updateSelection(this.pageVS, new Map([[elementUnderMouse, true]]));

            }
          }
        }

        if (!ctrlPressed && !shiftPressed) {
          // Clear selection (or reduce it to the note under the mouse)
          pageActions.clearSelection(this.pageVS);
          if (elementUnderMouse !== null) {
            let selectionMap = new Map([[elementUnderMouse, true]]);
            pageActions.updateSelection(this.pageVS, selectionMap);
          }
        }
      }

      else if (this.pageVS.mode === PageMode.DragNavigation) {
        pageActions.endDragNavigation(this.pageVS);
      } else if (this.pageVS.mode === PageMode.DragSelection) {
        pageActions.endDragSelection(this.pageVS);
      } else if (this.pageVS.mode === PageMode.DraggingEditWindow) {
        pageActions.endEditWindowDrag(this.pageVS);
      } else if (this.pageVS.mode === PageMode.ArrowControlPointDrag) {
        arrowActions.endControlPointDrag(this.pageVS, mousePos);
      } else if (this.pageVS.mode === PageMode.NoteResize) {
        noteActions.endNotesResize(this.pageVS, mousePos);
      } else if (this.pageVS.mode === PageMode.MoveElements) {
        noteActions.endElementsMove(this.pageVS, mousePos);
      }
    }
    if (event.button === 2) { // Right press
      if (this.pageVS.mode === PageMode.DragNavigation) {
        pageActions.endDragNavigation(this.pageVS);
      }

      // If it's a click - show context menu
      if (pressPos && mousePos.equals(pressPos)) {
        alert('Context menu not implemented yet')
      }
    }
  }

  handleMouseMove = (event: MouseEvent) => {
    let mousePos = new Point2D([event.clientX, event.clientY]);
    let pressPos = this.mouseState.positionOnPress;
    let delta = new Point2D([0, 0]); // This is for type safety mostly. When the delta is used surely the pressPos will be defined
    if (pressPos) {
      delta = pressPos.subtract(mousePos);
    }
    // state.renderId++;
    // pamet.renderProfiler.addRenderId(state.renderId)
    // log.info('[handleMouseMove] Mouse move: ', mousePos.x, mousePos.y, 'delta:', delta.x, delta.y)
    appActions.updateMouseState(pamet.appViewState, {
      position: mousePos,
    });

    if (this.pageVS.mode === PageMode.None) {
      if (this.mouseState.rightIsPressed) {
        pageActions.startDragNavigation(this.pageVS)
        pageActions.dragNavigationMove(this.pageVS, delta)
        this.navDeviceAutoSwitcher.registerRightMouseDrag(new Point2D([event.movementX, event.movementY]));
      } else if (this.mouseState.leftIsPressed) {
        console.log('Mouse move', PageMode[this.pageVS.mode], 'left button')
        if (!pressPos) {
          throw Error('Button pressed, but press pos not defined. This should not happen')
        }
        // If a single arrow is selected - its control points are visible
        // If the user drags a suggested control point - we create it
        // In any case - we start the arrow control point drag
        let editableArrow = this.pageVS.arrowVS_withVisibleControlPoints()
        if (editableArrow !== null) {
          // Check if we've clicked on an arrow control point
          // Go through all arrows

          let realPressPos = this.pageVS.viewport.unprojectPoint(pressPos);
          let controlPointIndex = editableArrow.controlPointAt(realPressPos);
          if (controlPointIndex !== null) {
            if (controlPointIndex % 1 !== 0) {
              // Whole indices are control points (.5 are suggested ones)
              arrowActions.createControlPointAndStartDrag(this.pageVS, realPressPos, controlPointIndex);
            } else {
              // Dragging an existing control point
              arrowActions.startControlPointDrag(this.pageVS, controlPointIndex);
            }
            // Update the drag position
            arrowActions.controlPointDragMove(this.pageVS, mousePos);
            return;  // If user clicked on a control point - don't do anythin else
          }
        }

        // If there was a note on the initial position - select and move it
        let noteVS_underMouse = this.pageVS.noteViewStateAt(this.pageVS.viewport.unprojectPoint(pressPos))
        let arrowVS_underMouse = this.pageVS.arrowViewStateAt(this.pageVS.viewport.unprojectPoint(pressPos))
        let elementUnderMouse = noteVS_underMouse || arrowVS_underMouse;
        if (elementUnderMouse !== null) {
          if (!this.pageVS.selectedElementsVS.has(elementUnderMouse)) {
            pageActions.clearSelection(this.pageVS)
            pageActions.updateSelection(this.pageVS, new Map([[elementUnderMouse, true]]))
          }
          noteActions.startMovingElements(this.pageVS, pressPos);
          noteActions.elementsMoveUpdate(this.pageVS, mousePos);
        } else {
          // If there was no note under the mouse - start drag selection
          pageActions.clearSelection(this.pageVS);
          pageActions.startDragSelection(this.pageVS, pressPos);
          pageActions.updateDragSelection(this.pageVS, mousePos);
        }
      }
    } else if (this.pageVS.mode === PageMode.DragNavigation) {
      pageActions.dragNavigationMove(this.pageVS, delta);
    } else if (this.pageVS.mode === PageMode.DragSelection) {
      pageActions.updateDragSelection(this.pageVS, mousePos);
    } else if (this.pageVS.mode === PageMode.DraggingEditWindow) {
      pageActions.updateEditWindowDrag(this.pageVS, mousePos);
    } else if (this.pageVS.mode === PageMode.ArrowControlPointDrag) {
      arrowActions.controlPointDragMove(this.pageVS, mousePos);
    } else if (this.pageVS.mode === PageMode.NoteResize) {
      noteActions.notesResizeMove(this.pageVS, mousePos);
    } else if (this.pageVS.mode === PageMode.MoveElements) {
      noteActions.elementsMoveUpdate(this.pageVS, mousePos);
    }
  }

  handleDoubleClick = (event: MouseEvent) => {
    let mousePos = new Point2D([event.clientX, event.clientY]);
    let realPos = this.pageVS.viewport.unprojectPoint(mousePos);

    // If an arrow is selected and a control point is under the mouse - delete it
    let editableArrowVS = this.pageVS.arrowVS_withVisibleControlPoints()
    if (editableArrowVS !== null) {
      let controlPointIndex = editableArrowVS.controlPointAt(realPos);
      // Whole indices are control points (.5 are suggested ones)
      if (controlPointIndex !== null && controlPointIndex % 1 === 0) {
        arrowActions.deleteControlPoint(editableArrowVS, controlPointIndex);
        return;
      }
    }

    let noteVS_underMouse = this.pageVS.noteViewStateAt(realPos)
    if (noteVS_underMouse !== null) {
      // If it's a link note - open the link
      let note = noteVS_underMouse.note();
      // For an internal link - follow it
      if (note instanceof CardNote && note.hasInternalPageLink) {
        let targetPage: Page | undefined;
        let targetPageId = note.internalLinkRoute()?.pageId;
        if (targetPageId !== undefined) {
          targetPage = pamet.page(targetPageId)
        }
        if (targetPage !== undefined) {
          appActions.setCurrentPage(pamet.appViewState, targetPage.id)
          return;
        }
      }
      // For an external link - open in new tab
      if (note instanceof CardNote && note.hasExternalLink) {
        log.info('Opening external link note:', note.content.url);
        let url = note.content.url;
        if (!url?.startsWith('http://') && !url?.startsWith('https://')) {
          url = '//' + url;
        }
        window.open(url, '_blank');
        return;
      }
      pageActions.startEditingNote(this.pageVS, noteVS_underMouse.note());
    } else {
      let realMousePos = this.pageVS.viewport.unprojectPoint(mousePos);
      pageActions.startNoteCreation(this.pageVS, realMousePos);
    }
  }

  handleWheel = (event: WheelEvent) => {
    // If the event is happening in a scrollable element that is not the page view,
    // don't do anything.. There's probably a more elegant way, but ok.
    let target = event.target as HTMLElement;
    if (target.closest('.page-view') !== this.superContainerRef.current) {
      return;
    }

    event.preventDefault();
    this.navDeviceAutoSwitcher.registerScrollEvent(new Point2D([event.deltaX, event.deltaY]));

    let new_height = this.pageVS.viewportHeight * Math.exp((event.deltaY / 120) * 0.1);
    new_height = Math.max(
      MIN_HEIGHT_SCALE,
      Math.min(new_height, MAX_HEIGHT_SCALE))

    let mousePos = new Point2D([event.clientX, event.clientY]);

    // console.log(mouse_pos)
    let mouse_pos_unproj = this.pageVS.viewport.unprojectPoint(mousePos)

    if (this.navDeviceAutoSwitcher.device === NavigationDevice.MOUSE) {
      let new_center = this.pageVS.viewportCenter.add(
        mouse_pos_unproj.subtract(this.pageVS.viewportCenter).multiply(
          1 - new_height / this.pageVS.viewportHeight))

      pageActions.updateViewport(this.pageVS, new_center, new_height);
    } else if (this.navDeviceAutoSwitcher.device === NavigationDevice.TOUCHPAD) {
      let delta = new Point2D([event.deltaX, event.deltaY]);
      let newViewportCenter = this.pageVS.viewportCenter.add(delta.divide(this.pageVS.viewport.heightScaleFactor()));
      pageActions.updateViewport(this.pageVS, newViewportCenter, this.pageVS.viewportHeight);
    }
  }

  bindEvents(canvas: HTMLCanvasElement) {
    const el = this.superContainerRef.current;
    if (!el) {
      throw new Error('superContainerRef is null');
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Could not get 2d context from canvas');
    }
    this._renderer = new CanvasPageRenderer(ctx, this.pageVS);


    this.mobxReactionRegistration = reaction(() => {
      // For creating notes - we need to list them to detect the change in references
      // Manual testing shows this to have minimal overhead
      let notes = Array.from(this.pageVS.noteViewStatesById.values())
      let arrows = Array.from(this.pageVS.arrowViewStatesById.values())

      // Trigger rendering if the mouse pos has changed AND it's
      // in a mode where that's significant.
      let mousePosIfRelevant: Point2D | null = null;
      if ([PageMode.DragNavigation,
      PageMode.DragSelection,
      PageMode.ArrowControlPointDrag,
      PageMode.MoveElements,
      PageMode.NoteResize,
      PageMode.CreateArrow].includes(this.pageVS.mode)) {
        mousePosIfRelevant = this.mouseState.position;
      } else {
        mousePosIfRelevant = null;
      }

      // pamet.renderProfiler.setMobxReaction(this.state.renderId!);
      // pamet.renderProfiler.logTimeSinceMouseMove('Mobx reaction', this.state.renderId!)

      // Trigger on changes in all of the below
      return {
        viewport: this.pageVS.viewportCenter,
        viewportHeight: this.pageVS.viewportHeight,
        viewportGeometry: this.pageVS.viewportGeometry,
        selectedElements: this.pageVS.selectedElementsVS.values(),
        dragSelectionRectData: this.pageVS.dragSelectionRectData,
        mode: this.pageVS.mode,
        dragSelectedElements: this.pageVS.dragSelectedElementsVS,
        notes: notes,
        arrows: arrows,
        mousePosIfRelevant: mousePosIfRelevant,
      }
    },
      () => {
        try {
          log.info('RENDEIRNG REACTION', this.pageVS.viewportCenter, pamet.appViewState.currentPageViewState?.viewportCenter)
          this._renderer?.renderCurrentPage();
        } catch (e) {
          log.error('Error rendering page:', e)
        }
      });

    el.addEventListener('mouseleave', this.handleMouseLeave);
    el.addEventListener('mouseenter', this.handleMouseEnter);
    el.addEventListener('mousedown', this.handleMouseDown);
    el.addEventListener('mouseup', this.handleMouseUp);
    el.addEventListener('mousemove', this.handleMouseMove);
    el.addEventListener('dblclick', this.handleDoubleClick);
    el.addEventListener('wheel', this.handleWheel, { passive: false });
  }

  unbindEvents() {
    log.info('Unbinding events from PageViewController')
    const el = this.superContainerRef.current;
    if (!el) {
      // If the element is gone, the events are also gone
      return;
    }

    if (this.mobxReactionRegistration) {
      this.mobxReactionRegistration();
      this.mobxReactionRegistration = undefined;
    }

    el.removeEventListener('mouseleave', this.handleMouseLeave);
    el.removeEventListener('mouseenter', this.handleMouseEnter);
    el.removeEventListener('mousedown', this.handleMouseDown);
    el.removeEventListener('mouseup', this.handleMouseUp);
    el.removeEventListener('mousemove', this.handleMouseMove);
    el.removeEventListener('dblclick', this.handleDoubleClick);
    el.removeEventListener('wheel', this.handleWheel);
  }
}

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

  // Stable controller instance
  const controllerRef = useRef<PageController | null>(null);
  if (!controllerRef.current) {
    controllerRef.current = new PageController(state, mouseState, superContainerRef);
  }
  const controller = controllerRef.current;

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
  }, [state, mouseState, superContainerRef, controller]);

  // Connect the canvas elements to paper.js and the DirectRenderer respectively
  useEffect(() => {
    const paperCanvas = paperCanvasRef.current;
    if (paperCanvas !== null) {
      paper.setup(paperCanvas);
      paper.view.autoUpdate = false;
    } else {
      log.error("[useEffect] paperCanvas is null")
    }
  }, [state, paperCanvasRef]);

  /**
   * Setup geometry update handling on resize
   * The viewport calculations need the window geometry info
   * And the canvas width/height attributes need to be correct for the rendering
   * to be accurate
   */
  const updateGeometryHandler = useCallback(() => {
    let container = superContainerRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!container || !canvas || !ctx) {
      log.error("[updateGeometry] superContainerRef, canvasRef or ctx is null")
      return;
    }
    let boundingRect = container.getBoundingClientRect();

    // Adjust for device pixel ratio, otherwise small objects will be blurry
    let dpr = window.devicePixelRatio || 1;  // How many of the screen's actual pixels should be used to draw a single CSS pixel
    // Set the canvas size in real coordinates
    canvas.width = boundingRect.width * dpr;
    canvas.height = boundingRect.height * dpr;

    // Update viewport geometry
    pageActions.updateGeometry(
      state,
      [boundingRect.left, boundingRect.top, boundingRect.width, boundingRect.height]);

  }, [state, superContainerRef]);

  useEffect(() => {
    // Watch for resize events and update the geometry accordingly
    let container = superContainerRef.current;
    if (container === null) {
      log.error("[updateGeometry] superContainerRef is null")
      return;
    }

    const resizeObserver = new ResizeObserver(updateGeometryHandler);
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [updateGeometryHandler, superContainerRef]);


  // // Setup the rendering mobx reaction. We access the data that on change should
  // // trigger the rendering reaction
  // useEffect(() => {
  //   // const ctx = canvasRef.current?.getContext('2d')
  //   // if (!ctx) {
  //   //   log.error("[useEffect] canvas context is null")
  //   //   return;
  //   // }

  //   const renderDisposer = reaction(() => {
  //     // For creating notes - we need to list them to detect the change in references
  //     // Manual testing shows this to have minimal overhead
  //     let notes = Array.from(state.noteViewStatesById.values())
  //     let arrows = Array.from(state.arrowViewStatesById.values())

  //     // Trigger rendering if the mouse pos has changed AND it's
  //     // in a mode where that's significant.
  //     let mousePosIfRelevant: Point2D | null = null;
  //     if ([PageMode.DragNavigation,
  //     PageMode.DragSelection,
  //     PageMode.ArrowControlPointDrag,
  //     PageMode.MoveElements,
  //     PageMode.NoteResize,
  //     PageMode.CreateArrow].includes(state.mode)) {
  //       mousePosIfRelevant = mouseState.position;
  //     } else {
  //       mousePosIfRelevant = null;
  //     }

  //     // pamet.renderProfiler.setMobxReaction(state.renderId!);
  //     // pamet.renderProfiler.logTimeSinceMouseMove('Mobx reaction', state.renderId!)

  //     // Trigger on changes in all of the below
  //     return {
  //       viewport: state.viewportCenter,
  //       viewportHeight: state.viewportHeight,
  //       viewportGeometry: state.viewportGeometry,
  //       selectedElements: state.selectedElementsVS.values(),
  //       dragSelectionRectData: state.dragSelectionRectData,
  //       mode: state.mode,
  //       dragSelectedElements: state.dragSelectedElementsVS,
  //       notes: notes,
  //       arrows: arrows,
  //       mousePosIfRelevant: mousePosIfRelevant,
  //     }
  //   },
  //     () => {
  //       try {
  //         log.info('RENDEIRNG REACTION')
  //         pamet.pageRenderer.renderCurrentPage();
  //       } catch (e) {
  //         log.error('Error rendering page:', e)
  //       }
  //     });

  //   return () => {
  //     renderDisposer();
  //   }
  // }, [state, mouseState]);

  // Mouse event handlers

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
  log.info('REACT Rendering PageView', state.viewportCenter, pamet.appViewState.currentPageViewState?.viewportCenter)
  // We'll crate hidden img elements for notes with images and use them in the
  // canvas renderer
  let imageUrls: Set<string> = new Set(state.mediaUrlsByItemId.values());

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
      onContextMenu={(event) => { event.preventDefault() }}
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
              log.error('Image load error', event, url)
            }}
          />
        ))}

    </main>
  );
});
