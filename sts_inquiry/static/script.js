"use strict";

window.addEventListener("load", function () {
    const stws = document.querySelectorAll("td:nth-child(2) .stw");
    for (let i = 0; i < stws.length; i++) {
        const stw = stws[i];

        const noscript = stw.getElementsByTagName("noscript")[0];
        const mapPlaceholder = stw.getElementsByClassName("stw-tooltip-map-placeholder")[0];

        if (noscript || mapPlaceholder) {
            stw.addEventListener("mouseenter", function listener() {
                stw.removeEventListener("mouseenter", listener);

                if (noscript) {
                    const content = noscript.textContent.trim();
                    const tmp = document.createElement("div");
                    tmp.innerHTML = content;
                    const img = tmp.getElementsByTagName("img")[0];
                    noscript.parentNode.replaceChild(img, noscript);
                }

                if (mapPlaceholder) {
                    const url = mapPlaceholder.textContent;
                    const iframe = document.createElement("iframe");
                    iframe.setAttribute("src", url);
                    iframe.setAttribute("class", "stw-tooltip-map");
                    mapPlaceholder.parentNode.replaceChild(iframe, mapPlaceholder);

                    // IE 11 fix: Hovering over an iframe should not lose the hover on the parent container.
                    if (window.navigator.userAgent.indexOf("Trident") > 0) {
                        iframe.addEventListener("mouseenter", function () {
                            stw.classList.add("ie-hover");
                        });
                        iframe.addEventListener("mouseleave", function () {
                            stw.classList.remove("ie-hover");
                        });
                    }
                }
            });
        }
    }
});
