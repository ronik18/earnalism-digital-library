/** One playing medium per page and, when supported, per same-origin comparison group.
 * BroadcastChannel cannot coordinate older comparison pages on different ports.
 * Returns an idempotent destroy function. Status is evidence of support, not DRM.
 */
const MESSAGE = 'earnalism.audio-focus.v1';
let serial = 0;
export function attachAudioFocus(media, {
  BroadcastChannelClass = globalThis.BroadcastChannel,
  channelName = 'earnalism-private-comparison-audio-v1',
  onStatus = () => {},
} = {}) {
  const items = [...new Set(Array.from(media))];
  if (!items.length || items.some(v => !v || typeof v.pause !== 'function' || typeof v.addEventListener !== 'function')) {
    throw new TypeError('Audio focus requires media event targets');
  }
  const owner = globalThis.crypto?.randomUUID?.() ?? `page-${Date.now()}-${++serial}-${Math.random()}`;
  let channel = null, destroyed = false, suspended = false, latest = null;
  const lifecycle = typeof globalThis.addEventListener === 'function' ? globalThis : null;
  const playing = () => items.filter(v => !v.paused && !v.ended);
  function status(state, detail = {}) {
    const supported = channel !== null;
    // UI failures must not leave several players running or leak a channel.
    try { onStatus({state, crossTabSupported: supported, scope: supported ? 'same-origin' : 'local-page-only', ...detail}); } catch {}
  }
  function disconnect() {
    if (!channel) return;
    const old = channel; channel = null;
    old.removeEventListener('message', receive);
    old.close();
  }
  function receive(event) {
    const claim = event.data;
    if (destroyed || suspended || !claim || claim.type !== MESSAGE || claim.owner === owner ||
        typeof claim.owner !== 'string' || !Number.isSafeInteger(claim.time) || claim.time < 0) return;
    const wins = !latest || claim.time > latest.time || (claim.time === latest.time && claim.owner > latest.owner);
    if (!wins) return;
    latest = claim;
    const active = playing();
    active.forEach(v => v.pause());
    if (active.length) status('paused', {media: active[0], reason: 'another-comparison-tab'});
  }
  function connect() {
    if (destroyed || suspended || channel) return;
    if (typeof BroadcastChannelClass !== 'function') {
      status('ready', {reason: 'BroadcastChannel unavailable; only this page is coordinated'});
      return;
    }
    try {
      channel = new BroadcastChannelClass(channelName);
      channel.addEventListener('message', receive);
    } catch {
      if (channel) { try { channel.close(); } catch {} channel = null; }
    }
    status('ready', channel ? {} : {reason: 'BroadcastChannel unavailable; only this page is coordinated'});
  }
  function onPlay(event) {
    if (destroyed) return;
    const current = event.currentTarget;
    items.forEach(v => { if (v !== current) v.pause(); });
    if (suspended) { current.pause(); return; }
    // Logical time makes a later local choice win after a remote claim. The
    // owner tie-break also prevents two simultaneous claims pausing each other.
    latest = {type: MESSAGE, owner, time: Math.max(Date.now(), (latest?.time ?? 0) + 1)};
    if (channel) {
      try { channel.postMessage(latest); } catch { disconnect(); }
    }
    status('playing', {media: current, reason: channel ? 'focus-acquired' : 'local-page-only'});
  }
  function onPause(event) {
    if (!destroyed && !event.currentTarget.ended && !playing().length) status('paused', {media: event.currentTarget, reason: 'media-paused'});
  }
  function onEnded(event) {
    if (!destroyed && !playing().length) status('ended', {media: event.currentTarget});
  }
  function onPageHide(event) {
    suspended = true;
    items.forEach(v => v.pause());
    disconnect();
    if (!event.persisted) destroy();
  }
  function onPageShow(event) {
    if (event.persisted && !destroyed) { suspended = false; connect(); }
  }
  function destroy() {
    if (destroyed) return;
    destroyed = true;
    for (const v of items) {
      v.removeEventListener('play', onPlay);
      v.removeEventListener('pause', onPause);
      v.removeEventListener('ended', onEnded);
      v.pause();
    }
    disconnect();
    lifecycle?.removeEventListener('pagehide', onPageHide);
    lifecycle?.removeEventListener('pageshow', onPageShow);
  }
  for (const v of items) {
    v.addEventListener('play', onPlay);
    v.addEventListener('pause', onPause);
    v.addEventListener('ended', onEnded);
  }
  lifecycle?.addEventListener('pagehide', onPageHide);
  lifecycle?.addEventListener('pageshow', onPageShow);
  connect();
  return destroy;
}
