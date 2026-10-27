import React, { act } from "react";
import { createRoot } from "react-dom/client";
const mockPlay = jest.fn();
let mockSeekSegment = "segment-1";
const mockTrack = { segmentId: "segment-1", audioUrl: "/api/reader/book/test/audiobook/segment-1", cumulativeStartMs: 0 };
jest.mock("react-router-dom", () => ({ Link: ({ to, children }) => <a href={to}>{children}</a>, NavLink: ({ to, children }) => <a href={to}>{children}</a>, useLocation: () => ({ pathname: "/listener/test" }), useNavigate: () => jest.fn() }), { virtual: true });
jest.mock("../shared/ReleaseTruthAdapter", () => ({ listenerReleasePresentation: () => ({ title: "Test", author: "Test", canRender: true, fixture: false }) }));
jest.mock("../../lib/audioPackageManifest", () => ({ selectAudioTrack: ({ preferredSegmentId }) => preferredSegmentId === "segment-2" ? { ...mockTrack, segmentId: "segment-2", audioUrl: "/api/reader/book/test/audiobook/segment-2" } : mockTrack, audioSegmentAtMediaPosition: () => ({ ...mockTrack, segmentId: mockSeekSegment, offsetSeconds: 0.5 }) }));
jest.mock("../../lib/audiobookPlayback", () => ({ loadAudiobookProgress: () => null, saveAudiobookProgress: jest.fn(), shouldPrefetchNextSegment: () => false, requestAudiobookPlayback: (...args) => mockPlay(...args) }));
import ListenerExperienceV2 from "../listener/ListenerExperienceV2";
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
test.each(["success", "denied", "unmounted", "cross-segment"])("media waits for active renewal: %s", async outcome => {
  mockPlay.mockReset(); mockPlay.mockResolvedValue();
  mockSeekSegment = outcome === "cross-segment" ? "segment-2" : "segment-1";
  const pause = jest.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  let resolve, reject;
  const before = jest.fn(() => new Promise((yes, no) => { resolve = yes; reject = no; }));
  const error = jest.fn();
  const container = document.createElement("div"); document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => { root.render(<ListenerExperienceV2 book={{ slug: "test" }} audioManifest={{ valid: true, packageVersion: "test", durationMs: 1000, tracks: [] }} access={{ authorized: true }} onBeforePlayback={before} onMediaError={error} />); });
  const seekSetter = jest.spyOn(HTMLMediaElement.prototype, "currentTime", "set");
  await act(async () => { container.querySelector('[aria-label="Forward 15 seconds"]').click(); });
  expect(seekSetter).not.toHaveBeenCalled();
  expect(container.querySelector("audio").getAttribute("src")).toContain("segment-1");
  await act(async () => { container.querySelector('[aria-label="Play approved audiobook"]').click(); });
  expect(before).toHaveBeenCalledTimes(1); expect(mockPlay).not.toHaveBeenCalled();
  if (outcome === "unmounted") await act(async () => { root.unmount(); });
  await act(async () => { if (outcome === "denied") reject(new Error("denied")); else resolve(); });
  if (outcome === "cross-segment") {
    const audio = container.querySelector("audio");
    expect(mockPlay).not.toHaveBeenCalled();
    expect(audio.getAttribute("src")).toContain("segment-2");
    Object.defineProperty(audio, "readyState", { configurable: true, value: 1 });
    await act(async () => { audio.dispatchEvent(new Event("loadedmetadata")); });
  }
  const succeeded = outcome === "success" || outcome === "cross-segment";
  expect(mockPlay).toHaveBeenCalledTimes(succeeded ? 1 : 0);
  expect(seekSetter).toHaveBeenCalledTimes(succeeded ? 1 : 0);
  if (succeeded) expect(seekSetter).toHaveBeenCalledWith(0.5);
  expect(error).toHaveBeenCalledTimes(outcome === "denied" ? 1 : 0);
  if (outcome !== "unmounted") await act(async () => { root.unmount(); });
  container.remove(); pause.mockRestore(); seekSetter.mockRestore();
});

test.each(['success','denied'])('playing cross-segment seek must renew before source change: %s',async outcome=>{
 mockPlay.mockReset();mockPlay.mockResolvedValue();mockSeekSegment='segment-2';
 const pause=jest.spyOn(HTMLMediaElement.prototype,'pause').mockImplementation(()=>{});
 let resolve,reject;const before=jest.fn(()=>new Promise((yes,no)=>{resolve=yes;reject=no}));const error=jest.fn();
 const container=document.createElement('div');document.body.appendChild(container);const root=createRoot(container);
 await act(async()=>root.render(<ListenerExperienceV2 book={{slug:'test'}} audioManifest={{valid:true,packageVersion:'test',durationMs:2000,tracks:[]}} access={{authorized:true}} onBeforePlayback={before} onMediaError={error}/>));
 const audio=container.querySelector('audio');await act(async()=>audio.dispatchEvent(new Event('play')));
 await act(async()=>container.querySelector('[aria-label="Forward 15 seconds"]').click());
 expect(before).toHaveBeenCalledTimes(1);expect(audio.getAttribute('src')).toContain('segment-1');
 await act(async()=>outcome==='success'?resolve():reject(new Error('denied')));
 expect(audio.getAttribute('src')).toContain(outcome==='success'?'segment-2':'segment-1');expect(error).toHaveBeenCalledTimes(outcome==='denied'?1:0);
 await act(async()=>root.unmount());container.remove();pause.mockRestore();
});

test.each(['pause','stop','unmount','newer-seek'])('delayed playing-seek authorization cannot override %s',async outcome=>{
 mockPlay.mockReset();mockPlay.mockResolvedValue();mockSeekSegment='segment-2';const pause=jest.spyOn(HTMLMediaElement.prototype,'pause').mockImplementation(()=>{});
 let resolves=[];const before=jest.fn(()=>new Promise(resolve=>resolves.push(resolve)));const error=jest.fn();const container=document.createElement('div');document.body.appendChild(container);const root=createRoot(container);
 await act(async()=>root.render(<ListenerExperienceV2 book={{slug:'test'}} audioManifest={{valid:true,packageVersion:'test',durationMs:2000,tracks:[]}} access={{authorized:true}} onBeforePlayback={before} onMediaError={error}/>));const audio=container.querySelector('audio');await act(async()=>audio.dispatchEvent(new Event('play')));await act(async()=>container.querySelector('[aria-label="Forward 15 seconds"]').click());
 if(outcome==='pause')await act(async()=>audio.dispatchEvent(new Event('pause')));
 if(outcome==='stop')await act(async()=>[...container.querySelectorAll('button')].find(b=>b.textContent==='Stop listening').click());
 if(outcome==='unmount')await act(async()=>root.unmount());
 if(outcome==='newer-seek')await act(async()=>container.querySelector('[aria-label="Forward 15 seconds"]').click());
 await act(async()=>resolves[0]());expect(audio.getAttribute('src')).toContain('segment-1');expect(mockPlay).not.toHaveBeenCalled();expect(error).not.toHaveBeenCalled();
 if(outcome==='newer-seek'){await act(async()=>resolves[1]());expect(audio.getAttribute('src')).toContain('segment-2');}
 if(outcome!=='unmount')await act(async()=>root.unmount());container.remove();pause.mockRestore();
});
