import { useRef } from 'react';
import styled from 'styled-components';
import { NOTE_MARGIN } from '../../constants';
import { color_to_css_rgba_string } from '../../util';
import { observer } from 'mobx-react-lite';
import { NoteViewState } from './NoteViewState';

interface NoteComponentProps {
    noteViewState: NoteViewState;
    handleClick: (event: MouseEvent) => void;
}

export const NoteContainer = styled.a`
    /* content-visibility: auto; */
    /* will-change: transform; */

    text-decoration: none;
    position: absolute;
    display: flex;
    flex-wrap: wrap;
    /* top: ${props => props.y}px;
    left: ${props => props.x}px;
    width: ${props => props.width}px;
    height: ${props => props.height}px;
    color: ${props => props.color};
    background-color: ${props => props.backgroundColor};
    ${props => props.isLink ? `border: 1px solid ${props.color}` : ''} */
`;

const NoteText = styled.div`
    flex-grow: 8;
    align-self: center;
    min-height: 20px;
    min-width: 20px;
    width: min-content;
    height: min-content;

    overflow: hidden;
    text-decoration: none;

    //justify text in center
    display: flex;
    text-align: center;
    align-items: center;
    justify-content: center;

    font-family: 'Open Sans', sans-serif;
    font-size: 18px;
    line-height: 20px;
    color: ${props => props.color};
`;


export const NoteComponentBase = ({ noteViewState: state, handleClick }: NoteComponentProps) => {
    const self_ref = useRef<HTMLAnchorElement>(null);
    // console.log('Rendering note', noteData.id)
    const [x, y, width, height] = state.geometry;
    if (state.style.color === undefined) {
        console.log('Style is undefined for note', state);
        return null;
    }
    const color = color_to_css_rgba_string(state.style.color)
    const backgroundColor = color_to_css_rgba_string(state.style.background_color)
    const imageUrl = state.content.image_url;

    let isExternal = true;

    // If the url is with a pamet:/ schema - convert it to a local file path
    let href  = state.content.url;
    if (href && href.startsWith('pamet:/')) {
        href = href.replace('pamet:/', '/');
        isExternal = false;
    }

    let target: string = '_self';
    if (isExternal) {
        target = '_blank';
    }

    return (
        <NoteContainer
            ref={self_ref}
            href={href}
            target={target}
            rel="noopener noreferrer"
            className="note"
            style= {{
                top: y + 'px',
                left: x + 'px',
                width: width + 'px',
                height: height  + 'px',
                color: color,
                backgroundColor: backgroundColor,
                border: !!state.content.url ? `1px solid ${color}` : '',
            }}
            // x={x}
            // y={y}
            // width={width}
            // height={height}
            // color={color}
            // backgroundColor={backgroundColor}
            // isLink={!!noteData.content.url}
            isExternal={isExternal}
            onClick={handleClick}
        >
            {imageUrl && <img src={imageUrl} alt={"Loading..."} style={{
                maxWidth: "100%",
                maxHeight: "100%",
                objectFit: "contain",
                flexGrow: 1,
                alignSelf: "center",
                objectPosition: "top left"}} />}
            {state.textLayoutData && <NoteText
                color={color}
                padding={NOTE_MARGIN}
            >{state.textLayoutData.lines.join('\n')}</NoteText>}

            {/* Draw a div with a yellow border around the selected note */}
            {/* do not use a custom component, just vanilla div and css-in-js*/}
            {state.selected && <div
                style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: '4px solid yellow',
                }}
            />}


        </NoteContainer>
    );
}

// export const NoteComponent = React.memo(observer(NoteComponentBase), (prevProps, nextProps) => { // That's react memo related
//     // Just don't rerender the note ever
//     // TODO: When we start editing notes - there should be some mechanism to
//     // mark them for rerendering (e.g. a flag in the props or a timestamp in the
//     // note data, combined with a service that keeps track of the last time the
//     // note was rendered)
//     // Yeah, mmaybe just a service that keeps track of the last time the note was
//     // edited and the last time it was rendered.
//     return prevProps.selected === nextProps.selected;
// });

export const NoteComponent = observer(NoteComponentBase);
