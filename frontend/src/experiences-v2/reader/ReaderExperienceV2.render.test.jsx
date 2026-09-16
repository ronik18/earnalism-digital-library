import React, { act } from "react";
import { createRoot } from "react-dom/client";
import ReaderExperienceV2, { READER_V2_FIXTURE } from "./ReaderExperienceV2";
import { READER_SETTINGS_STORAGE_KEY } from "../../lib/readerSettings";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const model = {
  ...READER_V2_FIXTURE,
  illustration: undefined,
  contents: [1, 2, 3, 4].map((page) => ({ page, label: `Page ${page}` })),
};

describe("ReaderExperienceV2 customer controls", () => {
  let container;
  let root;
  beforeEach(() => {
    localStorage.removeItem(READER_SETTINGS_STORAGE_KEY);
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });
  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    localStorage.removeItem(READER_SETTINGS_STORAGE_KEY);
  });
  const render = (props = {}) => act(() => root.render(<ReaderExperienceV2 model={model} {...props} />));
  const click = (element) => act(() => element.dispatchEvent(new MouseEvent("click", { bubbles: true })));
  const button = (text) => [...container.querySelectorAll("button")].find((element) => element.textContent.trim() === text);
  const change = (select, value) => act(() => {
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });

  test("a newly opened page resets reading focus and scroll while heartbeat updates preserve them", () => {
    const previousScrollIntoView = HTMLElement.prototype.scrollIntoView;
    const scrollIntoView = jest.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;
    try {
      render();
      expect(document.activeElement).toBe(container.querySelector("#reader-v2-title"));
      expect(scrollIntoView).toHaveBeenCalledTimes(1);
      const selector = container.querySelector('select[aria-label="Go to page"]');
      selector.focus();
      render({ model: { ...model, readingPass: "214 minutes left" } });
      expect(document.activeElement).toBe(selector);
      expect(scrollIntoView).toHaveBeenCalledTimes(1);
      render({ model: { ...model, canonicalPage: 2 } });
      expect(document.activeElement).toBe(container.querySelector("#reader-v2-title"));
      expect(scrollIntoView).toHaveBeenCalledTimes(2);
    } finally {
      if (previousScrollIntoView) HTMLElement.prototype.scrollIntoView = previousScrollIntoView;
      else delete HTMLElement.prototype.scrollIntoView;
    }
  });

  test("Library and contents request their actual destinations and mark the current page", () => {
    const onRequestPage = jest.fn();
    const onNavigate = jest.fn();
    render({ onRequestPage, onNavigate });
    click(container.querySelector(".experience-header__link"));
    expect(onNavigate).toHaveBeenCalledWith("library");
    click(button("Page 2"));
    expect(onRequestPage).toHaveBeenCalledWith(2);
    render({ model: { ...model, canonicalPage: 2 }, onRequestPage, onNavigate });
    expect(button("Page 2").getAttribute("aria-current")).toBe("page");
    expect(button("Page 1").hasAttribute("aria-current")).toBe(false);
    click(button("Page 2"));
    expect(onRequestPage).toHaveBeenCalledTimes(1);
  });

  test("the page selector and previous/next controls respect both book boundaries", () => {
    const onRequestPage = jest.fn();
    render({ onRequestPage });
    expect(button("Previous page").disabled).toBe(true);
    click(button("Next page"));
    expect(onRequestPage).toHaveBeenLastCalledWith(2);
    change(container.querySelector('select[aria-label="Go to page"]'), "3");
    expect(onRequestPage).toHaveBeenLastCalledWith(3);
    render({ model: { ...model, canonicalPage: 4 }, access: { authorized: true }, onRequestPage });
    expect(button("End of book").disabled).toBe(true);
    click(button("End of book"));
    expect(onRequestPage).toHaveBeenCalledTimes(2);
    click(button("Previous page"));
    expect(onRequestPage).toHaveBeenLastCalledWith(3);
    expect(container.textContent).toContain("You have reached the end of this book.");
  });

  test("crossing the free preview asks the route for authorization without blocking the request", () => {
    const onRequestPage = jest.fn();
    render({ model: { ...model, canonicalPage: 3 }, onRequestPage });
    click(button("Use Reading Time to Continue"));
    expect(onRequestPage).toHaveBeenCalledWith(4);
    render({ model: { ...model, canonicalPage: 3 }, access: { authorized: true }, onRequestPage });
    expect(button("Next page")).toBeDefined();
  });

  test("pending navigation disables duplicate page requests while leaving Library usable", () => {
    const onRequestPage = jest.fn();
    const onNavigate = jest.fn();
    render({ access: { busy: true }, onRequestPage, onNavigate });
    click(button("Next page"));
    click(button("Page 2"));
    expect(container.querySelector('select[aria-label="Go to page"]').disabled).toBe(true);
    expect(onRequestPage).not.toHaveBeenCalled();
    click(container.querySelector(".experience-header__link"));
    expect(onNavigate).toHaveBeenCalledWith("library");
  });

  test("both responsive font controls update actual text and persist the existing preference", () => {
    render();
    const text = container.querySelector('[data-testid="reader-reading-text"]');
    expect(text.style.fontSize).toBe("18px");
    click(container.querySelector('.reader-v2__toolbar button[aria-label="Increase text size"]'));
    expect(text.style.fontSize).toBe("20px");
    click(container.querySelector('.reader-v2__mobile-topbar button[aria-label="Decrease text size"]'));
    expect(text.style.fontSize).toBe("18px");
    expect(JSON.parse(localStorage.getItem(READER_SETTINGS_STORAGE_KEY)).fontSizeIdx).toBe(1);
  });

  test("settings change theme and spacing locally and survive remount without navigating away", () => {
    const onNavigate = jest.fn();
    render({ onNavigate });
    const settingsToggle = container.querySelector('.reader-v2__toolbar button[aria-label="Reader settings"]');
    click(settingsToggle);
    const selects = container.querySelectorAll("#reader-v2-settings select");
    change(selects[0], "dark");
    change(selects[2], "airy");
    expect(container.querySelector("article").getAttribute("data-reader-theme")).toBe("dark");
    expect(container.querySelector('[data-testid="reader-reading-text"]').style.lineHeight).toBe("2.02");
    click(button("Close preferences"));
    expect(container.querySelector("#reader-v2-settings")).toBeNull();
    expect(document.activeElement).toBe(settingsToggle);
    expect(onNavigate).not.toHaveBeenCalled();
    act(() => root.unmount());
    root = createRoot(container);
    render();
    expect(container.querySelector("article").getAttribute("data-reader-theme")).toBe("dark");
    expect(container.querySelector('[data-testid="reader-reading-text"]').style.lineHeight).toBe("2.02");
  });

  test("structured content preserves formatting without importing the fixture illustration", () => {
    render({ model: { ...model, content: <><h2>Chapter heading</h2><p>A <em>faithful</em> passage.</p><pre><code>print("hello")</code></pre></>, statusMessage: "Saved your place." } });
    const text = container.querySelector('[data-testid="reader-reading-text"]');
    expect(text.querySelector("em").textContent).toBe("faithful");
    expect(text.querySelector("pre code").textContent).toBe('print("hello")');
    expect(container.querySelector(".reader-v2__illustration")).toBeNull();
    expect(container.querySelector('[role="status"]').textContent).toBe("Saved your place.");
  });
});
