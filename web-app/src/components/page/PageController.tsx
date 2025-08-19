import { appActions } from '@/actions/app';
import { arrowActions } from '@/actions/arrow';
import { noteActions } from '@/actions/note';
import { pageActions } from '@/actions/page';
import { DirectRenderer } from '@/components/page/DirectRenderer';
import { ElementViewState } from '@/components/page/ElementViewState';
import { NavigationDeviceAutoSwitcher, NavigationDevice } from '@/components/page/NavigationDeviceAutoSwitcher';
import { PageViewState, PageMode } from '@/components/page/PageViewState';
import { MouseState } from '@/containers/app/WebAppState';
import { MIN_HEIGHT_SCALE, MAX_HEIGHT_SCALE, DEFAULT_EYE_HEIGHT } from '@/core/constants';
import { pamet } from '@/core/facade';
import { CardNote } from '@/model/CardNote';
import { Page } from '@/model/Page';
import { Viewport } from '@/components/page/Viewport';
import { Point2D } from 'fusion/primitives/Point2D';
import { reaction } from 'mobx';
import { getLogger } from 'fusion/logging';
import React from 'react';

const log = getLogger('PageController');



export class PageController {
  navDeviceAutoSwitcher: NavigationDeviceAutoSwitcher = new NavigationDeviceAutoSwitcher();
  private pageVS: PageViewState;
  private mouseState: MouseState;
  private superContainerRef: React.RefObject<HTMLDivElement>;
  private mobxReactionRegistration?: () => void;
  private _renderer?: DirectRenderer;
  private resizeObserver?: ResizeObserver;

  // Touch / pinch state
  private pinchStartDistance: number = 0;
  private pinchInProgress: boolean = false;
  private pinchStartViewportHeight: number = DEFAULT_EYE_HEIGHT;
  private initialPinchCenter: Point2D = new Point2D([0, 0]);

