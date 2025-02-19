import { useRef } from 'react';
import { NOTE_MARGIN } from '../../core/constants.js';
import { color_role_to_hex_color } from "../../util/Color.js";
import { observer } from 'mobx-react-lite';
import { NoteViewState } from './NoteViewState.js';
import { pamet } from '../../core/facade.js';
import { getLogger } from 'fusion/logging.js';

import { trace } from 'mobx';
import React from 'react';

let log = getLogger('NoteComponent');

interface NoteComponentProps {
    noteViewState: NoteViewState;
    // handleClick: (event: React.MouseEvent<HTMLAnchorElement, MouseEvent>) => void;
}


export const NoteComponentBase = ({ noteViewState: state }: NoteComponentProps) => {
    // trace(true)

    const self_ref = useRef<HTMLAnchorElement>(null);
    const note = state.note();
    const [x, y, width, height] = note.geometry;
    if (note.style.color_role === undefined) {
        console.log('Style is undefined for note', state);
        return null;
    }
    const color = color_role_to_hex_color(note.style.color_role)
    const backgroundColor = color_role_to_hex_color(note.style.background_color_role)

    // Handling the url
    let isExternal = true;
    // If the url is with a pamet:/ schema - convert it to a local file path
    let href = note.content.url;
    if (href && href.startsWith('pamet:/')) {
        href = href.replace('pamet:/', '/');
        isExternal = false;
    }

    let target: string = '_self';
    if (isExternal) {
        target = '_blank';
    }

    // Handling the image

    let image = note.content.image
    let imageSrc: string | undefined = undefined;
    // let apiBaseUrl = pamet.apiClient().endpointUrl('/');

    // if (imageUrl) {
    //     log.info('imageUrl', imageUrl)
    // }

    if (image ) {
        imageSrc = pamet.apiClient.projectScopedUrlToGlobal(image.url);
        isExternal = false;
    }
    // if (imageUrl) {
    //     log.info('NoteComponentBase', 'imageSrc', imageSrc, 'isExternal', isExternal)
    // }

    return (
        <a
            ref={self_ref}
            href={href}
            target={target}
            rel="noopener noreferrer"
            className="note note-container"
            draggable={false}
            style={{
                top: y + 'px',
                left: x + 'px',
                width: width + 'px',
                height: height + 'px',
                color: color,
                background: backgroundColor,
                border: !!note.content.url ? `1px solid ${color}` : '',
                textDecoration: 'none',
                position: 'absolute',
                display: 'flex',
                flexWrap: 'wrap',
            }}
            // isExternal={isExternal}
            // onClick={handleClick}
        >
            {imageSrc && <img src={imageSrc} alt={"Loading..."} style={{
                maxWidth: "100%",
                maxHeight: "100%",
                objectFit: "contain",
                flexGrow: 1,
                alignSelf: "center",
                objectPosition: "center"
            }} />}
            {state.textLayoutData && <div
                className="note-text"
                style={{color: color,
                    padding: NOTE_MARGIN}}
            >{state.textLayoutData.lines.join('\n')}</div>}
        </a>
    );
}

export const NoteComponent = React.memo(observer(NoteComponentBase), (prevProps, nextProps) => { // That's react memo related
    // Just don't rerender the note ever
    // TODO: When we start editing notes - there should be some mechanism to
    // mark them for rerendering (e.g. a flag in the props or a timestamp in the
    // note data, combined with a service that keeps track of the last time the
    // note was rendered)
    // Yeah, mmaybe just a service that keeps track of the last time the note was
    // edited and the last time it was rendered.
    return prevProps.noteViewState === nextProps.noteViewState;
    // return prevProps.noteViewState.selected === nextProps.noteViewState.selected;
});

// export const NoteComponent = observer(NoteComponentBase);
