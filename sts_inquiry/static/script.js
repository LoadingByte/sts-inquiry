window.addEventListener("load", function () {
    console.log("Hi");

    for (const stw of document.getElementsByClassName("stw")) {
        const mapPlaceholder = stw.getElementsByClassName("stw-tooltip-map-placeholder")[0];
        if (mapPlaceholder) {
            stw.addEventListener("mouseenter", function listener() {
                stw.removeEventListener("mouseenter", listener);

                const url = mapPlaceholder.textContent;
                const iframe = document.createElement("iframe");
                iframe.setAttribute("class", "stw-tooltip-map");
                iframe.setAttribute("src", url);
                mapPlaceholder.parentNode.replaceChild(iframe, mapPlaceholder);
            });
        }
    }
});
