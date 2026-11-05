import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const root = new URL('../../', import.meta.url);
const source = path => readFile(new URL(path, root), 'utf8');
const moduleSource = await source('frontend/src/lib/audioPackageManifest.js');
const media = await import(`data:text/javascript;base64,${Buffer.from(moduleSource).toString('base64')}`);
const manifest = { tracks: [{ chapterId: 'c1', chunks: [
  { segmentId: 's1', startWord: 0, endWord: 9, audioUrl: 'one', durationMs: 1000, cumulativeStartMs: 0 },
  { segmentId: 's2', startWord: 10, endWord: 20, audioUrl: 'two', durationMs: 2000, cumulativeStartMs: 1000 },
] }] };
test('stale text position cannot select or seek a media segment', () => {
  assert.equal(media.selectAudioTrack({ manifest, chapterId: 'c1', currentWordOffset: 19 }).segmentId, 's1');
});
test('explicit media navigation and ordered transitions are retained', () => {
  assert.equal(media.selectAudioTrack({ manifest, preferredSegmentId: 's2' }).segmentId, 's2');
  assert.equal(media.selectAudioTrack({ manifest }).nextSegmentId, 's2');
  assert.equal(media.selectAudioTrack({ manifest, preferredSegmentId: 's2' }).cumulativeStartMs, 1000);
});
test('legacy Reader has no cue fetch, word wrapping/following or text-derived audio seeking', async () => {
  const reader = await source('frontend/src/pages/Reader.jsx');
  assert.doesNotMatch(reader, /generatedTimestamps|timestampIndexAt|wrapWordsInSpans|highlightGeneratedWord|currentWordOffset|generatedHighlightSync/);
  assert.match(reader, /applyPendingAudioOffset\(\)/);
  assert.match(reader, /persistGeneratedAudioProgress/);
  assert.match(reader, /handleGeneratedAudioEnded/);
  assert.match(reader, /goNext/);
});
test('current Listener and legacy marketing cannot restore or claim read-along', async () => {
  for (const file of ['frontend/src/experiences-v2/listener/ListenerExperienceV2.jsx', 'frontend/src/components/ReaderAudiobookPanel.jsx', 'frontend/src/components/PremiumListeningRail.jsx']) {
    assert.doesNotMatch(await source(file), /read.?along|Paragraph.{0,5}sync|Read \+ Listen|onReadAlong|readAlongSupported/i);
  }
});
