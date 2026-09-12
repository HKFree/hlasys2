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

const { looksLikeMarkdown, render } = HlasysMarkdown;

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

test("underscore emphasis/strong is left as literal text", () => {
    assert.match(render("je _aktivne_ dnes", Marked), /_aktivne_/);
    assert.match(render("je __tucne__ dnes", Marked), /__tucne__/);
});

test("asterisk emphasis/strong still works normally", () => {
    assert.match(render("je *aktivne* dnes", Marked), /<em>aktivne<\/em>/);
    assert.match(render("je **tucne** dnes", Marked), /<strong>tucne<\/strong>/);
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
