// Pamet canvas viewer — readable source.
// This file is for development; viewer.min.js is injected into .canvas files.

(function () {
    "use strict";

    var dataTag = document.getElementById("pamet-data");
    if (!dataTag) {
        console.warn("pamet-data script tag not found");
        return;
    }

    var pageData;
    try {
        pageData = JSON.parse(dataTag.textContent);
    } catch (e) {
        console.error("Failed to parse pamet-data JSON:", e);
        return;
    }

    console.log("Pamet canvas loaded:", pageData.id, pageData.name);
})();
