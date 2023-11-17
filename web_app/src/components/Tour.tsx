// A component that takes a markdown string and divides it into segments divided
// by the links to the pamet page. They are displayed as a regular markdown file
// only with thin lines demarking the segments. (Formatting is broken if there's
// something around the links).
// There's a mark (circular element on the left side) that indicates the level for
// swithching segments (on scroll).
// Scrolling down initially moves the mark down (from 0 to the optimal focus level
// . Maybe 30-70% of the screen height), then holds in place until we reach the
// end of the page. Then it moves to the bottom (in order to focus the last
// segments).
// The links are e.g. pamet:/p/{page_id}/?eye_at={height}/{+}/{y}#note_id={}
// (and in markdown of course [text](link))

import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import styled from 'styled-components';
import { TourSegment } from '../model/Page';
import { parsePametUrl } from '../util';
import { mapActions } from '../actions/page';
import { PageViewState } from "./mapPage/PageViewState";


const MIN_SCROLL_BUFFER_POS = -100;
const MAX_SCROLL_BUFFER_POS = 100;
const PREFERED_FOCUS_LEVEL = 0.4;


interface TourComponentViewProps {
    segments: TourSegment[];
    parentPageViewState: PageViewState;
}

export const TourContainer = styled.div`
    // So absolute positioning of the mark works
    position: relative;
    display: flex;

    height: 100%;
    /* overflow: hidden; */
    flex-grow: 0;
    flex-shrink: 0;
    width: 800px;
    /* display: inline; */
    /* padding: 20px; */
    /* a left light gray border */
    border-left: 1px solid #e0e0e0;
    border-bottom: 1px solid #e0e0e0;

    @media (max-width: 1400px) {
        width: 600px
    }
    @media (max-width: 1024px) {
        width: 400px
    }
    @media (max-width: 768px) {
        width: 100%;
        height: 50%;
        min-width: 300px;
        /* font: 12px; */
    }
`;

const ScrollContainer = styled.div`
    /* position: relative; */
    /* display: flex; */
    overflow: auto;
    padding: 20px;
`;

export const SegmentContainer = styled.div`
    /* draw a light gray left border if props.active */
    border-left: 4px solid ${props => props.active ? '#e6e6e6' : 'transparent'};
    /* a very light gray bottom border */
    border-bottom: 1px solid #f0f0f0;
`

