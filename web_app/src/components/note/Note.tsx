import { useRef } from 'react';
import { NOTE_MARGIN } from '../../constants';
import { color_to_css_rgba_string } from '../../util';
import { observer } from 'mobx-react-lite';
import { NoteViewState } from './NoteViewState';
import { pamet } from '../../facade';
import { getLogger } from '../../fusion/logging';
import { trace } from 'mobx';
import React from 'react';

let log = getLogger('NoteComponent');

interface NoteComponentProps {
    noteViewState: NoteViewState;
    handleClick: (event: React.MouseEvent<HTMLAnchorElement, MouseEvent>) => void;
}


export const NoteComponentBase = ({ noteViewState: state, handleClick }: NoteComponentProps) => {
    // trace(true)

    const self_ref = useRef<HTMLAnchorElement>(null);
    const note = state.note;
    const [x, y, width, height] = note.geometry;
    if (note.style.color === undefined) {
        console.log('Style is undefined for note', state);
        return null;
    }
    const color = color_to_css_rgba_string(note.style.color)
    const backgroundColor = color_to_css_rgba_string(note.style.background_color)

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
    // There's image_url and local_image_url. The qt desktop app downloaded
    // everything and gave it a local_image_url. The web app might not.
    // Cases to handle:
    // No local_image_url: show image_url
    // local_image_url starts with pamet:/ - get it with the api
    // (it'll be like /p/{page_id}/media/{path:path})
    // local_image_url starts with / - use the API desktop/fs/{path} endpoint

    let imageUrl = note.content.local_image_url || note.content.image_url;
    let imageSrc = imageUrl;
    // let apiBaseUrl = pamet.apiClient().endpointUrl('/');

    // if (imageUrl) {
    //     log.info('imageUrl', imageUrl)
    // }

    if (imageUrl && imageUrl.startsWith('pamet:/')) {
        imageSrc = imageUrl.replace('pamet:/', '/');
        imageSrc = pamet.apiClient().endpointUrl(imageSrc);
        isExternal = false;
    } else if (imageUrl && imageUrl.startsWith('/')) {
        imageSrc = pamet.apiClient().endpointUrl('desktop/fs') + imageUrl;
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
            style={{
                top: y + 'px',
                left: x + 'px',
                width: width + 'px',
                height: height + 'px',
                color: color,
                backgroundColor: backgroundColor,
                border: !!note.content.url ? `1px solid ${color}` : '',
                textDecoration: 'none',
                position: 'absolute',
                display: 'flex',
                flexWrap: 'wrap',
            }}
            // isExternal={isExternal}
            onClick={handleClick}
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
                // padding={NOTE_MARGIN}
            >{state.textLayoutData.lines.join('\n')}</div>}

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
    return prevProps.noteViewState.selected === nextProps.noteViewState.selected;
});

// export const NoteComponent = observer(NoteComponentBase);
