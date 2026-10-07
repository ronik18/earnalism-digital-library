import React, { act } from "react";
jest.mock("react-router-dom", () => ({ Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>, NavLink: ({ to, children, className, ...props }) => <a href={to} className={typeof className === "function" ? className({ isActive: false }) : className} {...props}>{children}</a>, useLocation: () => ({ pathname: "/reader/example", search: "" }), useNavigate: () => jest.fn() }), { virtual: true });
import { createRoot } from "react-dom/client";
import ReaderExperienceV2, { READER_V2_FIXTURE } from "./ReaderExperienceV2";
import { READER_SETTINGS_STORAGE_KEY } from "../../lib/readerSettings";
import { readerNotebookKey } from "../../lib/readerNotebook";

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
    jest.spyOn(window, "scrollTo").mockImplementation(() => {});
    // JSDOM has no layout engine. Browser acceptance separately measures real dimensions.
    jest.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(600);
    jest.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(600);
    localStorage.removeItem(READER_SETTINGS_STORAGE_KEY);
    localStorage.removeItem(readerNotebookKey(model.title));
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });
  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    jest.restoreAllMocks();
    localStorage.removeItem(READER_SETTINGS_STORAGE_KEY);
  });
  const render = (props = {}) => act(() => root.render(<ReaderExperienceV2 model={model} {...props} />));
  const click = (element) => act(() => element.dispatchEvent(new MouseEvent("click", { bubbles: true })));
  const button = (text) => [...container.querySelectorAll("button")].find((element) => element.textContent.trim() === text);
  const change = (select, value) => act(() => {
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });

  test("image-only navigation, selector and bookmarks use structural anchors", async () => {
    jest.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(function () { return this.classList.contains('reader-v2__pagination-measure') ? this.querySelectorAll('img').length * 400 : 0; });
    await act(async () => root.render(<ReaderExperienceV2 model={{ ...model, slug: 'image-test', sourceRevision: 'images-v1', content: <><img src="/fixture-one.png" alt="First image" /><img src="/fixture-two.png" alt="Second image" /></> }} />));
    const selector = container.querySelector('select[aria-label="Go to page"]');
    expect(selector.options).toHaveLength(2);
    click(container.querySelector('.reader-v2__page-arrow--next'));
    expect(container.querySelector('[data-testid="reader-reading-text"] img').alt).toBe('Second image');
    expect(container.querySelector('[data-testid="reader-page-content"]').className).toContain('--next');
    click(container.querySelector('.reader-v2__toolbar button[aria-label="Bookmark this page"]'));
    expect(JSON.parse(localStorage.getItem(readerNotebookKey('image-test'))).bookmarkAnchors[0].anchor.offset).toBe('media:1');
    click(container.querySelector('.reader-v2__page-arrow--previous'));
    expect(container.querySelector('[data-testid="reader-reading-text"] img').alt).toBe('First image');
    change(selector, '1');
    expect(container.querySelector('[data-testid="reader-reading-text"] img').alt).toBe('Second image');
  });

  test("captioned media selector distinguishes identical offsets in different source chunks", async () => {
    jest.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(function () { return this.classList.contains('reader-v2__pagination-measure') ? this.querySelectorAll('figure').length * 400 : 0; });
    const plan = { key: 'captioned-chapter', chapterId: 'captioned', chapterTitle: 'Captioned chapter' };
    await act(async () => root.render(<ReaderExperienceV2 model={{ ...model,
      sourceRevision: 'captions-v1', authorizedChapter: { plan, textLength: 2, sources: [{ page: 1, start: 0, end: 1, revision: 'captions-v1' }, { page: 2, start: 1, end: 2, revision: 'captions-v1' }] }, authorizedBookPlans: [plan],
      sourceAnchorForOffset: offset => ({ page: offset + 1, offset: 0, revision: 'captions-v1' }),
      content: <><figure><img src="/one.png" alt="First figure" /><figcaption>A</figcaption></figure><figure><img src="/two.png" alt="Second figure" /><figcaption>B</figcaption></figure></>,
    }} />));
    const selector = container.querySelector('select[aria-label="Go to page"]');
    expect(selector.value).toBe('captioned-chapter:0');
    click(container.querySelector('.reader-v2__page-arrow--next'));
    expect(container.querySelector('[data-testid="reader-reading-text"] img').alt).toBe('Second figure');
    expect(selector.value).toBe('captioned-chapter:1');
    click(container.querySelector('.reader-v2__page-arrow--previous'));
    expect(selector.value).toBe('captioned-chapter:0');
  });

  test("side arrows use canonical requests and preserve focus on page turns", () => {
    const onRequestPage = jest.fn();
    render({ model: { ...model, canonicalPage: 1 }, onRequestPage });
    const previous = container.querySelector('.reader-v2__page-arrow--previous');
    const next = container.querySelector('.reader-v2__page-arrow--next');
    expect(previous.disabled).toBe(true);
    next.focus();
    click(next);
    expect(onRequestPage).toHaveBeenCalledWith(2);
    render({ model: { ...model, canonicalPage: 2 }, onRequestPage });
    expect(document.activeElement).toBe(next);
    expect(container.querySelector('[data-testid="reader-page-content"]').className).toContain('--next');
    render({ model: { ...model, canonicalPage: 1 }, onRequestPage });
    expect(container.querySelector('[data-testid="reader-page-content"]').className).toContain('--previous');
  });

  test("keyboard turns exclude editing and interactive controls", () => {
    const onRequestPage = jest.fn();
    render({ model: { ...model, canonicalPage: 1 }, onRequestPage });
    for (const tag of ['input', 'textarea', 'select', 'button', 'a', 'audio', 'video']) {
      const target = document.createElement(tag);
      container.appendChild(target);
      act(() => target.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })));
      target.remove();
    }
    const slider = document.createElement('div');
    slider.setAttribute('role', 'slider'); container.appendChild(slider);
    act(() => slider.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })));
    slider.remove();
    expect(onRequestPage).not.toHaveBeenCalled();
    act(() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })));
    expect(onRequestPage).toHaveBeenCalledWith(2);
  });

  test("only a valid edition licence enables the delivered-text print marker", () => {
    render();
    expect(container.querySelector('[data-licensed-text="true"]')).toBeNull();
    const book = { slug: "licensed-title", text_license: {
      schema_version: "earnalism.text-license.v1", slug: "licensed-title",
      license: "CC-BY-SA-4.0", license_url: "https://creativecommons.org/licenses/by-sa/4.0/",
      attribution: "Wikisource contributors", changes: "Formatting", scope: "Transcription only", disclaimer: "No warranties",
      source_url: "https://bn.wikisource.org/w/index.php?oldid=123",
      contributors_url: "https://bn.wikisource.org/w/index.php?action=history",
    } };
    render({ model: { ...model, book } });
    expect(container.querySelector('[data-licensed-text="true"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="text-license-notice"]')).toBeTruthy();
    render({ model: { ...model, book: { ...book, slug: "another-edition" } } });
    expect(container.querySelector('[data-licensed-text="true"]')).toBeNull();
  });

  test("bookmarks persist and requests for protected pages still use route authorization", () => {
    localStorage.setItem(readerNotebookKey(model.title), JSON.stringify({ notes: [], bookmarks: [4] }));
    const onRequestPage = jest.fn();
    render({ onRequestPage });
    click(button("Bookmarks"));
    click(button("Page 4"));
    expect(onRequestPage).toHaveBeenCalledWith(4);
    expect(container.querySelector('[data-testid="reader-page-content"]').textContent).not.toContain("Page 4 content");
    click(container.querySelector('.reader-v2__toolbar button[aria-label="Bookmark this page"]'));
    expect(JSON.parse(localStorage.getItem(readerNotebookKey(model.title))).bookmarks).toEqual([1, 4]);
  });

  test("a visual fixture never presents synthetic account progress or Reading Pass balance", () => {
    const onNavigate = jest.fn();
    render({ model: { ...model, visualFixture: true, progress: null, readingTime: "", readingPass: "Sign in to check Reading Pass balance" }, onNavigate });
    expect(container.textContent).not.toContain("Reading Progress");
    expect(container.textContent).not.toContain("215 minutes left");
    expect(button("Sign in to check balance")).toBeTruthy();
    click(button("Sign in to check balance"));
    expect(onNavigate).toHaveBeenCalledWith("signin");
  });

  test("the Reader enters at the masthead and page turns preserve keyboard focus and scroll", () => {
    render();
    expect(document.activeElement).toBe(container.querySelector("#reader-v2-title"));
    expect(container.querySelector("#reader-v2-title").tabIndex).toBe(-1);
    expect(container.querySelector('.reader-v2__toolbar button[aria-label="Reader settings"]').getAttribute("aria-label")).toBe("Reader settings");
    expect(window.scrollTo).toHaveBeenCalledTimes(1);
    expect(window.scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: "instant" });
    const selector = container.querySelector('select[aria-label="Go to page"]');
    selector.focus();
    render({ model: { ...model, readingPass: "214 minutes left" } });
    expect(document.activeElement).toBe(selector);
    expect(window.scrollTo).toHaveBeenCalledTimes(1);
    render({ model: { ...model, canonicalPage: 2 } });
    expect(document.activeElement).toBe(selector);
    expect(window.scrollTo).toHaveBeenCalledTimes(1);
    expect(window.scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: "instant" });
  });

  test("immersive primary navigation keeps real links and runs the route settlement callback", () => {
    const onNavigate = jest.fn();
    render({ onNavigate });
    const desktopLibrary = container.querySelector('.premium-header-nav--desktop a[data-nav-key="library"]');
    expect(desktopLibrary.getAttribute("href")).toBe("/library");
    click(desktopLibrary);
    expect(onNavigate).toHaveBeenCalledWith("library", "/library");

    click(container.querySelector('[data-testid="mobile-menu-toggle"][aria-label="Open menu"]'));
    const menuLibrary = container.querySelector('#mobile-menu a[data-nav-key="library"]');
    expect(menuLibrary.getAttribute("href")).toBe("/library");
    click(menuLibrary);
    expect(onNavigate).toHaveBeenLastCalledWith("library", "/library");

    click(container.querySelector('[data-testid="mobile-menu-toggle"][aria-label="Open menu"]'));
    const signIn = container.querySelector('#mobile-menu a[data-testid="mobile-nav-sign-in"]');
    expect(signIn.getAttribute("href")).toBe("/login");
    click(signIn);
    expect(onNavigate).toHaveBeenLastCalledWith("signin", "/login");
  });

  test("Library and contents request their actual destinations and mark the current page", () => {
    const onRequestPage = jest.fn();
    const onNavigate = jest.fn();
    render({ onRequestPage, onNavigate });
    click(container.querySelector('.premium-header-nav--desktop [data-nav-key="library"]'));
    expect(onNavigate).toHaveBeenCalledWith("library", "/library");
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
    expect(container.querySelector('select[aria-label="Go to page"]').options.length).toBe(1);
    click(button("Page 3"));
    expect(onRequestPage).toHaveBeenLastCalledWith(3);
    render({ model: { ...model, canonicalPage: 4 }, access: { authorized: true }, onRequestPage });
    expect(button("End of book").disabled).toBe(true);
    click(button("End of book"));
    expect(onRequestPage).toHaveBeenCalledTimes(2);
    click(button("Previous page"));
    expect(onRequestPage).toHaveBeenLastCalledWith(3, "end");
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
    click(container.querySelector('.premium-header-nav--desktop [data-nav-key="library"]'));
    expect(onNavigate).toHaveBeenCalledWith("library", "/library");
  });

  test("both responsive font controls use the bounded rem contract and persist an explicit preference", () => {
    render();
    const text = container.querySelector('[data-testid="reader-reading-text"]');
    expect(container.querySelector("article").getAttribute("data-reader-theme")).toBe("beige");
    expect(text.style.fontSize).toBe("1.125rem");
    expect(text.style.lineHeight).toBe("1.375");
    expect(text.style.fontFamily).toContain("EB Garamond");
    click(container.querySelector('.reader-v2__toolbar button[aria-label="Increase text size"]'));
    expect(text.style.fontSize).toBe("1.25rem");
    click(container.querySelector('.reader-v2__mobile-topbar button[aria-label="Decrease text size"]'));
    expect(text.style.fontSize).toBe("1.125rem");
    expect(JSON.parse(localStorage.getItem(READER_SETTINGS_STORAGE_KEY)).fontSizeIdx).toBe(1);
    expect(JSON.parse(localStorage.getItem(READER_SETTINGS_STORAGE_KEY)).readerTextSizeRem).toBe(1.125);
  });

  test("settings change theme and spacing locally and survive remount without navigating away", () => {
    const onNavigate = jest.fn();
    render({ onNavigate });
    const settingsToggle = container.querySelector('.reader-v2__toolbar button[aria-label="Reader settings"]');
    click(settingsToggle);
    const selects = container.querySelectorAll("#reader-v2-settings select");
    change(selects[0], "sepia");
    change(selects[2], "airy");
    expect(container.querySelector("article").getAttribute("data-reader-theme")).toBe("sepia");
    expect(container.querySelector('[data-testid="reader-reading-text"]').style.lineHeight).toBe("1.51");
    click(button("Close preferences"));
    expect(container.querySelector("#reader-v2-settings")).toBeNull();
    expect(document.activeElement).toBe(settingsToggle);
    expect(onNavigate).not.toHaveBeenCalled();
    act(() => root.unmount());
    root = createRoot(container);
    render();
    expect(container.querySelector("article").getAttribute("data-reader-theme")).toBe("sepia");
    expect(container.querySelector('[data-testid="reader-reading-text"]').style.lineHeight).toBe("1.51");
  });

  test("uses language-specific literary defaults and an accessible typography reset", () => {
    render({ model: { ...model, language: "bn", content: <p>বাংলা পাঠ্য</p> } });
    const text = container.querySelector('[data-testid="reader-reading-text"]');
    expect(container.querySelector("article").lang).toBe("bn");
    expect(text.style.fontSize).toBe("1.125rem");
    expect(text.style.lineHeight).toBe("1.4");
    expect(text.style.fontWeight).toBe("500");
    expect(text.style.fontFamily).toContain("Noto Sans Bengali");

    click(container.querySelector('.reader-v2__toolbar button[aria-label="Reader settings"]'));
    const selects = container.querySelectorAll("#reader-v2-settings select");
    change(selects[1], "2");
    change(selects[3], "sans");
    expect(text.style.fontSize).toBe("2rem");
    expect(text.style.fontFamily).toContain("Noto Sans Bengali");
    click(button("Reset typography"));
    expect(text.style.fontSize).toBe("1.125rem");
    expect(text.style.fontFamily).toContain("Noto Sans Bengali");
    expect(JSON.parse(localStorage.getItem(READER_SETTINGS_STORAGE_KEY)).readerTextSizeRem).toBeNull();
  });

  test("valid saved typography and theme take precedence over new defaults", () => {
    localStorage.setItem(READER_SETTINGS_STORAGE_KEY, JSON.stringify({
      theme: "beige", lineSpacingMode: "relaxed", readerTypographyVersion: 2,
      readerTextSizeRem: 1.5, readerFontFamilyPreference: "serif",
    }));
    render();
    const text = container.querySelector('[data-testid="reader-reading-text"]');
    expect(container.querySelector("article").getAttribute("data-reader-theme")).toBe("beige");
    expect(text.style.fontSize).toBe("1.5rem");
    expect(text.style.lineHeight).toBe("1.44");
    expect(text.style.fontFamily).toContain("EB Garamond");
  });

  test("preference changes do not request another canonical page", () => {
    const onRequestPage = jest.fn();
    render({ onRequestPage });
    click(container.querySelector('.reader-v2__toolbar button[aria-label="Increase text size"]'));
    click(container.querySelector('.reader-v2__toolbar button[aria-label="Reader settings"]'));
    const selects = container.querySelectorAll("#reader-v2-settings select");
    change(selects[0], "sepia");
    change(selects[2], "relaxed");
    expect(onRequestPage).not.toHaveBeenCalled();
  });

  test("structured content preserves formatting without importing the fixture illustration", () => {
    render({ model: { ...model, content: <><h2>Chapter heading</h2><p>A <em>faithful</em> passage.</p><pre><code>print("hello")</code></pre></>, statusMessage: "Saved your place." } });
    const text = container.querySelector('[data-testid="reader-reading-text"]');
    expect(text.querySelector("em").textContent).toBe("faithful");
    expect(text.querySelector("pre code").textContent).toBe('print("hello")');
    expect(container.querySelector(".reader-v2__illustration")).toBeNull();
    expect(container.querySelector('[role="status"]').textContent).toBe("Saved your place.");
  });

  test("keeps the text measure in a centered reading column", () => {
    render();
    const text = container.querySelector('[data-testid="reader-reading-text"]');
    expect(text.classList).toContain("reader-v2__body");
    expect(container.querySelector("article").classList).toContain("reader-v2__canvas");
  });
});
