import React, { useState, useEffect, useRef, useMemo, useCallback, useContext } from 'react';
import styled from 'styled-components';

import { NoteData } from '../types/Note';
import { ArrowData } from '../types/Arrow';
import { MapPageData } from '../types/MapPage';
import { NoteComponent } from './note/Note';
import { DEFAULT_BACKGROUND_COLOR, DEFAULT_EYE_HEIGHT, DEFAULT_TEXT_COLOR, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE } from '../constants';
import { Point2D } from '../util/Point2D';
import { Geometry, Viewport } from './Viewport';
import { MapController } from '../controllers/MapController';
import { Note } from '../model/Note';
import { ArrowComponent, ArrowHeadComponent } from './Arrow';
type Status = 'loading' | 'error' | 'loaded';

export const MapContainer = styled.div`
--map-scale: ${1 / DEFAULT_EYE_HEIGHT};
--map-translate-x: 0px;
--map-translate-y: 0px;
user-select: none;
width: 100%;
height: 100%;
transform:  scale(var(--map-scale)) translate(var(--map-translate-x), var(--map-translate-y)) translate(50vw, 50vh);
backface-visibility: hidden;
touch-action: none;
`;


interface PageProps {
  page: MapPageData;
}

const MapPageComponent = ({ page }: PageProps) => {
  // Get all notes from the /pamet_presentation-6d903c80.pam4.json file
  // and display them on the map, using reacts effect hook
  const [status, setStatus] = useState<Status>('loading');
  const [errorString, setErrorString] = useState<string>('');

  const [notesData, setNotesData] = useState<NoteData[]>([]);
  const [arrowsData, setArrowsData] = useState<ArrowData[]>([]);

  const [mousePos, setMousePos] = useState<Point2D>(new Point2D(0, 0));
  const [mouseDown, setMouseDown] = useState<boolean>(false);
  const [mousePosOnPress, setMousePosOnPress] = useState<Point2D>(new Point2D(0, 0));
  const [viewportCenterOnModeStart, setViewportCenterOnModeStart] = useState<Point2D>(new Point2D(0, 0));

  const [pinchStartDistance, setPinchStartDistance] = useState<number>(0);
  const [pinchInProgress, setPinchInProgress] = useState<boolean>(false);
  const [pinchStartViewportHeight, setPinchStartViewportHeight] = useState<number>(DEFAULT_EYE_HEIGHT);
  const [initialPinchCenter, setInitialPinchCenter] = useState<Point2D>(new Point2D(0, 0));

  const [geometry, setGeometry] = useState<Geometry>([
    0, 0, window.innerWidth, window.innerHeight]);
  const [viewportCenter, setViewportCenter] = useState<Point2D>(new Point2D(0, 0));
  const [viewportHeight, setViewportHeight] = useState<number>(DEFAULT_EYE_HEIGHT);
  const [selection, setSelection] = useState<Array<string>>([]);

  // const viewport = new Viewport(viewportCenter, viewportHeight, geometry)
  const viewport = useMemo(() => new Viewport(viewportCenter, viewportHeight, geometry),
    [viewportCenter, viewportHeight, geometry]);
  const container_ref = useRef<HTMLElement>()
  const controller = new MapController(selection, setSelection);

  // Update geometry on resize events
  useEffect(() => {
    const handleResize = () => {
      setGeometry([0, 0, window.innerWidth, window.innerHeight]);
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // Fetch notes
  useEffect(() => {
    const fetchData = async () => {
      try {
        // fetch children from /p/:id/children
        const response = await fetch('/p/' + page.id + '/children.json');
        const data: { notes: NoteData[], arrows: ArrowData[] } = await response.json();
        // Hacky way to add default colors to notes that don't have them
        // (they should normally be present in the JSON file)
        for (let note of data.notes) {
          if (note.style.color === undefined) {
            note.style.color = DEFAULT_TEXT_COLOR
          }
          if (note.style.background_color === undefined) {
            note.style.background_color = DEFAULT_BACKGROUND_COLOR
          }
        }

        // Populate the page_id and own_id fields (for convenience
        // will probably be removed)
        for (let note of data.notes) {
          // id = [page_id, own_id]
          note.page_id = note.id[0];
          note.own_id = note.id[1];
        }
        setNotesData(data.notes)
        setArrowsData(data.arrows)
        setStatus('loaded');
      } catch (error: any) {
        setStatus('error');
        setErrorString(error.message);
      }
    };

    fetchData();
  }, [page]);

  const updateViewport = useCallback(() => {
    // This css var can go in the MapContainer styled component ..?
    // But we'll still set it through javascript because of the stuttering
    // that happens when we set it through styled components
    // In that case we can probably use the ref hook to get the element
    let container = container_ref.current;
    if (container === undefined) {
      return;  // Yes, this happens
    } else {
      container.style.setProperty('--map-scale', `${1 / viewportHeight}`);
      container.style.setProperty('--map-translate-x', `${-viewportCenter.x}px`);
      container.style.setProperty('--map-translate-y', `${-viewportCenter.y}px`);
    }

  }, [viewportCenter, viewportHeight]);

  useEffect(() => {
    updateViewport();
  }, [viewportHeight, viewportCenter, updateViewport]);

  const copySelectedToClipboard = useCallback(() => {
    let selected_notes = notesData.filter((note) => selection.includes(note.id.toString()));
    let text = selected_notes.map((note) => note.content.text).join('\n\n');
    navigator.clipboard.writeText(text);
  }, [notesData, selection]);


  // Detect url anchor changes in order to update the viewport and note selection
  useEffect(() => {
    const handleHashChange = () => {
      // Schema /p/:id?eye_at=height/center_x/center_y&selection=note_id1,note_id2#note_id3
      let query = new URLSearchParams(window.location.search);
      let eye_at = query.get('eye_at');
      if (eye_at !== null) {
        let eye_at_params = eye_at.split('/');
        if (eye_at_params.length === 3) {
          let height = parseFloat(eye_at_params[0]);
          let center_x = parseFloat(eye_at_params[1]);
          let center_y = parseFloat(eye_at_params[2]);
          setViewportHeight(height);
          setViewportCenter(new Point2D(center_x, center_y));
        }
        // TODO: selection
      }
      let hash = window.location.hash;
      if (hash !== '') {
        let note_id = hash.slice(1);
        let noteData = notesData.find((note) => note.id.toString() === note_id);
        if (noteData !== undefined) {
          // Go to note center
          let note = new Note(noteData);
          setViewportCenter(note.rect.center());
        }
      };
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, [notesData]);

  const handleScroll = (event) => {
    let new_height = viewportHeight * Math.exp((event.deltaY / 120) * 0.1);
    new_height = Math.max(
      MIN_HEIGHT_SCALE,
      Math.min(new_height, MAX_HEIGHT_SCALE))

    // new_center = (current_center +
    //   (state.unproject_point(mouse_pos) - current_center) *
    //   (current_height / new_height - 1))
    let mouse_pos = new Point2D(event.clientX, event.clientY);
    let mouse_pos_unproj = viewport.unprojectPoint(mouse_pos)
    let new_center = viewportCenter.add(
      mouse_pos_unproj.subtract(viewportCenter).multiply(
        1 - new_height / viewportHeight))

    setViewportHeight(new_height);
    setViewportCenter(new_center);
  };

  const handleMouseDown = useCallback((event) => {
    setMouseDown(true);
    setMousePosOnPress(new Point2D(event.clientX, event.clientY));
    setViewportCenterOnModeStart(viewportCenter);
  }, [viewportCenter]);

  const handleTouchStart = useCallback((event) => {
    // Only for single finger touch
    if (event.touches.length === 1) {
      setMouseDown(true);
      setMousePosOnPress(new Point2D(event.touches[0].clientX, event.touches[0].clientY));
      setViewportCenterOnModeStart(viewportCenter);
    } else if (event.touches.length === 2) {
      setViewportCenterOnModeStart(viewportCenter);
      console.log('pinch start')
      let touch1 = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      let touch2 = new Point2D(event.touches[1].clientX, event.touches[1].clientY);
      let distance = touch1.distanceTo(touch2);
      setPinchStartDistance(distance);
      setPinchStartViewportHeight(viewportHeight);
      setPinchInProgress(true);
      let initPinchCenter = touch1.add(touch2).divide(2)
      setInitialPinchCenter(initPinchCenter);
      console.log('Initial pinch center', initPinchCenter)
    }
  }, [viewportCenter, viewportHeight]);

  const handleMouseMove = useCallback((event) => {
    let new_mouse_pos = new Point2D(event.clientX, event.clientY);
    setMousePos(new_mouse_pos);
    if (mouseDown) {
      let delta = mousePosOnPress.subtract(new_mouse_pos);
      let delta_unproj = delta.divide(viewport.heightScaleFactor());
      let new_center = viewportCenterOnModeStart.add(delta_unproj);
      setViewportCenter(new_center);
    }
  }, [mouseDown, mousePosOnPress, viewportCenterOnModeStart, viewport]);

  const handeTouchMove = useCallback((event) => {
    if (event.touches.length === 1) {
      let new_mouse_pos = new Point2D(event.touches[0].clientX, event.touches[0].clientY);
      setMousePos(new_mouse_pos);
      if (mouseDown) {
        let delta = mousePosOnPress.subtract(new_mouse_pos);
        let delta_unproj = delta.divide(viewport.heightScaleFactor());
        let new_center = viewportCenterOnModeStart.add(delta_unproj);
        setViewportCenter(new_center);
      }
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
        let delta_unproj = delta.divide(viewport.heightScaleFactor());
        let new_center = viewportCenterOnModeStart.add(delta_unproj);

        // Apply the correction to make the zoom focused on the pinch center
        // M - mouse pos (unprojected), C - viewport center. s - scale
        // M' = M * s, C' = C * s : M and C after the scale
        // V = (M - C) - (M' - C'): the vector of change for M
        // correction = - ( V ) = (M - C) - (M' - C') = (M - C) * (1 - s)
        let old_viewport = new Viewport(viewportCenterOnModeStart, pinchStartViewportHeight, geometry);
        let unprInitPinchCenter = old_viewport.unprojectPoint(initialPinchCenter);
        let focusDelta = unprInitPinchCenter.subtract(viewportCenterOnModeStart);
        let correction = focusDelta.multiply(
          1 - new_height / pinchStartViewportHeight);
        new_center = new_center.add(correction)

        setViewportHeight(new_height);
        setViewportCenter(new_center);
      }
    }
  }, [mouseDown, mousePosOnPress, viewportCenterOnModeStart, viewport, geometry,
    pinchStartViewportHeight, pinchStartDistance, pinchInProgress, initialPinchCenter]);

  const handleMouseUp = useCallback((event) => {
    setMouseDown(false);
  }, []);

  const handleTouchEnd = useCallback((event) => {
    setMouseDown(false);
    setPinchInProgress(false);
  }, []);

  const handleClick = (event) => {
    // let mouse_pos = new Point2D(event.clientX, event.clientY);
    if (event.target === event.currentTarget &&
      !(event.shiftKey || event.ctrlKey)) {
      controller.clearSelection();
    }
  };

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


  // Rendering phase
  if (status === 'loading') {
    return <p>Loading...</p>;
  }

  if (status === 'error') {
    return <p>Error loading data. Message: {errorString}</p>;
  }

  // TODO: setup min/max viewport position.
  let vb_x = -100000;
  let vb_y = -100000;
  let vb_width = 200000;
  let vb_height = 200000;

  return (
    <div
      style={{ width: '100%', height: '100%', overflow: 'hidden', touchAction: 'none' }}
      onWheel={handleScroll}
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
      onMouseUp={handleMouseUp}
      onTouchEnd={handleTouchEnd}
      onMouseMove={handleMouseMove}
      onTouchMove={handeTouchMove}
      onClick={handleClick}
    >
      {/* This second onClick is hacky - I should check for a note under the
      mouse instad (to handle the cases when the click is on the MapContainer*/}
      <MapContainer ref={container_ref} onClick={handleClick}>
        {notesData.map((noteData) => (
          <NoteComponent
            key={noteData.id}
            noteData={noteData}
            selected={selection.includes(noteData.own_id)}
            mapController={controller} />
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
            {arrowsData.map((arrowData) => (
              <ArrowHeadComponent key={arrowData.id} arrowData={arrowData} />
            ))}
          </defs>
          {arrowsData.map((arrowData) => (
            <ArrowComponent
              key={arrowData.id}
              arrowData={arrowData}
            />
          ))}


          {/* debug touch positions. draw a circle at the pinchCenter */}
        </svg>
      </MapContainer>

    </div>
  );
};

export default MapPageComponent;
