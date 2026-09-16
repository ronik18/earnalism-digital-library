import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { paragraphsFromHtml, ReaderContent } from "./readerContent";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("Reader canonical HTML rendering", () => {
  test("preserves paragraph markup as ordered Reader paragraphs", () => {
    expect(paragraphsFromHtml("<p>First.</p><p>Second.</p>")).toEqual(["First.", "Second."]);
  });

  test("preserves readable canonical text when a package uses no paragraph elements", () => {
    expect(paragraphsFromHtml("<article><h2>Opening</h2><div>Readable body</div></article>")).toEqual(["Opening", "Readable body"]);
  });

  test("mixed canonical structures retain order, semantics, Bengali verse and code whitespace", () => {
    const container = document.createElement("div");
    const root = createRoot(container);
    act(() => root.render(<ReaderContent html={'<h2>Opening</h2><p>First <em>paragraph</em>.</p><ol><li>First item<ul><li>Nested item</li></ul></li><li>Second item</li></ol><pre><code>if ready:\n    read()\n\n    keep_indent()</code></pre><blockquote>প্রথম পঙ্‌ক্তি<br>দ্বিতীয় পঙ্‌ক্তি</blockquote><table><caption>Contents</caption><tbody><tr><th>One</th><td>Two</td></tr></tbody></table><p><a href="/library">Library</a></p>'} />));
    expect(container.querySelector("h2").textContent).toBe("Opening");
    expect(container.querySelector("em").textContent).toBe("paragraph");
    expect(container.querySelectorAll("ol > li")).toHaveLength(2);
    expect(container.querySelector("ol ul li").textContent).toBe("Nested item");
    expect(container.querySelector("pre").textContent).toBe("if ready:\n    read()\n\n    keep_indent()");
    expect(container.querySelector("blockquote br")).not.toBeNull();
    expect(container.querySelector("blockquote").textContent).toContain("প্রথম পঙ্‌ক্তি");
    expect(container.querySelector('[role="region"] table caption').textContent).toBe("Contents");
    expect(container.querySelector("a").getAttribute("href")).toBe("/library");
    expect(container.textContent.indexOf("Opening")).toBeLessThan(container.textContent.indexOf("Second item"));
    act(() => root.unmount());
  });

  test("source HTML cannot inject active scripts, controls, event attributes or unsafe links", () => {
    const container = document.createElement("div");
    const root = createRoot(container);
    act(() => root.render(<ReaderContent html={'<p onclick="attack()">Safe <strong>text</strong></p><script>attack()</script><iframe src="/private"></iframe><form><input></form><a href="javascript:attack()">Unsafe link</a><img src="data:image/svg+xml,evil" onerror="attack()"><a href="https://example.org">Safe link</a>'} />));
    expect(container.querySelector("script,iframe,form,input,[onclick],[onerror],img")).toBeNull();
    expect(container.querySelector("a").hasAttribute("href")).toBe(false);
    expect(container.querySelectorAll("a")[1].getAttribute("href")).toBe("https://example.org");
    expect(container.textContent).toContain("Safe text");
    expect(container.textContent).not.toContain("attack()");
    act(() => root.unmount());
  });
});
