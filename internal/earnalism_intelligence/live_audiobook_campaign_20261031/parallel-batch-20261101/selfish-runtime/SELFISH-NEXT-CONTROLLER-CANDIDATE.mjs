import { waitForAdvancingNativePlayback, quantizeSeekTarget, awaitBoundedTerminalAck } from './SELFISH-CONTROLLER-READINESS.mjs';
// OFFLINE CANDIDATE ONLY. All four permitted starts consumed; execution remains prohibited.
// Reviewed ordinary UI automation only. Declaration alone performs no action.
// Never reuse an existing journal or invoke without root's final source/budget GO.
async function runRemainingSelfishCheck({ tab, cdp, fs, crypto, baselineBalance, priorCreditDelta = 3, rootGo, sourcePinsVerified, networkCursor, journalPath, futureIntegrationAuthority = false }) {
  if (!futureIntegrationAuthority) throw Error('OFFLINE_ONLY: no fifth live start authorized');
  const ownedTab = tab;
  const ownedCdp = cdp;
  const packageVersion = 'sha256-b00212b82996e194a7b3bef4f3fb8982304b71afcd32e5f0fa6e93e9341f3211';
  if (!rootGo || !sourcePinsVerified || !Number.isFinite(baselineBalance) || baselineBalance < (120 - priorCreditDelta) || priorCreditDelta < 7 || priorCreditDelta + 70 + 20 + 20 > 120) throw Error('Final source/account/cumulative-budget preflight failed before authorization');
  const state = { schema: 'earnalism.selfish.remaining-normal-check.v1', status: 'PREPARED_NO_AUTHORIZATION', ownerMaximumCumulativeCreditSeconds: 120, internalMaximumTotalStarts: 4, priorStartsKnownOrUncertain: 3, priorWholeSecondCreditDelta: priorCreditDelta, ordinaryCleanupReservationSeconds: 20, maximumLiveLeaseSeconds: 20, safetyCloseWallSeconds: 70, stage: 'prepared', stages: [], requests: [], responses: [], observations: [], errors: [], authorizeReservations: 0, actualNormalStartRequestsObserved: 0, normalStartHttp: null, normalEndConfirmed: false, totalWholeSecondCreditDelta: null, ownSessionBinding: null, noFurtherAutomaticStart: true, rootGo: true, rawIdentityAbsoluteBalanceOrCredentialsSaved: false };
  const exclusive = await fs.open(journalPath, 'wx', 0o600); await exclusive.close();
  let startedAt = null, safetyTimer = null, closed = false, cursor = networkCursor;
  let ownSessionId = null; // Private memory only, never serialized.
  const requestIds = new Set(), responseIds = new Set(), finishedIds = new Set(), bodyRead = new Set(), pendingResponses = new Map();
  const elapsed = () => startedAt === null ? 0 : (Date.now() - startedAt) / 1000;
  const persist = async () => { state.updatedAt = new Date().toISOString(); state.elapsedWallSeconds = elapsed(); await fs.writeFile(journalPath, JSON.stringify(state, null, 2), { mode: 0o600 }); };
  const safeMessage = error => String(error?.message || error).split('\n')[0].replace(/Bearer\s+\S+/gi, '[credential]').replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, '[email]').replace(/([?&][\w-]+=)[^&\s)]+/g, '$1[redacted]').replace(/\b\d+(?:\.\d+)?\s+minutes? left\b/gi, '[private balance]').slice(0, 700);
  const hash = text => crypto.createHash('sha256').update(text).digest('hex');
  const knownPath = path => /^\/api\/reading-pass\/(sessions\/(start|end|transfer)|leases\/renew)$/.test(path) || path.startsWith('/api/reader/book/the-selfish-giant/audiobook/');
  async function captureNetwork(label) {
    state.stage = `network:${label}`; await persist();
    let page;
    do {
      page = await ownedCdp.readEvents({ afterSequence: cursor, methods: ['Network.requestWillBeSent', 'Network.responseReceived', 'Network.loadingFinished', 'Network.loadingFailed'], limit: 1000 });
      cursor = page.cursor;
      if (page.truncated) state.networkTruncated = true;
      for (const event of page.events) {
        const p = event.params || {};
        if (event.method === 'Network.loadingFinished') { finishedIds.add(p.requestId); continue; }
        if (event.method === 'Network.loadingFailed') { state.errors.push({ stage: label, type: 'NETWORK_LOADING_FAILED', error: safeMessage(p.errorText || 'network load failed'), requestId: p.requestId }); continue; }
        const rawUrl = p.response?.url || p.request?.url;
        let url; try { url = new URL(rawUrl); } catch { continue; }
        if (url.origin !== 'https://theearnalism.com' || !knownPath(url.pathname)) continue;
        if (event.method === 'Network.requestWillBeSent' && !requestIds.has(p.requestId)) {
          requestIds.add(p.requestId);
          const row = { requestId: p.requestId, path: url.pathname, method: p.request?.method, timestamp: p.timestamp, wallTime: p.wallTime };
          // Only ordinary controller state; NEVER request headers, tokens, raw bodies or identity.
          if (p.request?.postData && url.pathname.endsWith('/leases/renew')) {
            try { const body = JSON.parse(p.request.postData); row.active = body.active; row.playbackState = body.playback_state; row.sequence = body.sequence; } catch {}
          }
          state.requests.push(row);
          if (url.pathname === '/api/reading-pass/sessions/start') state.actualNormalStartRequestsObserved += 1;
          if (url.pathname.endsWith('/sessions/transfer')) state.errors.push({ stage: label, type: 'UNEXPECTED_TRANSFER_REQUEST' });
        }
        if (event.method === 'Network.responseReceived' && !responseIds.has(p.requestId)) {
          responseIds.add(p.requestId);
          const row = { requestId: p.requestId, path: url.pathname, status: p.response.status, timestamp: p.timestamp };
          state.responses.push(row); pendingResponses.set(p.requestId, row);
          if (url.pathname === '/api/reading-pass/sessions/start') state.normalStartHttp = p.response.status;
        }
      }
      await persist(); // Save safe tape BEFORE another UI operation or close.
    } while (page.hasMore);
    for (const [id, row] of pendingResponses) {
      if (!finishedIds.has(id) || bodyRead.has(id) || !row.path.startsWith('/api/reading-pass/')) continue;
      state.stage = `normal-response-body:${row.path}`; await persist();
      try {
        const response = await ownedCdp.send('Network.getResponseBody', { requestId: id }, { timeoutMs: 1500 });
        const data = JSON.parse(response.body); bodyRead.add(id);
        // Select only the workflow's required fields; ignore credential/identity fields.
        if (row.path.endsWith('/sessions/start') && row.status === 200 && data.session_id) { ownSessionId = data.session_id; state.ownSessionBinding = hash(ownSessionId); }
        if (Number.isFinite(Number(data.balance_seconds))) state.totalWholeSecondCreditDelta = priorCreditDelta + baselineBalance - Number(data.balance_seconds);
        row.deductedSeconds = data.deducted_seconds ?? null;
        if (row.path.endsWith('/sessions/end') && row.status === 200) { state.normalEndConfirmed = data.ended === true; row.ended = data.ended === true; if (state.normalEndConfirmed && safetyTimer) clearTimeout(safetyTimer); }
        if (row.status >= 400) row.errorCode = typeof data.detail?.code === 'string' ? data.detail.code : 'HTTP_ERROR';
      } catch (error) { state.errors.push({ stage: state.stage, type: error.name, error: safeMessage(error), requestId: id }); }
      await persist();
    }
    if (state.actualNormalStartRequestsObserved > 1 || state.requests.some(r => r.path.endsWith('/sessions/transfer'))) throw Error('Unexpected extra normal start or transfer; stop');
    if (state.totalWholeSecondCreditDelta !== null && (state.totalWholeSecondCreditDelta < 0 || state.totalWholeSecondCreditDelta > 120)) throw Error('Owner cumulative-credit delta outside approved bound');
  }
  async function step(label, operation, { collect = true } = {}) {
    if (startedAt !== null && elapsed() >= 54) throw Error('Safety stop: preserve time for own-session containment');
    state.stage = label; state.stages.push({ label, status: 'BEFORE', at: new Date().toISOString(), wallSeconds: elapsed() }); await persist();
    try { const value = await operation(); state.stages.push({ label, status: 'AFTER', at: new Date().toISOString(), wallSeconds: elapsed() }); await persist(); if (collect) await captureNetwork(label); return value; }
    catch (error) { state.errors.push({ stage: label, type: error.name, error: safeMessage(error) }); await persist(); throw error; }
  }
  async function axClick(label, match) {
    const ax = await step(`${label}:fresh-AX`, () => ownedTab.getAXState({ emit: false, disableDiffing: true }));
    const line = ax.split(/\r?\n/).find(item => /^\s*\d+ button\b/.test(item) && !item.includes('(disabled') && match(item));
    if (!line) throw Error(`Enabled normal button missing: ${label}`);
    const index = Number(/^\s*(\d+)/.exec(line)[1]);
    await step(`${label}:native-click-index-${index}`, () => ownedTab.click(index));
    await step(`${label}:post-AX`, () => ownedTab.getAXState({ emit: false }));
  }
  async function waitEnabled(label, locator, maximumMs = 8000) {
    const deadline = Date.now() + maximumMs;
    while (Date.now() < deadline) {
      const enabled = await step(`${label}:isEnabled`, async () => { try { return await locator.isEnabled(); } catch { return false; } });
      if (enabled) return;
      await step(`${label}:readiness-poll-wait`, () => new Promise(resolve => setTimeout(resolve, 250)), { collect: false });
    }
    throw Error(`Normal control did not become ENABLED: ${label}`);
  }
  async function observe(label) {
    const audio = await step(`${label}:DOM`, () => ownedTab.playwright.evaluate(() => { const a = document.querySelector('audio'); return a ? { segment: a.dataset.segmentId, packageVersion: a.dataset.packageVersion, currentTime: a.currentTime, duration: a.duration, paused: a.paused, ended: a.ended, rate: a.playbackRate, readyState: a.readyState } : null; }));
    state.observations.push({ label, wallSeconds: elapsed(), audio }); await persist();
    if (audio && audio.packageVersion !== packageVersion) throw Error('Wrong immutable package in native player');
    if (audio && audio.readyState >= 1 && audio.rate !== 1 && label !== 'restored-metadata-ready' && label !== 'paused-native-rate-before-Play') throw Error('Playback speed drifted from explicit1x');
    return audio;
  }
  async function waitMedia(label, segment = null, maximumMs = 6000) {
    const deadline = Date.now() + maximumMs;
    while (Date.now() < deadline) {
      const audio = await observe(label);
      if (audio && audio.readyState >= 1 && Number.isFinite(audio.duration) && audio.duration > 0 && (!segment || audio.segment === segment)) return audio;
      await step(`${label}:metadata-poll-wait`, () => new Promise(resolve => setTimeout(resolve, 200)), { collect: false });
    }
    throw Error(`Native package metadata not ready: ${label}`);
  }
  async function waitActive(label, segment, maximumMs = 12000) {
    return waitForAdvancingNativePlayback({ read: () => observe(label), poll: () => delay(label + ':active-poll', 200), now: Date.now, maximumMs, segment, rate: 1 });
  }
  async function delay(label, ms) { await step(label, () => new Promise(resolve => setTimeout(resolve, ms))); }
  async function seek(target) {
    target = quantizeSeekTarget(target, 0, 777.12, 0.1);
    await waitEnabled('seek', ownedTab.playwright.getByRole('slider', { name: 'Seek within approved audiobook', exact: true }), 2000);
    const ax = await step(`seek-${target}:fresh-AX`, () => ownedTab.getAXState({ emit: false, disableDiffing: true }));
    // Unchanged parser: validated against retained REAL enabled and disabled AX.
    const m = ax.match(/\n\s*(\d+) slider \(settable[^\n]*Seek within approved audiobook/);
    if (!m) throw Error('Validated enabled seek AX pattern not found');
    await step(`seek-${target}:native-setValue`, () => ownedTab.setValue(Number(m[1]), String(target)));
    await step(`seek-${target}:post-AX`, () => ownedTab.getAXState({ emit: false }));
  }
  async function waitTerminalResponse(label) {
    await awaitBoundedTerminalAck({ capture: async () => { state.stage = 'wait-terminal:' + label; await persist(); await captureNetwork('wait-terminal:' + label); }, confirmed: () => state.normalEndConfirmed || closed, poll: () => new Promise(resolve => setTimeout(resolve, 200)), now: Date.now, startedAt });
    state.terminalResponseWaitCompleted = true; await persist();
  }
  await persist();
  try {
    await waitEnabled('preauth-authorize', ownedTab.playwright.getByRole('button', { name: 'Authorize Listening', exact: true }), 2000);
    state.authorizeReservations = 1; state.status = 'ONE_FINAL_AUTHORIZATION_RESERVED'; state.authorizeReservedAt = new Date().toISOString(); await persist();
    startedAt = Date.now();
    safetyTimer = setTimeout(async () => {
      state.safetyCloseTriggered = true; state.stageAtSafetyClose = state.stage;
      try { await persist(); } catch {} // Safe tape already persisted continuously; never delay the hard-close on network body reads.
      try { await ownedTab.close(); closed = true; state.closedWallSeconds = elapsed(); } catch (error) { state.errors.push({ stage: 'safety-close', type: error.name, error: safeMessage(error) }); }
      try { await persist(); } catch {}
    }, 70000);
    await axClick('Authorize Listening', line => /button Authorize Listening$/.test(line.trim()));
    await waitEnabled('play-after-manifest', ownedTab.playwright.getByRole('button', { name: 'Play approved audiobook', exact: true }));
    await waitEnabled('chapter-after-manifest', ownedTab.playwright.getByRole('button', { name: /^01\s*The Selfish Giant/ }));
    await waitMedia('restored-metadata-ready');
    if (!ownSessionId || state.normalStartHttp !== 200) throw Error('Normal start200/private session binding not established');
    await waitEnabled('normal-Speed-selector', ownedTab.playwright.getByRole('combobox', { name: 'Speed', exact: true }), 3000);
    await step('select-normal-speed-1x', () => ownedTab.playwright.getByRole('combobox', { name: 'Speed', exact: true }).selectOption('1', { timeoutMs: 3000 }));
    await step('speed-post-AX', () => ownedTab.getAXState({ emit: false }));
    const beforePlayRate = await observe('paused-native-rate-before-Play');
    if (!beforePlayRate || !beforePlayRate.paused || beforePlayRate.rate !== 1) throw Error('Normal speed1x not established before spoken playback');
    await axClick('chapter-01-restart', line => /button.*01\s*The Selfish Giant/.test(line));
    const visibleZero = await step('chapter-visible-zero', () => ownedTab.playwright.getByRole('slider', { name: 'Seek within approved audiobook', exact: true }).evaluate(el => Number(el.value) === 0));
    state.visibleChapterStartZero = visibleZero; await persist(); if (!visibleZero) throw Error('Chapter restart did not show0:00');
    await axClick('Play approved audiobook', line => /button Play approved audiobook$/.test(line.trim()));
    await waitActive('first-active-group01', 'group-01'); await delay('first-active-3s', 3000); await observe('initial-playing-1x');
    await seek(61.0); await waitActive('active-cross-group02', 'group-02'); await delay('cross-active-2s', 2000); await observe('cross-segment-1x');
    await seek(55.0); await waitActive('near-first-end-group01', 'group-01');
    await waitActive('natural-transition-group02', 'group-02', 12000); await observe('natural-transition-1x');
    await axClick('Pause approved audiobook', line => /button Pause approved audiobook$/.test(line.trim()));
    await seek(773.1); await observe('paused-final-seek-queued'); await delay('paused-final-2s', 2000); await observe('paused-final-2s-end');
    await axClick('Play approved audiobook', line => /button Play approved audiobook$/.test(line.trim()));
    await waitActive('last-group06', 'group-06'); await delay('final-active-5s', 5000); await observe('after-final-window');
    await waitTerminalResponse('natural-completion');
    await captureNetwork('after-planned-natural-end'); state.status = 'FINAL_SEQUENCE_FINISHED_OBSERVATION_ADJUDICATION_PENDING';
  } catch (error) { state.status = 'FINAL_CHECK_INCOMPLETE_BLOCKED'; state.errors.push({ stage: state.stage, type: error.name, error: safeMessage(error) }); }
  finally {
    if (!closed) {
      try { await captureNetwork('finally-before-containment'); } catch (error) { state.errors.push({ stage: 'finally-capture', type: error.name, error: safeMessage(error) }); }
      if (state.normalStartHttp === 200 && !state.normalEndConfirmed && elapsed() < 67) {
        try {
          const ax = await ownedTab.getAXState({ emit: false, disableDiffing: true });
          const line = ax.split(/\r?\n/).find(item => /^\s*\d+ button Stop listening$/.test(item.trim()));
          if (line) { state.stage = 'contain-owned-session:Stop'; await persist(); await ownedTab.click(Number(/^\s*(\d+)/.exec(line.trim())[1])); await ownedTab.getAXState({ emit: false }); }
          await captureNetwork('after-owned-session-stop');
          await waitTerminalResponse('owned-session-stop');
        } catch (error) { state.errors.push({ stage: 'own-session-containment', type: error.name, error: safeMessage(error) }); }
      }
      await persist(); // All safe request/response evidence is durable BEFORE close.
      try { await ownedTab.close(); closed = true; state.closedWallSeconds = elapsed(); } catch (error) { state.errors.push({ stage: 'close-owned-tab', type: error.name, error: safeMessage(error) }); }
    }
    if (safetyTimer) clearTimeout(safetyTimer);
    state.finalNormalStartCount = state.actualNormalStartRequestsObserved || (state.authorizeReservations ? 'UNVERIFIED_NOT_ASSUMED_ZERO' : 0);
    state.finalNoFurtherAutomaticStart = true;
    await persist();
  }
  return { status: state.status, authorizeReservedAt: state.authorizeReservedAt, actualNormalStartRequestsObserved: state.actualNormalStartRequestsObserved, normalStartHttp: state.normalStartHttp, normalEndConfirmed: state.normalEndConfirmed, totalWholeSecondCreditDelta: state.totalWholeSecondCreditDelta, closedWallSeconds: state.closedWallSeconds, errors: state.errors, observationCount: state.observations.length, journalPath };
}

export { runRemainingSelfishCheck };
