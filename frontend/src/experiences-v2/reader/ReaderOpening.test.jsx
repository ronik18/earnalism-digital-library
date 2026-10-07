import React, { act } from "react";
import { createRoot } from "react-dom/client";
import ReaderOpening from "./ReaderOpening";
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container;
beforeEach(() => { jest.useFakeTimers(); container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); jest.useRealTimers(); });
const render = props => act(() => root.render(<ReaderOpening {...props} />));
test("canonical brand line and accessible initial status", () => {
  render({}); expect(container.textContent).toContain("A quiet page, opening into another world.");
  expect(container.querySelector('[role="status"]').textContent).toContain("Opening reader");
  expect(container.querySelector('[aria-hidden="true"]')).not.toBeNull();
  expect(container.querySelector("img")).toBeNull();
});
test("personalizes only with supplied metadata", () => {
  render({ book: { public_title: "A Ghost Story", author: "Mark Twain" } });
  expect(container.querySelector("h1").textContent).toBe("A Ghost Story");
  expect(container.textContent).toContain("by Mark Twain");
  expect(container.querySelector('[role="status"]').textContent).toContain("Opening A Ghost Story");
});
test("slow copy is a status change, not a failure or readiness timer", () => {
  render({}); act(() => jest.advanceTimersByTime(3000));
  expect(container.textContent).toContain("Still preparing your page");
  expect(container.querySelector('[role="alert"]')).toBeNull();
});
test("actual failure exposes retry and library recovery without progress", () => {
  const onRetry = jest.fn(), onLibrary = jest.fn(); render({ failed: true, onRetry, onLibrary });
  expect(container.querySelector('[role="alert"]')).not.toBeNull();
  expect(container.textContent).toContain("We couldn’t open this page.");
  expect(container.querySelector('.reader-opening__progress')).toBeNull();
  act(() => container.querySelector('.reader-opening__retry').click());
  act(() => container.querySelector('.reader-opening__back').click());
  expect(onRetry).toHaveBeenCalledTimes(1); expect(onLibrary).toHaveBeenCalledTimes(1);
});
test("loading escape remains reachable with a semantic button", () => {
  const onLibrary = jest.fn(); render({ onLibrary });
  const button = container.querySelector("button"); expect(button.textContent).toBe("Back to Library");
  act(() => button.click()); expect(onLibrary).toHaveBeenCalledTimes(1);
});
test("unmount clears the slow-load timer immediately", () => {
  render({}); expect(jest.getTimerCount()).toBe(1); act(() => root.render(null)); expect(jest.getTimerCount()).toBe(0);
});
