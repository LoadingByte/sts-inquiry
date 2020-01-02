window.addEventListener("load", function () {
    for (const cont of document.getElementsByClassName("stw-container")) {
        for (const stw of cont.getElementsByClassName("stw")) {
            const noscript = stw.getElementsByTagName("noscript")[0];
            const mapPlaceholder = stw.getElementsByClassName("stw-tooltip-map-placeholder")[0];

            if (noscript || mapPlaceholder) {
                stw.addEventListener("mouseenter", function listener() {
                    stw.removeEventListener("mouseenter", listener);

                    if (noscript) {
                        const content = noscript.textContent.trim();
                        const wrapper = document.createElement("div");
                        wrapper.innerHTML = content;
                        noscript.parentNode.replaceChild(wrapper, noscript);
                    }

                    if (mapPlaceholder) {
                        const url = mapPlaceholder.textContent;
                        const iframe = document.createElement("iframe");
                        iframe.setAttribute("class", "stw-tooltip-map");
                        iframe.setAttribute("src", url);
                        mapPlaceholder.parentNode.replaceChild(iframe, mapPlaceholder);
                    }
                });
            }
        }
    }
});
