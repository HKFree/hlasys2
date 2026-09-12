/**
 * Client-side markdown rendering for proposal descriptions.
 *
 * Design: descriptions are stored and server-rendered as plain text
 * (Jinja `| urlize`, unchanged). This script inspects the *rendered* text
 * content, and only if it looks like markdown does it re-render the element
 * as sanitized HTML. Plain prose, and anything with JS disabled, keeps
 * today's exact behaviour.
 *
 * Exposed as `window.HlasysMarkdown` so both the proposal page and the
 * create-proposal preview tab use the exact same pipeline, and so this file
 * is testable with `node --test` (see tests/js/markdown.test.mjs).
 */
(function (root) {
    "use strict";

    // --- 1. Detection -------------------------------------------------
    //
    // Deliberately narrow: only constructs nobody types by accident in a
    // plaintext box. Ordinary Czech prose ("1998. rok byl...", "5*100 Kč",
    // "S pozdravem\n-- ", "_aktivne_") must NOT trigger this.
    const DETECT_RULES = [
        /^ {0,3}#{1,6} +\S/m, // ATX heading:      ## Nadpis
        /^ {0,3}(```|~~~)/m, // fenced code:      ```
        /\*\*[^\s*][^*\n]*\*\*/, // bold:             **tucne**
        /!?\[[^\]\n]*\]\([^)\s]+(?: +"[^"\n]*")?\)/, // link/image:  [text](url)
        /^ {0,3}> +\S/m, // blockquote:       > citace
        /`[^`\n]+`/, // inline code:      `kod`
        /^ {0,3}[-*+] +\S/m, // bullet list:      - polozka
        /^ {0,3}\|?(?:[^\n|]*\|)+[^\n|]*\n {0,3}\|? *:?-{2,}:? *(?:\| *:?-{2,}:? *)*\|? *$/m, // GFM table
    ];

    function looksLikeMarkdown(src) {
        if (!src) return false;
        return DETECT_RULES.some((re) => re.test(src));
    }

    // --- 2. Rendering ---------------------------------------------------
    //
    // breaks:true is load-bearing - without it, existing multi-line
    // descriptions collapse into a single paragraph.
    //
    // The renderer overrides below neutralise markdown constructs that are
    // common accidental collisions with plain prose written in a textarea,
    // verified against real historical proposal data:
    //   - raw HTML          -> escaped literal (also XSS defense in depth)
    //   - setext headings   -> paragraph   ("S pozdravem\n-- " is not a heading)
    //   - indented code     -> paragraph   (4 leading spaces is not code)
    //   - _underscore_ em/strong -> literal (collides with snake_case, URLs)
    function escapeHtml(s) {
        return s
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function makeRenderer(MarkedCtor) {
        const m = new MarkedCtor({ gfm: true, breaks: true });
        m.use({
            renderer: {
                html(token) {
                    return escapeHtml(token.raw);
                },
                heading(token) {
                    // A setext heading's raw text ends in a line of `-` or `=`.
                    // ATX headings ("## x") don't match this and fall through.
                    if (/\n[ \t]*(=+|-+)[ \t]*$/.test(token.raw.replace(/\n$/, ""))) {
                        return "<p>" + this.parser.parseInline(token.tokens) + "</p>\n";
                    }
                    return false;
                },
                code(token) {
                    if (!/^ {0,3}(```|~~~)/.test(token.raw)) {
                        return "<p>" + escapeHtml(token.text).replace(/\n/g, "<br>") + "</p>\n";
                    }
                    return false;
                },
                em(token) {
                    return token.raw.startsWith("_") ? escapeHtml(token.raw) : false;
                },
                strong(token) {
                    return token.raw.startsWith("_") ? escapeHtml(token.raw) : false;
                },
            },
        });
        return (src) => m.parse(src);
    }

    // --- 3. Sanitizing ---------------------------------------------------

    const SANITIZE_CONFIG = {
        ALLOWED_TAGS: [
            "p", "br", "strong", "em", "del", "code", "pre", "blockquote",
            "ul", "ol", "li", "a", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
            "table", "thead", "tbody", "tr", "th", "td", "img",
        ],
        ALLOWED_ATTR: ["href", "title", "alt", "src", "align"],
        ALLOWED_URI_REGEXP: /^(?:https?:|mailto:)/i,
    };

    function sanitize(DOMPurifyInstance, html) {
        return DOMPurifyInstance.sanitize(html, SANITIZE_CONFIG);
    }

    // --- 4. Full pipeline (render + sanitize), used by page wiring ------
    //
    // `render` (markdown -> raw HTML string) needs only `marked` and runs
    // fine in plain Node, so it's unit-tested directly (see
    // tests/js/markdown.test.mjs). `renderMarkdown` additionally sanitizes
    // with DOMPurify, which requires a real DOM/window and is therefore
    // only exercised by browser QA, not the Node test suite.
    function render(src, MarkedCtor) {
        return makeRenderer(MarkedCtor)(src);
    }

    function renderMarkdown(src, MarkedCtor, DOMPurifyInstance) {
        return sanitize(DOMPurifyInstance, render(src, MarkedCtor));
    }

    // --- 5. Post-processing of the resulting DOM -------------------------
    // DOMPurify's allowlist governs *tags/attrs*, not link/image behaviour.
    // Force these regardless of what the markdown produced.
    function hardenRenderedDom(container) {
        container.querySelectorAll("a").forEach((a) => {
            a.setAttribute("target", "_blank");
            a.setAttribute("rel", "noopener noreferrer nofollow");
        });
        container.querySelectorAll("img").forEach((img) => {
            img.setAttribute("loading", "lazy");
            img.setAttribute("referrerpolicy", "no-referrer");
        });
    }

    // --- 6. DOM wiring (skipped entirely outside a browser / in tests) --
    function enhanceElement(el, MarkedCtor, DOMPurifyInstance) {
        const src = el.textContent;
        if (!looksLikeMarkdown(src)) return false;
        el.innerHTML = renderMarkdown(src, MarkedCtor, DOMPurifyInstance);
        el.classList.add("md-rendered");
        hardenRenderedDom(el);
        return true;
    }

    const HlasysMarkdown = {
        looksLikeMarkdown,
        render,
        renderMarkdown,
        hardenRenderedDom,
        enhanceElement,
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = HlasysMarkdown;
    } else {
        root.HlasysMarkdown = HlasysMarkdown;
    }

    if (typeof document !== "undefined") {
        document.addEventListener("DOMContentLoaded", function () {
            if (typeof marked === "undefined" || typeof DOMPurify === "undefined") {
                return;
            }
            document.querySelectorAll("[data-markdown-source]").forEach((el) => {
                enhanceElement(el, marked.Marked, DOMPurify);
            });
        });
    }
})(typeof window !== "undefined" ? window : globalThis);