export const TourComponent = ({ segments, parentPageViewState }: TourComponentViewProps) => {
    let segmentRefs: React.RefObject<HTMLDivElement>[] = useMemo(() => {
        let refs: React.RefObject<HTMLDivElement>[] = [];
        for (let i = 0; i < segments.length; i++) {
            // console.log(segments[i]);
            // ref = useRef(null);
            refs.push(React.createRef());
        }
        return refs;
    }, [segments]);

    // Catch the scrodoubledoubledoublelling in order to change the mark position and active segment

    const [activeSegmentIdx, setActiveSegmentIdx] = React.useState(0);
    const [activationLevelPx, setActivationLevelPx] = React.useState(0);

    const [scrollTop, setScrollTop] = React.useState(0);
    const [clientHeight, setClientHeight] = React.useState(0);
    const [maxScrollTop, setMaxScrollTop] = React.useState(0);
    const [touchStartY, setTouchStartY] = React.useState(0);
    const [touchStartScrollTop, setTouchStartScrollTop] = React.useState(0);

    // We setup a scroll buffer in order to properly iterate small segments
    // in the beginning and the end of the page.
    // The scroll buffer can vary between -1 and 1. -1 initially. Then several
    // steps move the marker down. Then it holds in place until the end of the
    // page. Then it moves from 0 to 1 after we've reached the page bottom.
    const [scrollBufferPos, setScrollBufferPos] = React.useState(MIN_SCROLL_BUFFER_POS);

    const scrollContainerRef = useRef<HTMLDivElement>(null);

    // Update the scroll position on state change
    useEffect(() => {
        if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = scrollTop;
        }
    }, [scrollTop]);

    const scrollInContainer = useCallback((delta) => {

        const container = scrollContainerRef.current;
        if (!container) {
            return 0;
        }
        let remainder = 0;
        let newScrollTop = scrollTop + delta;
        if (newScrollTop < 0) {
            remainder = newScrollTop;
            newScrollTop = 0;
        }
        if (newScrollTop > maxScrollTop) {
            remainder = newScrollTop - maxScrollTop;
            newScrollTop = maxScrollTop;
        }
        setScrollTop(newScrollTop);
        // console.log('scrollInContainer', newScrollTop, 'for', delta)
        // console.log('maxScrollTop', maxScrollTop, 'scrollTop', scrollTop)
        return remainder;
    }, [scrollTop, maxScrollTop]);

    const scrollInBuffer = useCallback((delta) => {
        // Applies the scroll and returns the ramainder if we've passed the
        // zero in either direction
        let remainder = 0;
        let newBufPosition = scrollBufferPos + delta;
        if ((scrollBufferPos > 0 && newBufPosition < 0) ||
            (scrollBufferPos < 0 && newBufPosition > 0)) {
            // console.log('passed zero', scrollBufferPos, newBufPosition)
            remainder = newBufPosition;
            newBufPosition = 0;
        }
        // Limit to the upper and lower buffer bound
        newBufPosition = Math.max(MIN_SCROLL_BUFFER_POS, newBufPosition);
        newBufPosition = Math.min(MAX_SCROLL_BUFFER_POS, newBufPosition);

        setScrollBufferPos(newBufPosition);
        // console.log('scrollInBuffer', newBufPosition, 'for', delta)
        return remainder;
    }, [scrollBufferPos]);

    const applyScrollDelta = useCallback((delta: number) => {
        // Emulates a scroll buffer in order to properly iterate small segments

        // If we're in the buffer - apply the scroll there until we reach the
        // top/bottom or zero position. We snap at zero if there's room to
        // scroll in the container

        // Try to apply the scroll in the buffer if we're in the buffer
        let remainder = delta;
        if (scrollBufferPos !== 0) {
            remainder = scrollInBuffer(delta);
        }
        // console.log('remainder', remainder);
        // Apply the remainder in the container if there's room to do so
        if (remainder !== 0) {
            remainder = scrollInContainer(remainder);
        }
        // console.log('remainder2', remainder);
        // If there's still a remainder - apply it in the buffer again
        if (remainder !== 0) {
            scrollInBuffer(remainder);
        }
        // console.log('remainder3', remainder);
    }, [scrollBufferPos, scrollInBuffer, scrollInContainer]);

    const seekScrollTop = useCallback((newScrollTop: number) => {
        let delta = newScrollTop - scrollTop;
        applyScrollDelta(delta);
    }, [scrollTop, applyScrollDelta]);

    const onWheel = useCallback((event) => {
        // console.log(event);
        if (!scrollContainerRef.current) {
            return;
        }
        const delta = event.deltaY / 6;
        applyScrollDelta(delta);
        event.preventDefault();
    }, [applyScrollDelta]);

    const onTouchStart = useCallback((event) => {
        if (!scrollContainerRef.current) {
            return;
        }
        const touch = event.touches[0];
        setTouchStartY(touch.clientY);
        setTouchStartScrollTop(scrollContainerRef.current.scrollTop);
    }, []);

    const onTouchMove = useCallback((event) => {
        if (!scrollContainerRef.current) {
            return;
        }
        if (event.touches.length < 1 && event.touches.length > 2) {
            return;
        }
        const touch = event.touches[0];
        const touchDelta = touchStartY - touch.clientY;
        seekScrollTop(touchStartScrollTop + touchDelta);
    }, [touchStartY, touchStartScrollTop, seekScrollTop]);

    const onTouchEnd = useCallback((event) => {
        if (!scrollContainerRef.current) {
            return;
        }
        const touch = event.changedTouches[0];
        const touchDelta = touchStartY - touch.clientY;
        seekScrollTop(touchStartScrollTop + touchDelta);
    }, [touchStartY, touchStartScrollTop, seekScrollTop]);

    // Setup event listeners
    useEffect(() => {
        const handleResize = () => {
            let container = scrollContainerRef.current;
            if (!container) {
                return;
            }
            setClientHeight(container.clientHeight);
            setMaxScrollTop(container.scrollHeight - container.clientHeight);
        };

        handleResize();

        let container = scrollContainerRef.current;
        if (container) {
            container.addEventListener("resize", handleResize);
            container.addEventListener("wheel", onWheel, { passive: false })
            container.addEventListener("touchstart", onTouchStart, { passive: false });
            container.addEventListener("touchmove", onTouchMove, { passive: false });
            container.addEventListener("touchend", onTouchEnd, { passive: false });
        }

        return () => {
            if (container) {
                container.removeEventListener("resize", handleResize);
                container.removeEventListener("wheel", onWheel);
                container.removeEventListener("touchstart", onTouchStart);
                container.removeEventListener("touchmove", onTouchMove);
                container.removeEventListener("touchend", onTouchEnd);
            }
        };
    }, [onWheel, onTouchStart, onTouchMove, onTouchEnd]);

    // Update the activation level
    useEffect(() => {
        let FOCUS_LVL_PX = clientHeight * PREFERED_FOCUS_LEVEL;
        let SECOND_SEGMENT_H = clientHeight - FOCUS_LVL_PX;

        let newActivationLevel = 0;
        if (scrollBufferPos === 0) {
            newActivationLevel = FOCUS_LVL_PX;
        } else if (scrollBufferPos < 0) {
            let ratio = scrollBufferPos / MIN_SCROLL_BUFFER_POS; // both negative
            newActivationLevel = (1 - ratio) * FOCUS_LVL_PX;
        } else {
            let ratio = scrollBufferPos / MAX_SCROLL_BUFFER_POS;
            newActivationLevel = FOCUS_LVL_PX + SECOND_SEGMENT_H * ratio;
        }
        setActivationLevelPx(newActivationLevel);
        // console.log('newActivationLevel', newActivationLevel)
    }, [clientHeight, scrollBufferPos]);

    // Detect which segment we're on. Whichever is on the activation level
    // or closest to it is the active one
    useEffect(() => {
        let closestSegmentIdx = 0;
        let closestSegmentDist = Number.MAX_SAFE_INTEGER;
        for (let i = 0; i < segmentRefs.length; i++) {
            const segmentRef = segmentRefs[i];
            if (segmentRef.current === null) {
                continue;
            }
            const segmentRect = segmentRef.current.getBoundingClientRect();
            let segTop = segmentRect.top;
            let segBottom = segmentRect.bottom;
            let segCenter = (segTop + segBottom) / 2;

            // Check if the segment is on the activation level
            if (segTop <= activationLevelPx && segBottom >= activationLevelPx) {
                setActiveSegmentIdx(i);
                // console.log('Found closest segment directly. Id:', i);
                return;
            }

            // Mark the segment which is closest to the activation level
            let dist = Math.abs(segCenter - activationLevelPx);
            if (dist < closestSegmentDist) {
                closestSegmentDist = dist;
                closestSegmentIdx = i;
            }
            // console.log('segCenter', segCenter, 'activationLevelPx', activationLevelPx, 'dist', dist)
        }
        setActiveSegmentIdx(closestSegmentIdx);
        // console.log('Approximated closest segment. Id:', closestSegmentIdx);
    }, [activationLevelPx, segmentRefs, scrollTop, clientHeight]);

    // When the focused segment changes - use its link to reposition the map
    useEffect(() => {
        if (activeSegmentIdx === null) {
            return;
        }
        console.log('Segment changed. Id:', activeSegmentIdx)
        const segment = segments[activeSegmentIdx];
        if (segment.link) {
            console.log('Segment has link. Parsing:', segment.link)
            let link_data = parsePametUrl(segment.link);
            console.log('Viewport: ', link_data.viewportCenter, link_data.viewportHeight, '')
            if (link_data.viewportCenter && link_data.viewportHeight) {
                mapActions.startAutoNavigation(
                    parentPageViewState,
                    link_data.viewportCenter,
                    link_data.viewportHeight)
            }
        }
    }, [activeSegmentIdx, segments, parentPageViewState]);

    return (
        <TourContainer
            className='tour-container'
        >
            {/* Scroll area */}
            <ScrollContainer
                ref={scrollContainerRef}
            >
                {segments.map((segment, index) => (
                    <SegmentContainer
                        key={index}
                        ref={segmentRefs[index]}
                        className='tour-segment'
                        active={index === activeSegmentIdx}
                        dangerouslySetInnerHTML={{ __html: segment.html }}>
                    </SegmentContainer>
                ))}
            </ScrollContainer>

            {/* Activation level marker */}
            <div style={{
                position: 'absolute',
                left: '0px',
                top: '0px',
                width: '10px',
                height: '100%',
            }}>
                <div className='tour-mark' style={{
                    position: 'relative',
                    left: '0px',
                    top: (activationLevelPx - 5) + 'px',
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    backgroundColor: 'gray',
                }} />
            </div>
        </TourContainer>

    );
};
