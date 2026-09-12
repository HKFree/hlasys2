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

    // --- 4b. Editor keyboard shortcuts -----------------------------------
    //
    // Pure string transforms on (value, selectionStart, selectionEnd) so
    // they're unit-testable without a DOM/textarea (see
    // tests/js/markdown.test.mjs). The DOM wiring (keydown listener,
    // reading/writing textarea.value and .selectionStart/End) lives in
    // create.html, next to the write/preview tab wiring it complements.
    //
    // Wrapping is a toggle: applying the same shortcut to an already-wrapped
    // selection (e.g. **bold** -> Ctrl+B again) removes the markers instead
    // of nesting them.
    function applyInlineWrap(value, start, end, before, after, placeholder) {
        const hasSelection = start !== end;
        const selected = value.slice(start, end);
        const beforeCtx = value.slice(Math.max(0, start - before.length), start);
        const afterCtx = value.slice(end, end + after.length);
        // Guard against matching a single-char marker (e.g. italic `*`)
        // against the boundary of a longer run of the same character (e.g.
        // bold `**`) - without this, toggling italic inside **bold** would
        // strip one asterisk from each side instead of nesting correctly.
        const beforeExtra = value.slice(Math.max(0, start - before.length - 1), start - before.length);
        const afterExtra = value.slice(end + after.length, end + after.length + 1);
        const isExactBoundary =
            beforeExtra !== before[before.length - 1] && afterExtra !== after[0];

        if (hasSelection && beforeCtx === before && afterCtx === after && isExactBoundary) {
            const newValue =
                value.slice(0, start - before.length) +
                selected +
                value.slice(end + after.length);
            return {
                value: newValue,
                selectionStart: start - before.length,
                selectionEnd: start - before.length + selected.length,
            };
        }

        const text = hasSelection ? selected : placeholder;
        const newValue = value.slice(0, start) + before + text + after + value.slice(end);
        return {
            value: newValue,
            selectionStart: start + before.length,
            selectionEnd: start + before.length + text.length,
        };
    }

    // Inserts `[selected or placeholder text](placeholderUrl)` and selects
    // the URL portion, so pasting a URL immediately after triggering the
    // shortcut just works - mirrors common markdown editor behaviour.
    function applyLinkInsert(value, start, end, placeholderText, placeholderUrl) {
        const hasSelection = start !== end;
        const linkText = hasSelection ? value.slice(start, end) : placeholderText;
        const insertion = "[" + linkText + "](" + placeholderUrl + ")";
        const newValue = value.slice(0, start) + insertion + value.slice(end);
        const urlStart = start + 1 + linkText.length + 2;
        const urlEnd = urlStart + placeholderUrl.length;
        return { value: newValue, selectionStart: urlStart, selectionEnd: urlEnd };
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
        applyInlineWrap,
        applyLinkInsert,
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
