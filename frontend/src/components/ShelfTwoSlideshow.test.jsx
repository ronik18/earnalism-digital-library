import React, { act } from "react";
import { createRoot } from "react-dom/client";
import ShelfTwoSlideshow, { chunkBooks, shouldAutoplayShelfTwo } from "./ShelfTwoSlideshow";
import { buildShelfTwoBooks } from "../lib/shelfTwoBooks";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function setReducedMotion(matches) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: jest.fn().mockImplementation((query) => ({
      matches: query.includes("prefers-reduced-motion") ? matches : false,
      media: query,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      addListener: jest.fn(),
      removeListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
}

function renderSlideshow(ui) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(ui);
  });
  return {
    container,
    cleanup() {
      act(() => root.unmount());
      container.remove();
    },
  };
}

describe("ShelfTwoSlideshow hotfix", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    setReducedMotion(false);
  });

  afterEach(() => {
    jest.useRealTimers();
    document.body.innerHTML = "";
  });

  test("builds a Bengali-led shelf with more than one eligible slide", () => {
    const books = buildShelfTwoBooks();
    const titles = books.map((book) => book.title).join(" ");

    expect(books.length).toBeGreaterThan(5);
    expect(chunkBooks(books).length).toBeGreaterThan(1);
    expect(shouldAutoplayShelfTwo({ slideCount: chunkBooks(books).length, isPaused: false, prefersReducedMotion: false })).toBe(true);
    expect(shouldAutoplayShelfTwo({ slideCount: chunkBooks(books).length, isPaused: false, prefersReducedMotion: true })).toBe(false);
    expect(titles).toMatch(/দুই বিঘা জমি|দেবদাস|পথের পাঁচালী/);
    expect(books[0].slug).not.toBe("dracula");
  });

  test("does not introduce Listen CTA, static audio paths, or audiobook status into the shelf data", () => {
    const serialized = JSON.stringify(buildShelfTwoBooks());

    expect(serialized).not.toMatch(/\bListen\b|Listen Now|paid Listen/i);
    expect(serialized).not.toMatch(/\/audio\//i);
    expect(serialized).not.toMatch(/AudioObject/i);
    expect(buildShelfTwoBooks().find((book) => book.slug === "a-ghost-story")).toBeUndefined();
  });

  test("autoplay advances when reduced motion is not requested", () => {
    const books = buildShelfTwoBooks();
    const { container, cleanup } = renderSlideshow(
      <ShelfTwoSlideshow books={books} autoplayIntervalMs={1000} />,
    );

    const track = container.querySelector("[data-testid='shelf-two-track']");
    expect(track.style.transform).toBe("translateX(-0%)");

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(track.style.transform).toBe("translateX(-100%)");
    cleanup();
  });

  test("reduced motion disables autoplay while preserving manual controls", () => {
    setReducedMotion(true);
    const books = buildShelfTwoBooks();
    const { container, cleanup } = renderSlideshow(
      <ShelfTwoSlideshow books={books} autoplayIntervalMs={1000} />,
    );

    const track = container.querySelector("[data-testid='shelf-two-track']");
    expect(track.style.transform).toBe("translateX(-0%)");

    act(() => {
      jest.advanceTimersByTime(3000);
    });
    expect(track.style.transform).toBe("translateX(-0%)");

    act(() => {
      container.querySelector(".shelf-two-arrow--next").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(track.style.transform).toBe("translateX(-100%)");

    act(() => {
      container.querySelector(".shelf-two-arrow--prev").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(track.style.transform).toBe("translateX(-0%)");
    cleanup();
  });
});
