// Run with: node --test tests/js/
//
// No npm install, no build step - this loads the vendored UMD files and
// the app's own markdown.js exactly as Node's CommonJS `require` would.
// DOMPurify needs a real DOM/window and is therefore NOT exercised here;
// see docs/superpowers/specs/2026-09-12-markdown-rendering-design.md for
// the manual QA checklist that covers sanitizing and the tab UI.

import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { Marked } = require("../../hlasys2_app/static/vendor/marked.umd.js");
const HlasysMarkdown = require("../../hlasys2_app/static/markdown.js");

const { looksLikeMarkdown, render, applyInlineWrap, applyLinkInsert } = HlasysMarkdown;

// --- Detection -----------------------------------------------------------

test("detects standard markdown constructs", () => {
    const positives = [
        "## Nadpis",
        "- prvni\n- druhy",
        "je **tucne** dnes",
        "[odkaz](https://hkfree.org)",
        "![alt](https://hkfree.org/x.png)",
        "> citace",
        "pouzij `kod` prikaz",
        "| a | b |\n|---|---|\n| 1 | 2 |",
        "```\nkod blok\n```",
    ];
    for (const src of positives) {
        assert.equal(looksLikeMarkdown(src), true, `expected markdown: ${JSON.stringify(src)}`);
    }
});

test("does not flag ordinary Czech prose as markdown", () => {
    const negatives = [
        "Bezny text.\nDruhy radek popisu navrhu.",
        "Rok 1998. byl pro hkfree klicovy.",
        "S pozdravem\n-- ",
        "je _aktivne_ pouzivano",
        "cena je 5*100 Kc za kus",
        "viz http://hkfree.org/a_b_c pro detaily",
        "2+2=4\n---\nkonec zpravy",
        "soubor se jmenuje muj_dlouhy_nazev.txt",
        "",
    ];
    for (const src of negatives) {
        assert.equal(looksLikeMarkdown(src), false, `expected plain text: ${JSON.stringify(src)}`);
    }
});

// Regression fixtures mined from the production database (see design doc):
// these are real proposals whose plain-text descriptions would otherwise be
// mangled by a stock markdown renderer.
test("real historical descriptions that trigger detection via bullets still render safely", () => {
    // #46 - contains "- " style content further down; representative excerpt
    const src = "Navrh:\n- zvysit limit\n- snizit poplatek";
    assert.equal(looksLikeMarkdown(src), true);
    const html = render(src, Marked);
    assert.match(html, /<ul>/);
});

// --- Renderer overrides: collision handling --------------------------------

test("setext-style underlines (signatures) do not become headings", () => {
    const html = render("S pozdravem\n-- ", Marked);
    assert.doesNotMatch(html, /<h[1-6]>/);
    assert.match(html, /S pozdravem/);
});

test("a long run of '=' under a URL does not become an h1", () => {
    const html = render("http://tresice.hkfree.org\n======================", Marked);
    assert.doesNotMatch(html, /<h[1-6]>/);
});

test("4-space indented text is not treated as a code block", () => {
    const html = render("text\n\n     ctyri mezery", Marked);
    assert.doesNotMatch(html, /<pre>/);
});

test("fenced code blocks still render as code", () => {
    const html = render("```\nkod\n```", Marked);
    assert.match(html, /<pre><code>/);
});

test("raw HTML in the source is escaped, not executed", () => {
    const html = render("kontakt <OliAP spravce> dnes", Marked);
    assert.doesNotMatch(html, /<OliAP/);
    assert.match(html, /&lt;OliAP spravce&gt;/);
});

test("a raw <img onerror> payload is neutralized by the renderer itself", () => {
    const html = render("<img src=x onerror=alert(1)>", Marked);
    assert.doesNotMatch(html, /<img/);
    assert.match(html, /&lt;img/);
});

test("underscore and asterisk emphasis/strong both render normally", () => {
    // CommonMark's own intraword-underscore suppression (verified in the
    // "does not flag ordinary prose" test above via looksLikeMarkdown, and
    // directly below) already keeps snake_case/URLs literal, so a
    // genuine "_word_" or "__word__" with real word boundaries is safe to
    // render as real emphasis - this is also the only way to write bold
    // or italic text that wraps a link (`__[text](url)__`).
    assert.match(render("je _aktivne_ dnes", Marked), /<em>aktivne<\/em>/);
    assert.match(render("je __tucne__ dnes", Marked), /<strong>tucne<\/strong>/);
    assert.match(render("je *aktivne* dnes", Marked), /<em>aktivne<\/em>/);
    assert.match(render("je **tucne** dnes", Marked), /<strong>tucne<\/strong>/);
});

