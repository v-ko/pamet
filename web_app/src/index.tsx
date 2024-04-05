import React, { createContext } from 'react';
import ReactDOM from 'react-dom/client';
import WebApp, { WebAppState } from './containers/app/App';
import './index.css';
// import reportWebVitals from './reportWebVitals';
import { PametFacade, pamet } from './facade';
import { getLogger } from './fusion/logging';


// Imports that are required to just activate decorators. Might be removed when
// some extensions logic is implemented
import { TextNote } from './model/TextNote';
import { CardNote } from './model/CardNote';
import { ImageNote } from './model/ImageNote';
import { OtherPageListNote } from './model/OtherPageListNote';
import { ScriptNote } from './model/ScriptNote';
import { InternalLinkNote } from './model/InternalLinkNote';
import { InternalLinkNoteCanvasView } from './components/note/InternalLinkCanvasView';
import { ExternalLinkNote } from './model/ExternalLinkNote';
import { ExternalLinkNoteCanvasView } from './components/note/ExternalLinkCanvasView';
import { ScriptNoteCanvasView } from './components/note/ScriptNoteCanvasView';
import { CardNoteCanvasView } from './components/note/CardNoteCanvasView';
import { fusion } from './fusion';
import { ActionState } from './fusion/libs/Action';
let dummyImports: any[] = [];
dummyImports.push(TextNote);
dummyImports.push(CardNote);
dummyImports.push(ImageNote);
dummyImports.push(OtherPageListNote);
dummyImports.push(ScriptNote);
dummyImports.push(InternalLinkNote);
dummyImports.push(ExternalLinkNote);
dummyImports.push(InternalLinkNoteCanvasView)
dummyImports.push(ExternalLinkNoteCanvasView)
dummyImports.push(ScriptNoteCanvasView)
dummyImports.push(CardNoteCanvasView)

const log = getLogger("index.tsx");

// Create the root
const root = ReactDOM.createRoot(
    document.getElementById('root') as HTMLElement
);

// Pass the facade to all components
const PametContext = createContext<PametFacade>(pamet);
(window as any).pamet = pamet; // For debugging

// Create the app state with the appropriate page from the URL
let app_state = new WebAppState();

pamet.setWebAppState(app_state);

// Testing: log the actions channel
fusion.rootActionEventsChannel.subscribe((actionState: ActionState) => {
    if (actionState.issuer !== 'user'){
        return;
    }
    log.info(`Action ${actionState.name} ${actionState.runState}`);
});

root.render(
    <React.StrictMode>
        <PametContext.Provider value={pamet}>
            <WebApp state={app_state} />
        </PametContext.Provider>
    </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
// reportWebVitals();
