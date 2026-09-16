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

  test("mixed paragraphs do not discard headings, list items, code or Bengali verse", () => {
    const container = document.createElement("div");
    const root = createRoot(container);
    act(() => root.render(<ReaderContent html={'<h2>Opening</h2><p>First <em>paragraph</em>.</p><ul><li>List entry</li></ul><pre><code>if ready:\n    read()</code></pre><blockquote>প্রথম পঙ্‌ক্তি<br>দ্বিতীয় পঙ্‌ক্তি</blockquote>'} />));
    expect(container.querySelector("h2").textContent).toBe("Opening");
    expect(container.querySelector("em").textContent).toBe("paragraph");
    expect(container.querySelector("li").textContent).toBe("List entry");
    expect(container.querySelector("pre").textContent).toBe("if ready:\n    read()");
    expect(container.querySelector("blockquote br")).not.toBeNull();
    expect(container.querySelector("blockquote").textContent).toContain("প্রথম পঙ্‌ক্তি");
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