test("intraword underscores (snake_case, URLs) still do not trigger emphasis", () => {
    const html = render("soubor muj_dlouhy_nazev.txt", Marked);
    assert.match(html, /muj_dlouhy_nazev\.txt/);
    assert.doesNotMatch(html, /<em>|<strong>/);
});

test("bold/italic markers can wrap a link (a real proposal from the field)", () => {
    const html = render("__[pica](https://nodeca.github.io/pica/demo/)__ - popis", Marked);
    assert.match(html, /<strong><a href="https:\/\/nodeca\.github\.io\/pica\/demo\/">pica<\/a><\/strong>/);
});

test("multi-line prose keeps line breaks (breaks:true) instead of collapsing to one paragraph", () => {
    const html = render("# H\nline1\nline2", Marked);
    assert.match(html, /line1<br>line2/);
});

test("GFM tables render", () => {
    const html = render("| a | b |\n|---|---|\n| 1 | 2 |", Marked);
    assert.match(html, /<table>/);
    assert.match(html, /<td>1<\/td>/);
});

test("horizontal rules still work", () => {
    const html = render("text\n\n---\n\ndalsi", Marked);
    assert.match(html, /<hr>/);
});

// --- Editor shortcuts: applyInlineWrap (Ctrl+B / Ctrl+I) -------------------

test("wraps a selection with markers", () => {
    const r = applyInlineWrap("je dulezity text", 3, 11, "**", "**", "placeholder");
    assert.equal(r.value, "je **dulezity** text");
    assert.equal(r.value.slice(r.selectionStart, r.selectionEnd), "dulezity");
});

test("inserts a placeholder and selects it when there is no selection", () => {
    const r = applyInlineWrap("", 0, 0, "**", "**", "tucny text");
    assert.equal(r.value, "**tucny text**");
    assert.equal(r.value.slice(r.selectionStart, r.selectionEnd), "tucny text");
});

test("toggles off markers when the selection is already wrapped", () => {
    const wrapped = applyInlineWrap("je dulezity text", 3, 11, "**", "**", "x");
    // Re-apply to the now-selected inner text ("dulezity") -> should unwrap.
    const unwrapped = applyInlineWrap(wrapped.value, wrapped.selectionStart, wrapped.selectionEnd, "**", "**", "x");
    assert.equal(unwrapped.value, "je dulezity text");
});

test("italic and bold markers do not collide when toggling", () => {
    // A bold selection re-wrapped with the italic marker should nest, not unwrap.
    const r = applyInlineWrap("**bold**", 2, 6, "*", "*", "x");
    assert.equal(r.value, "**" + "*bold*" + "**");
});

// --- Editor shortcuts: applyLinkInsert (Ctrl+K) ----------------------------

test("wraps a selection as link text and selects the URL placeholder", () => {
    const r = applyLinkInsert("prectete si toto", 12, 16, "text odkazu", "https://");
    assert.equal(r.value, "prectete si [toto](https://)");
    assert.equal(r.value.slice(r.selectionStart, r.selectionEnd), "https://");
});

test("inserts placeholder link text and selects the URL when there is no selection", () => {
    const r = applyLinkInsert("", 0, 0, "text odkazu", "https://");
    assert.equal(r.value, "[text odkazu](https://)");
    assert.equal(r.value.slice(r.selectionStart, r.selectionEnd), "https://");
});

// --- Compact rendering: blank-line-separated bullets stay tight ----------
//
// GFM calls this a "loose list" and wraps every item in <p>, which looks
// like large wasted gaps since a <p>'s margin can't collapse across the
// enclosing <li> boundary. Authors leaving blank lines for readability in a
// plaintext box almost never intend that; tight rendering matches what they
// expect to see.

test("a blank-line-separated bullet list renders tight, not wrapped in <p>", () => {
    const html = render("- prvni polozka\n\n- druha polozka", Marked);
    assert.doesNotMatch(html, /<li><p>/);
    assert.match(html, /<li>prvni polozka<\/li>/);
});

test("a genuine second paragraph within a single list item is still wrapped", () => {
    const html = render("- prvni radek\n\n  druhy odstavec ve stejne polozce", Marked);
    // The item's own first line stays unwrapped; the deliberate second
    // paragraph nested under it keeps its <p>, so it's still visually
    // distinct from the item's leading line.
    assert.match(html, /<li>prvni radek<p>druhy odstavec/);
});

test("nested sub-lists still render correctly when the parent list is tightened", () => {
    const html = render("- top\n  - nested\n\n- top2", Marked);
    assert.match(html, /<li>top<ul>\s*<li>nested<\/li>/);
});
