import MapPageComponent from "./components/MapPage";
import "./App.css";
import { useCallback, useContext, useEffect, useState } from "react";
import { CurrentPageContext } from "./contexts";
import { MapPageData } from "./types/MapPage";

let HOME_PAGE_ID = "home";


const App = () => {

  // Get the pages from the server
  const [pages, setPages] = useState<MapPageData[]>([]);
  const [currentPage, setCurrentPage] = useState<MapPageData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // const changePage = (pageId: string) => {
  //   const page = pages.find((page) => page.id === pageId);

  //   if (page) {
  //     setCurrentPage(page);
  //   }
  // }

  // On url change (anchor, page change) - update page props
  const updatePageFromUrl = useCallback(() => {

    if (pages.length === 0) {
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
    // If the URL contains /p/ - load the page by id, else load the home page
    if (url.includes("/p/")) {
      const pageId = url.split("/p/")[1];

      // Get the page from the pages array
      const page = pages.find((page) => page.id === pageId);
      if (page) {
        setCurrentPage(page);
      } else {
        setPageToHomeOrFirst();
      }
    } else {
      setPageToHomeOrFirst();
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
        <MapPageComponent page={currentPage} />
        // </CurrentPageContext.Provider>
      ) : (
        <div>No current page present. Error: {errorMessage}</div>
      )}
    </div>
  );
};

export default App;
