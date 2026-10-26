import React, { act } from "react";
import { createRoot } from "react-dom/client";
const mockPlay = jest.fn();
const mockSegments = Array.from({ length: 29 }, (_, n) => ({ segmentId: `segment-${n+1}`, audioUrl: `/api/reader/book/test/audiobook/segment-${n+1}`, cumulativeStartMs: n*1000, nextSegmentId: n<28 ? `segment-${n+2}` : "" }));
jest.mock("react-router-dom", () => ({ Link: ({ to, children }) => <a href={to}>{children}</a>, NavLink: ({ to, children }) => <a href={to}>{children}</a>, useLocation: () => ({ pathname: "/listener/test" }), useNavigate: () => jest.fn() }), { virtual: true });
jest.mock("../shared/ReleaseTruthAdapter", () => ({ listenerReleasePresentation: () => ({ title: "Test", author: "Test", canRender: true, fixture: false }) }));
jest.mock("../../lib/audioPackageManifest", () => ({ selectAudioTrack: ({ preferredSegmentId }) => mockSegments.find(s => s.segmentId === preferredSegmentId) || mockSegments[0], audioSegmentAtMediaPosition: () => ({ ...mockSegments[0], offsetSeconds: 0 }) }));
jest.mock("../../lib/audiobookPlayback", () => ({ loadAudiobookProgress: () => null, saveAudiobookProgress: jest.fn(), shouldPrefetchNextSegment: () => false, requestAudiobookPlayback: (...args) => mockPlay(...args) }));
import ListenerExperienceV2 from "../listener/ListenerExperienceV2";
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

async function setup() {
  const pause=jest.spyOn(HTMLMediaElement.prototype,"pause").mockImplementation(()=>{});
  mockPlay.mockReset();mockPlay.mockResolvedValue();
  const container=document.createElement("div");document.body.appendChild(container);const root=createRoot(container);
  const states=jest.fn(),complete=jest.fn(),error=jest.fn();let resolve,reject;
  const before=jest.fn(()=>new Promise((yes,no)=>{resolve=yes;reject=no}));
  await act(async()=>{root.render(<ListenerExperienceV2 book={{slug:"test"}} audioManifest={{valid:true,packageVersion:"test",durationMs:29000,tracks:[]}} access={{authorized:true}} onBeforePlayback={before} onPlaybackStateChange={states} onPlaybackComplete={complete} onMediaError={error}/>)});
  const audio=container.querySelector("audio");Object.defineProperty(audio,"readyState",{configurable:true,value:1});
  return {container,root,audio,states,complete,error,before,resolve:()=>resolve(),reject:()=>reject(new Error("denied")),cleanup:async()=>{await act(async()=>root.unmount());container.remove();pause.mockRestore()}};
}

test("all 29 segment transitions renew before source change and suppress source-swap pauses",async()=>{
 const x=await setup();await act(async()=>x.audio.dispatchEvent(new Event("play")));
 for(let n=0;n<28;n++){
  await act(async()=>{x.audio.dispatchEvent(new Event("pause"));x.audio.dispatchEvent(new Event("ended"))});
  expect(x.before).toHaveBeenCalledTimes(n+1);
  expect(x.audio.getAttribute("src")).toBe(mockSegments[n].audioUrl);
  await act(async()=>x.resolve());
  expect(x.audio.getAttribute("src")).toBe(mockSegments[n+1].audioUrl);
  x.states.mockClear();
  await act(async()=>x.audio.dispatchEvent(new Event("pause")));
  expect(x.states).not.toHaveBeenCalledWith("paused");
  await act(async()=>x.audio.dispatchEvent(new Event("loadedmetadata")));
  expect(mockPlay).toHaveBeenCalledTimes(n+1);
  await act(async()=>x.audio.dispatchEvent(new Event("play")));
 }
 await act(async()=>{x.audio.dispatchEvent(new Event("pause"));x.audio.dispatchEvent(new Event("ended"))});
 expect(x.complete).toHaveBeenCalledTimes(1);expect(x.before).toHaveBeenCalledTimes(28);expect(x.error).not.toHaveBeenCalled();await x.cleanup();
});

test("denied transition leaves source unchanged and reports media failure",async()=>{
 const x=await setup();await act(async()=>x.audio.dispatchEvent(new Event("ended")));await act(async()=>x.reject());
 expect(x.audio.getAttribute("src")).toBe(mockSegments[0].audioUrl);expect(mockPlay).not.toHaveBeenCalled();expect(x.error).toHaveBeenCalledTimes(1);await x.cleanup();
});

test("pending transition cannot update media after unmount",async()=>{
 const x=await setup();await act(async()=>x.audio.dispatchEvent(new Event("ended")));await x.cleanup();await act(async()=>x.resolve());expect(mockPlay).not.toHaveBeenCalled();expect(x.complete).not.toHaveBeenCalled();
});

test.each([1,1.25,1.5])("native waiting and playing, not playback rate %s, control billable state",async(rate)=>{
 const x=await setup();
 await act(async()=>{const select=x.container.querySelector('select');select.value=String(rate);select.dispatchEvent(new Event('change',{bubbles:true}));x.audio.dispatchEvent(new Event('play'))});
 expect(x.states).not.toHaveBeenCalledWith('playing');
 await act(async()=>x.audio.dispatchEvent(new Event('playing')));expect(x.states).toHaveBeenLastCalledWith('playing');
 await act(async()=>x.audio.dispatchEvent(new Event('waiting')));expect(x.states).toHaveBeenLastCalledWith('buffering');
 await act(async()=>x.audio.dispatchEvent(new Event('playing')));expect(x.states).toHaveBeenLastCalledWith('playing');
 await act(async()=>x.audio.dispatchEvent(new Event('pause')));expect(x.states).toHaveBeenLastCalledWith('paused');
 await x.cleanup();
});
