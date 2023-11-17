import React, { createContext } from 'react';
import ReactDOM from 'react-dom/client';
import WebApp, { WebAppState } from './containers/app/App';
import './index.css';
import reportWebVitals from './reportWebVitals';
import { PametFacade, pamet } from './facade';
// import { PersistenceManagerService } from './services/persistenceManager';
import { WebAppActions } from './actions/app';
import { getLogger } from './fusion/logging';

// The setup logic is here, yes.
// let persistenceManager = new PersistenceManagerService();
// pamet.setRepo(persistenceManager);

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
pamet.loadAllEntitiesTMP(() => {
    log.info("Loaded all entities")
    WebAppActions.setLoading(app_state, false);

    let urlPath = window.location.pathname;
    // If we're at the index page, load home or first
    if (urlPath === "/") {
        WebAppActions.setPageToHomeOrFirst(app_state);

        // If the URL contains /p/ - load the page by id, else load the home page
    } else if (urlPath.includes("/p/")) {
        const pageId = urlPath.split("/")[2];

        // Get the page from the pages array
        const page = pamet.findOne({ id: pageId });
        if (page) {
            WebAppActions.setCurrentPage(app_state, page.id);
        } else {
            WebAppActions.setErrorMessage(app_state, `Page with id ${pageId} not found`);
            console.log("Page not found", pageId)
            // console.log("Pages", pages)
            WebAppActions.setCurrentPage(app_state, null);
        }
    } else {
        console.log("Url not supported", urlPath)
        WebAppActions.setCurrentPage(app_state, null);
    }
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
reportWebVitals();
