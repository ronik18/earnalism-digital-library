import React, { act, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import ListenerExperienceV2 from "../listener/ListenerExperienceV2";

jest.mock("../shared/ReleaseTruthAdapter", () => ({
  listenerReleasePresentation: (book, { fixture }) => ({
    canRender: book.renderable !== false, fixture, title: "Isolated approved package",
    author: "Test author", chapterLabel: "Chapter 1", durationSeconds: 20,
  }),
}));
jest.mock("../shared/ExperienceHeader", () => () => null);
jest.mock("../shared/ExperienceBottomNavigation", () => () => null);
jest.mock("../../components/BookCoverImage", () => () => null);

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
// Playback admission uses the current onBeforePlayback contract; the component owns no interval.
const version = `sha256-${"a".repeat(64)}`;
const book = { slug: "isolated-listener-lifecycle", chapters: [{ id: "c1", title: "Chapter 1" }] };
const audioManifest = {
  valid: true, packageVersion: version, durationMs: 20000,
  tracks: [{ chapterId: "c1", chunks: [0, 1].map(index => ({
    segmentId: `segment-${index + 1}`, audioUrl: `/api/isolated/segment-${index + 1}`,
    cumulativeStartMs: index * 10000, durationMs: 10000, startWord: index * 10, endWord: index * 10 + 9,
  })) }],
};
let root, container, media, pauseStates, activeIntervals;
const deferred = () => { let resolve; const promise = new Promise(yes => { resolve = yes; }); return { promise, resolve }; };
const state = audio => { if (!media.has(audio)) media.set(audio, { paused: true, time: 0 }); return media.get(audio); };
async function render(extra = {}, strict = false) {
  const child = <ListenerExperienceV2 book={book} audioManifest={audioManifest} access={{ authorized: true }} {...extra} />;
  await act(async () => root.render(strict ? <StrictMode>{child}</StrictMode> : child));
}
async function click(label) {
  const button = container.querySelector(`button[aria-label="${label}"]`);
  expect(button).not.toBeNull();
  await act(async () => button.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}
async function metadata(audio) { await act(async () => audio.dispatchEvent(new Event("loadedmetadata"))); }
async function unmount() { await act(async () => root.unmount()); root = null; }

beforeEach(() => {
  jest.useFakeTimers(); media = new WeakMap(); pauseStates = []; activeIntervals = new Set(); localStorage.clear();
  const setInterval = window.setInterval, clearInterval = window.clearInterval;
  jest.spyOn(window, "setInterval").mockImplementation((callback, delay) => {
    const timer = setInterval(callback, delay); activeIntervals.add(timer); return timer;
  });
  jest.spyOn(window, "clearInterval").mockImplementation(timer => {
    activeIntervals.delete(timer); clearInterval(timer);
  });
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
  jest.spyOn(HTMLMediaElement.prototype, "paused", "get").mockImplementation(function () { return state(this).paused; });
  jest.spyOn(HTMLMediaElement.prototype, "readyState", "get").mockReturnValue(3);
  jest.spyOn(HTMLMediaElement.prototype, "duration", "get").mockReturnValue(10);
  jest.spyOn(HTMLMediaElement.prototype, "currentTime", "get").mockImplementation(function () { return state(this).time; });
  jest.spyOn(HTMLMediaElement.prototype, "currentTime", "set").mockImplementation(function (value) { state(this).time = value; });
  jest.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(function () {
    state(this).paused = false; this.dispatchEvent(new Event("play")); return Promise.resolve();
  });
  jest.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(function () {
    pauseStates.push({ node: this, connected: this.isConnected });
    const wasPlaying = !state(this).paused; state(this).paused = true;
    if (wasPlaying) this.dispatchEvent(new Event("pause"));
  });
});
afterEach(async () => {
  if (root) await unmount(); container.remove(); jest.restoreAllMocks(); jest.useRealTimers();
});

test("media admitted after mount is paused on unmount even after React detaches its ref", async () => {
  await render({ access: { authorized: false } });
  expect(container.querySelector("audio")).toBeNull();
  await render();
  const audio = container.querySelector("audio"); await metadata(audio);
  await click("Play approved audiobook");
  expect(audio.paused).toBe(false);
  expect(activeIntervals.size).toBe(0);
  await unmount();
  expect(pauseStates).toContainEqual({ node: audio, connected: false });
  expect(audio.paused).toBe(true);
  expect(activeIntervals.size).toBe(0);
});

test("loss of admission pauses the owned node without leaving audio running after detachment", async () => {
  await render(); const audio = container.querySelector("audio"); await metadata(audio);
  await click("Play approved audiobook");
  await render({ access: { authorized: false } });
  expect(container.querySelector("audio")).toBeNull();
  expect(pauseStates).toContainEqual({ node: audio, connected: false });
  expect(audio.paused).toBe(true);
});

test("segment transitions, speed and time renders retain media ownership and no added monitor", async () => {
  const prepare = jest.fn().mockResolvedValue(undefined);
  await render({ onBeforePlayback: prepare });
  const audio = container.querySelector("audio"); await metadata(audio); await click("Play approved audiobook");
  const pauses = pauseStates.length;
  state(audio).time = 3;
  await act(async () => audio.dispatchEvent(new Event("timeupdate")));
  const speed = container.querySelector("select");
  await act(async () => { speed.value = "1.25"; speed.dispatchEvent(new Event("change", { bubbles: true })); });
  await act(async () => audio.dispatchEvent(new Event("ended")));
  expect(container.querySelector("audio")).toBe(audio);
  expect(audio.dataset.segmentId).toBe("segment-2");
  await metadata(audio);
  expect(audio.playbackRate).toBe(1.25);
  expect(pauseStates).toHaveLength(pauses);
  expect(activeIntervals.size).toBe(0);
});

test("a pending preparation resolved after unmount cannot play the detached node", async () => {
  const pending = deferred(); const prepare = jest.fn(() => pending.promise);
  await render({ onBeforePlayback: prepare });
  const audio = container.querySelector("audio"); await metadata(audio);
  await click("Play approved audiobook");
  expect(prepare).toHaveBeenCalledTimes(1);
  await unmount();
  await act(async () => pending.resolve());
  expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
  expect(audio.paused).toBe(true);
  expect(activeIntervals.size).toBe(0);
});

test("Stop invalidates an earlier preparation instead of letting its completion play", async () => {
  const pending = deferred();
  await render({ onBeforePlayback: () => pending.promise });
  const audio = container.querySelector("audio"); await metadata(audio); await click("Play approved audiobook");
  const stop = [...container.querySelectorAll("button")].find(button => button.textContent === "Stop listening");
  await act(async () => stop.dispatchEvent(new MouseEvent("click", { bubbles: true })));
  await act(async () => pending.resolve());
  expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
  expect(audio.paused).toBe(true);
});

test("StrictMode replay cleans captured media and leaves one live monitor, then none on exit", async () => {
  await render({}, true);
  const audio = container.querySelector("audio");
  expect(pauseStates.some(value => value.node === audio)).toBe(true);
  expect(activeIntervals.size).toBe(0);
  await metadata(audio); await click("Play approved audiobook");
  await unmount();
  expect(audio.paused).toBe(true);
  expect(activeIntervals.size).toBe(0);
});