  public get renderer(): DirectRenderer | undefined {
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

  public setupResizeObserver(canvas: HTMLCanvasElement) {
    const container = this.superContainerRef.current;
    if (!container) {
        throw new Error('superContainerRef is null');
    }

    const compute = () => {
        let boundingRect = container.getBoundingClientRect();

        // Adjust for device pixel ratio
        let dpr = window.devicePixelRatio || 1;
        canvas.width = boundingRect.width * dpr;
        canvas.height = boundingRect.height * dpr;

        // Update viewport geometry
        pageActions.updateGeometry(
            this.pageVS,
            [boundingRect.left, boundingRect.top, boundingRect.width, boundingRect.height]
        );
    };

    this.resizeObserver = new ResizeObserver(() => {
        compute();
    });

    // Initialize immediately so canvas and viewport are correct before first resize callback
    compute();

    this.resizeObserver.observe(container);
  }

  handleMouseLeave = (event: MouseEvent) => {
    // Clear the mode (for most modes), to avoid weird behavior
    // currently those are not implemented actually
    appActions.updateMouseState(pamet.appViewState, {
      position: null,
      buttonsOnLeave: event.buttons,
    });
  };

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
      log.info('Mouse buttons released off-window. Clearing mode');
      pageActions.clearMode(this.pageVS);
      appActions.updateMouseState(pamet.appViewState, {
        buttons: 0
      });
    }
  };

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
        let realClickPos = this.pageVS.viewport.unprojectPoint(mousePos);
        // Resize related
        // Get noteVS whose riseze circle is clicked if any
        let resizedNoteVS = this.pageVS.resizeCircleAt(realClickPos);
        if (resizedNoteVS) {
          // If the note is not selected - deselect all and select it
          if (!this.pageVS.selectedElementsVS.has(resizedNoteVS)) {
            pageActions.clearSelection(this.pageVS);
            pageActions.updateSelection(this.pageVS, new Map([[resizedNoteVS, true]]));
          }
          // Start resize mode
          noteActions.startNotesResize(this.pageVS, resizedNoteVS, mousePos);
        }
      } else if (this.pageVS.mode === PageMode.CreateArrow) {
        arrowActions.arrowCreationClick(this.pageVS, mousePos);
      }
    } else if (event.button === 2) { // right mouse
    }
    log.info('[handleMouseDown] Mouse down: ', mousePos.x, mousePos.y);

  };

  handleMouseUp = (event: MouseEvent) => {
    let mousePos = new Point2D([event.clientX, event.clientY]);

    let pressPos = this.mouseState.positionOnPress;
    let realPos = this.pageVS.viewport.unprojectPoint(mousePos);
    let ctrlPressed = event.ctrlKey;
    let shiftPressed = event.shiftKey;

    let elementUnderMouse: ElementViewState | null = this.pageVS.arrowViewStateAt(realPos);
    let noteVS_underMouse = this.pageVS.noteViewStateAt(realPos);
    if (noteVS_underMouse !== null) {
      elementUnderMouse = noteVS_underMouse;
    }

    console.log('Mouse up', PageMode[this.pageVS.mode], 'button', event.button, elementUnderMouse);

    appActions.updateMouseState(pamet.appViewState, {
      buttons: event.buttons
    });

    if (event.button === 0) { // Left press (different from the .buttons left button index, because fu)
      console.log();
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
        alert('Context menu not implemented yet');
      }
    }
  };

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
        pageActions.startDragNavigation(this.pageVS);
        pageActions.dragNavigationMove(this.pageVS, delta);
        this.navDeviceAutoSwitcher.registerRightMouseDrag(new Point2D([event.movementX, event.movementY]));
      } else if (this.mouseState.leftIsPressed) {
        console.log('Mouse move', PageMode[this.pageVS.mode], 'left button');
        if (!pressPos) {
          throw Error('Button pressed, but press pos not defined. This should not happen');
        }
        // If a single arrow is selected - its control points are visible
        // If the user drags a suggested control point - we create it
        // In any case - we start the arrow control point drag
        let editableArrow = this.pageVS.arrowVS_withVisibleControlPoints();
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
            return; // If user clicked on a control point - don't do anythin else
          }
        }

        // If there was a note on the initial position - select and move it
        let noteVS_underMouse = this.pageVS.noteViewStateAt(this.pageVS.viewport.unprojectPoint(pressPos));
        let arrowVS_underMouse = this.pageVS.arrowViewStateAt(this.pageVS.viewport.unprojectPoint(pressPos));
        let elementUnderMouse = noteVS_underMouse || arrowVS_underMouse;
        if (elementUnderMouse !== null) {
          if (!this.pageVS.selectedElementsVS.has(elementUnderMouse)) {
            pageActions.clearSelection(this.pageVS);
            pageActions.updateSelection(this.pageVS, new Map([[elementUnderMouse, true]]));
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
  };

  handleDoubleClick = (event: MouseEvent) => {
    let mousePos = new Point2D([event.clientX, event.clientY]);
    let realPos = this.pageVS.viewport.unprojectPoint(mousePos);

    // If an arrow is selected and a control point is under the mouse - delete it
    let editableArrowVS = this.pageVS.arrowVS_withVisibleControlPoints();
    if (editableArrowVS !== null) {
      let controlPointIndex = editableArrowVS.controlPointAt(realPos);
      // Whole indices are control points (.5 are suggested ones)
      if (controlPointIndex !== null && controlPointIndex % 1 === 0) {
        arrowActions.deleteControlPoint(editableArrowVS, controlPointIndex);
        return;
      }
    }

    let noteVS_underMouse = this.pageVS.noteViewStateAt(realPos);
    if (noteVS_underMouse !== null) {
      // If it's a link note - open the link
      let note = noteVS_underMouse.note();
      // For an internal link - follow it
      if (note instanceof CardNote && note.hasInternalPageLink) {
        let targetPage: Page | undefined;
        let targetPageId = note.internalLinkRoute()?.pageId;
        if (targetPageId !== undefined) {
          targetPage = pamet.page(targetPageId);
        }
        if (targetPage !== undefined) {
          appActions.setCurrentPage(pamet.appViewState, targetPage.id);
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
  };

  handleContextMenu = (event: MouseEvent) => {
    event.preventDefault();
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
      Math.min(new_height, MAX_HEIGHT_SCALE));

    let mousePos = new Point2D([event.clientX, event.clientY]);

    // console.log(mouse_pos)
    let mouse_pos_unproj = this.pageVS.viewport.unprojectPoint(mousePos);

    if (this.navDeviceAutoSwitcher.device === NavigationDevice.MOUSE) {
      let new_center = this.pageVS.viewportCenter.add(
        mouse_pos_unproj.subtract(this.pageVS.viewportCenter).multiply(
          1 - new_height / this.pageVS.viewportHeight));

      pageActions.updateViewport(this.pageVS, new_center, new_height);
    } else if (this.navDeviceAutoSwitcher.device === NavigationDevice.TOUCHPAD) {
      let delta = new Point2D([event.deltaX, event.deltaY]);
      let newViewportCenter = this.pageVS.viewportCenter.add(delta.divide(this.pageVS.viewport.heightScaleFactor()));
      pageActions.updateViewport(this.pageVS, newViewportCenter, this.pageVS.viewportHeight);
    }
  };

  // Touch handlers (ported from PageView)
  handleTouchStart = (event: TouchEvent) => {
    if (event.touches.length === 1) {
      const touchPos = new Point2D([event.touches[0].clientX, event.touches[0].clientY]);
      appActions.updateMouseState(pamet.appViewState, { positionOnPress: touchPos });
      pageActions.startDragSelection(this.pageVS, touchPos);
    } else if (event.touches.length === 2) {
      const touch1 = new Point2D([event.touches[0].clientX, event.touches[0].clientY]);
      const touch2 = new Point2D([event.touches[1].clientX, event.touches[1].clientY]);
      const distance = touch1.distanceTo(touch2);
      const initPinchCenter = touch1.add(touch2).divide(2);

      this.pinchStartDistance = distance;
      this.pinchStartViewportHeight = this.pageVS.viewportHeight;
      this.pinchInProgress = true;
      this.initialPinchCenter = initPinchCenter;

      pageActions.startDragNavigation(this.pageVS);
    }
  };

  handleTouchMove = (event: TouchEvent) => {
    if (event.touches.length === 1) {
      const newTouchPos = new Point2D([event.touches[0].clientX, event.touches[0].clientY]);
      pageActions.updateDragSelection(this.pageVS, newTouchPos);
    } else if (event.touches.length === 2) {
      const touch1 = new Point2D([event.touches[0].clientX, event.touches[0].clientY]);
      const touch2 = new Point2D([event.touches[1].clientX, event.touches[1].clientY]);

      if (this.pinchInProgress) {
        const distance = touch1.distanceTo(touch2);
        const newPinchCenter = touch1.add(touch2).divide(2);
        let new_height = this.pinchStartViewportHeight * (this.pinchStartDistance / distance);
        new_height = Math.max(MIN_HEIGHT_SCALE, Math.min(new_height, MAX_HEIGHT_SCALE));

        // Move the center according to the pinch center
        const delta = this.initialPinchCenter.subtract(newPinchCenter);
        const delta_unproj = delta.divide(this.pageVS.viewport.heightScaleFactor());
        let new_center = this.pageVS.viewportCenterOnModeStart.add(delta_unproj);

        // Apply correction to focus zoom at pinch center
        const old_viewport = new Viewport(this.pageVS.viewportGeometry, this.pinchStartViewportHeight);
        old_viewport.moveRealCenterTo(this.pageVS.viewportCenterOnModeStart);
        const unprInitPinchCenter = old_viewport.unprojectPoint(this.initialPinchCenter);
        const focusDelta = unprInitPinchCenter.subtract(this.pageVS.viewportCenterOnModeStart);
        const correction = focusDelta.multiply(1 - new_height / this.pinchStartViewportHeight);
        new_center = new_center.add(correction);

        pageActions.updateViewport(this.pageVS, new_center, new_height);
      }
    }
  };

  handleTouchEnd = (_event: TouchEvent) => {
    if (this.pageVS.mode === PageMode.DragNavigation) {
      pageActions.endDragNavigation(this.pageVS);
    }
    this.pinchInProgress = false;
  };
  bindEvents(canvas: HTMLCanvasElement) {
    log.info('Binding events to PageViewController');
    this.setupResizeObserver(canvas);
    const el = this.superContainerRef.current;
    if (!el) {
      throw new Error('superContainerRef is null');
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Could not get 2d context from canvas');
    }
    this._renderer = new DirectRenderer(ctx, this.pageVS);


    this.mobxReactionRegistration = reaction(() => {
      // For creating notes - we need to list them to detect the change in references
      // Manual testing shows this to have minimal overhead
      let notes = Array.from(this.pageVS.noteViewStatesById.values());
      let arrows = Array.from(this.pageVS.arrowViewStatesById.values());

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
      };
    },
      () => {
        try {
          this._renderer?.renderCurrentPage();
        } catch (e) {
          log.error('Error rendering page:', e);
        }
      }
    );

    // Mouse events
    el.addEventListener('mouseleave', this.handleMouseLeave);
    el.addEventListener('mouseenter', this.handleMouseEnter);
    el.addEventListener('mousedown', this.handleMouseDown);
    el.addEventListener('mouseup', this.handleMouseUp);
    el.addEventListener('mousemove', this.handleMouseMove);
    el.addEventListener('dblclick', this.handleDoubleClick);
    el.addEventListener('wheel', this.handleWheel, { passive: false });
    el.addEventListener('contextmenu', this.handleContextMenu);

    // Touch events (pinch + drag-selection)
    el.addEventListener('touchstart', this.handleTouchStart, { passive: true });
    el.addEventListener('touchmove', this.handleTouchMove, { passive: true });
    el.addEventListener('touchend', this.handleTouchEnd);
  }

  unbindEvents() {
    this.resizeObserver?.disconnect();
    log.info('Unbinding events from PageViewController');

    // Always dispose reaction and renderer, even if element is already gone
    if (this.mobxReactionRegistration) {
      this.mobxReactionRegistration();
      this.mobxReactionRegistration = undefined;
    }
    this._renderer?.dispose();
    this._renderer = undefined;

    const el = this.superContainerRef.current;
    if (!el) {
      // If the element is gone, the events are also gone
      return;
    }

    // Mouse
    el.removeEventListener('mouseleave', this.handleMouseLeave);
    el.removeEventListener('mouseenter', this.handleMouseEnter);
    el.removeEventListener('mousedown', this.handleMouseDown);
    el.removeEventListener('mouseup', this.handleMouseUp);
    el.removeEventListener('mousemove', this.handleMouseMove);
    el.removeEventListener('dblclick', this.handleDoubleClick);
    el.removeEventListener('wheel', this.handleWheel);
    el.removeEventListener('contextmenu', this.handleContextMenu);

    // Touch
    el.removeEventListener('touchstart', this.handleTouchStart);
    el.removeEventListener('touchmove', this.handleTouchMove);
    el.removeEventListener('touchend', this.handleTouchEnd);
  }
}
