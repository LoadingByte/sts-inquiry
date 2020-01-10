"use strict";

window.addEventListener("load", function () {
    // Add listeners that load stw image and map as soon as the user activates a tooltip.
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

    // Add listeners to links that change the currently highlighted row.
    const tbodyTrs = document.querySelectorAll("tbody tr");
    for (let i = 0; i < tbodyTrs.length; i++) {
        const tr = tbodyTrs[i];

        const clusterLink = tr.getElementsByClassName("cluster-link")[0];
        if (clusterLink) {
            clusterLink.addEventListener("click", function (event) {
                const oldHighlightTr = document.getElementsByClassName("highlight-row")[0];
                if (oldHighlightTr) {
                    oldHighlightTr.classList.remove("highlight-row");
                }
                tr.classList.add("highlight-row");
                history.pushState(null, null, clusterLink.getAttribute("href"));
                event.preventDefault();
            })
        }
    }

    // Scroll the page to the row that is highlighted at page load (if any).
    const highlightRow = document.getElementsByClassName("highlight-row")[0];
    if (highlightRow) {
        const rect = highlightRow.getBoundingClientRect();
        const scroll = rect.top + window.pageYOffset - (window.innerHeight - rect.height) / 2;
        window.scrollTo(0, scroll);
    }
});
