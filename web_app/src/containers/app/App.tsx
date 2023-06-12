import "./App.css";
import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { MapPageData } from "../../model/MapPage";
import { MapPageComponent } from "../../components/MapPage/MapPage";
import { MapPageViewState } from "../../components/MapPage/MapPageViewState";

let HOME_PAGE_ID = "home";


// // Define the app state with mobx and typescript
// class AppState {
//   // Define the state
//   pages: MapPageData[] = [];
//   currentPage: MapPageData | null = null;
//   errorMessage: string | null = null;

//   constructor() {
//     makeAutoObservable(this);
//   }

//   setCurrentPage(page: MapPageData) {
//     this.currentPage = page;
//   }

//   setErrorMessage(message: string) {
//     this.errorMessage = message;
//   }
// }


const App = observer(() => {


  // Get the pages from the server
  const [pages, setPages] = useState<MapPageData[]>([]);
  const [currentPage, setCurrentPage] = useState<MapPageData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // On url change (anchor, page change) - update page props
  const updatePageFromUrl = useCallback(() => {

    if (pages.length === 0) {
      setCurrentPage(null);
      return;
    }

    function setPageToHomeOrFirst() {
      const page = pages.find((page) => page.id === HOME_PAGE_ID);
      if (page) {
        setCurrentPage(page);
      } else {
        console.warn("No home page found");
        setCurrentPage(pages[0]);
      }
    }

    // Get the page id from the URL (/p/:id)
    const url = window.location.href;
    const urlPath = window.location.pathname;

    // If we're at the index page, load home or first
    if(urlPath === "/") {
      setPageToHomeOrFirst();
      return;

    // If the URL contains /p/ - load the page by id, else load the home page
    } else if (urlPath.includes("/p/")) {
      const pageId = urlPath.split("/")[2];

      // Get the page from the pages array
      const page = pages.find((page) => page.id === pageId);
      if (page) {
        setCurrentPage(page);
      } else {
        setErrorMessage(`Page with id ${pageId} not found`);
        console.log("Page not found", pageId)
        console.log("Pages", pages)
        setCurrentPage(null);
      }
    } else {
      console.log("Url not supported", urlPath)
      setCurrentPage(null);
    }
  }, [pages]);

  // Set the page initially from the URL and subscribe to URL changes
  useEffect(() => {
    updatePageFromUrl();
    window.addEventListener("popstate", updatePageFromUrl);

    return () => {
      window.removeEventListener("popstate", updatePageFromUrl);
    };
  }, [updatePageFromUrl]);

  // Get the pages from the server
  useEffect(() => {
    fetch("/pages.json")
      .then((res) => {
        return res.json()})
      .then((pages) => {
        // console.log(pages)
        setPages(pages);
      })
      .catch((err) => {
        console.error("Error getting pages", err.message);
        setErrorMessage(err.message);
      });
  }, []);


  return (
    <div className="app">


      {currentPage ? (
        // <CurrentPageContext.Provider value={{pageId: currentPage.id, changePage}}>
        <MapPageComponent state={new MapPageViewState(currentPage)} />
        // </CurrentPageContext.Provider>
      ) : (
        <div>No current page present. Error: {errorMessage}</div>
      )}
    </div>
  );
});

export default App;
