import test from 'node:test';
import assert from 'node:assert/strict';
import {attachAudioFocus} from '../comparison-player/audio-focus.mjs';

class Media extends EventTarget {
  constructor(id) { super(); this.id = id; this.paused = true; this.ended = false; this.muted = false; }
  play() { this.paused = false; this.ended = false; this.dispatchEvent(new Event('play')); }
  pause() { if (this.paused) return; this.paused = true; this.dispatchEvent(new Event('pause')); }
  end() { this.ended = true; this.paused = true; this.dispatchEvent(new Event('pause')); this.dispatchEvent(new Event('ended')); }
}
function bus() {
  const peers = new Set(), queue = [];
  class Channel extends EventTarget {
    constructor(name) { super(); this.name = name; this.closed = false; peers.add(this); }
    postMessage(data) { for (const p of peers) if (p !== this && p.name === this.name) queue.push([p, structuredClone(data)]); }
    close() { this.closed = true; peers.delete(this); }
  }
  return {Channel, peers, flush() { while (queue.length) { const [p, data] = queue.shift(); if (!p.closed) p.dispatchEvent(new MessageEvent('message', {data})); } }};
}
const audible = media => media.filter(v => !v.paused && !v.ended && !v.muted).length;

test('independent comparison tabs coordinate video and dry-audio playback', () => {
  const b = bus(), v1 = new Media('video-1'), dry = new Media('dry-1'), v2 = new Media('video-2');
  const d1 = attachAudioFocus([v1, dry], {BroadcastChannelClass: b.Channel});
  const d2 = attachAudioFocus([v2], {BroadcastChannelClass: b.Channel});
  try {
    v1.play(); b.flush(); assert.equal(audible([v1, dry, v2]), 1);
    dry.play(); b.flush(); assert.equal(v1.paused, true); assert.equal(dry.paused, false);
    v2.play(); b.flush(); assert.equal(dry.paused, true); assert.equal(audible([v1, dry, v2]), 1);
    dry.play(); b.flush(); assert.equal(v2.paused, true); assert.equal(audible([v1, dry, v2]), 1);
  } finally { d1(); d2(); }
});

test('simultaneous claims converge to one player rather than stopping both', () => {
  const b = bus(), a = new Media('a'), c = new Media('c');
  const da = attachAudioFocus([a], {BroadcastChannelClass: b.Channel});
  const dc = attachAudioFocus([c], {BroadcastChannelClass: b.Channel});
  try { a.play(); c.play(); b.flush(); assert.equal(audible([a, c]), 1); }
  finally { da(); dc(); }
});

test('paused status follows a real pause and ended status is not overwritten by remote playback', () => {
  const b = bus(), a = new Media('a'), c = new Media('c'), states = [];
  const da = attachAudioFocus([a], {BroadcastChannelClass: b.Channel, onStatus: s => states.push(s.state)});
  const dc = attachAudioFocus([c], {BroadcastChannelClass: b.Channel});
  try {
    a.play(); b.flush(); a.pause(); assert.equal(states.at(-1), 'paused');
    a.play(); b.flush(); a.end(); assert.equal(states.at(-1), 'ended');
    c.play(); b.flush(); assert.equal(states.at(-1), 'ended');
  } finally { da(); dc(); }
});

test('pause callbacks identify the actual medium for consumers that ignore unbound status', () => {
  const b = bus(), video = new Media('video'), dry = new Media('dry'), rendered = [];
  const destroy = attachAudioFocus([video, dry], {
    BroadcastChannelClass: b.Channel,
    onStatus: status => { if (status.media) rendered.push(status); },
  });
  try {
    video.play(); video.pause();
    assert.equal(rendered.at(-1).state, 'paused');
    assert.equal(rendered.at(-1).media, video);
    dry.play(); dry.pause();
    assert.equal(rendered.at(-1).state, 'paused');
    assert.equal(rendered.at(-1).media, dry);
    video.play(); video.end();
    assert.equal(rendered.at(-1).state, 'ended');
    assert.equal(rendered.at(-1).media, video);
  } finally { destroy(); }
});

test('remote pause callbacks retain the medium that relinquished focus', () => {
  const b = bus(), a = new Media('a'), c = new Media('c'), states = [];
  const da = attachAudioFocus([a], {BroadcastChannelClass: b.Channel, onStatus: s => states.push(s)});
  const dc = attachAudioFocus([c], {BroadcastChannelClass: b.Channel});
  try {
    a.play(); b.flush(); c.play(); b.flush();
    assert.equal(states.at(-1).state, 'paused');
    assert.equal(states.at(-1).reason, 'another-comparison-tab');
    assert.equal(states.at(-1).media, a);
  } finally { da(); dc(); }
});

test('destroy is idempotent, closes channels and removes media listeners', () => {
  const b = bus(), a = new Media('a'), c = new Media('c'), states = [];
  const da = attachAudioFocus([a], {BroadcastChannelClass: b.Channel, onStatus: s => states.push(s.state)});
  const dc = attachAudioFocus([c], {BroadcastChannelClass: b.Channel});
  a.play(); b.flush(); da(); da(); assert.equal(a.paused, true); assert.equal(b.peers.size, 1);
  const n = states.length; a.play(); c.play(); b.flush(); assert.equal(states.length, n); assert.equal(a.paused, false);
  a.pause(); dc(); assert.equal(b.peers.size, 0);
});

test('unsupported BroadcastChannel reports local-only fallback without claiming cross-tab exclusivity', () => {
  const a = new Media('a'), dry = new Media('dry'), states = [];
  const destroy = attachAudioFocus([a, dry], {BroadcastChannelClass: null, onStatus: s => states.push(s)});
  try {
    assert.equal(states[0].crossTabSupported, false); assert.equal(states[0].scope, 'local-page-only');
    assert.match(states[0].reason, /unavailable/);
    a.play(); dry.play(); assert.equal(a.paused, true); assert.equal(dry.paused, false);
    assert.equal(states.at(-1).crossTabSupported, false);
  } finally { destroy(); }
});

test('pagehide closes focus channel and pauses playback; BFCache restore reconnects once', () => {
  const events = new EventTarget();
  const oldAdd = globalThis.addEventListener, oldRemove = globalThis.removeEventListener;
  globalThis.addEventListener = events.addEventListener.bind(events);
  globalThis.removeEventListener = events.removeEventListener.bind(events);
  const b = bus(), a = new Media('a');
  const destroy = attachAudioFocus([a], {BroadcastChannelClass: b.Channel});
  try {
    a.play(); assert.equal(b.peers.size, 1);
    const hide = new Event('pagehide'); Object.defineProperty(hide, 'persisted', {value: true}); events.dispatchEvent(hide);
    assert.equal(a.paused, true); assert.equal(b.peers.size, 0);
    const show = new Event('pageshow'); Object.defineProperty(show, 'persisted', {value: true}); events.dispatchEvent(show);
    events.dispatchEvent(show); assert.equal(b.peers.size, 1);
    destroy(); events.dispatchEvent(show); assert.equal(b.peers.size, 0);
  } finally {
    destroy();
    if (oldAdd) globalThis.addEventListener = oldAdd; else delete globalThis.addEventListener;
    if (oldRemove) globalThis.removeEventListener = oldRemove; else delete globalThis.removeEventListener;
  }
});
