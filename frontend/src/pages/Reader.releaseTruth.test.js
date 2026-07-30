import fs from "fs";
import path from "path";

const readerSourcePath = path.resolve(__dirname, "Reader.jsx");
const readerSource = fs.readFileSync(readerSourcePath, "utf8");

describe("Reader release-truth and reading-room guardrails", () => {
  test("does not expose browser speech as an audiobook fallback", () => {
    expect(readerSource).not.toMatch(/speechSynthesis|SpeechSynthesisUtterance|synthRef|system speech|browser speech/i);
  });

  test("does not derive static audio URLs", () => {
    expect(readerSource).not.toMatch(/\/audio\//);
    expect(readerSource).not.toMatch(/audioUrl\s*\|\|/);
    expect(readerSource).not.toMatch(/timestampsUrl\s*\|\|/);
  });

  test("keeps Reader audio controls behind shared approval evidence", () => {
    expect(readerSource).toMatch(/canExposeAudiobookControls/);
    expect(readerSource).toMatch(/hasGeneratedAudioEnabled\(book,\s*bookId\)/);
    expect(readerSource).toMatch(/generatedAudioAvailable/);
    expect(readerSource).toMatch(/Audio will appear only after narration, sync, and browser gates pass/);
  });

  test("does not claim word-level sync in customer copy", () => {
    expect(readerSource).not.toMatch(/word-level|word level|word sync/i);
    expect(readerSource).toMatch(/Section-following narration/);
    expect(readerSource).toMatch(/Paragraph\/Stanza Sync/);
  });

  test("normalizes approved production timestamps before playback", () => {
    expect(readerSource).toMatch(/normalizeAudioTimestamp/);
    expect(readerSource).toMatch(/audioTimestampStartMs\(timestamps\[mid\]\)/);
    expect(readerSource).toMatch(/audioTimestampStartMs\(firstTimestamp\) \/ 1000/);
  });

  test("plays approved MP3-only editions without inventing highlight sync", () => {
    expect(readerSource).toMatch(/if \(assets\?\.mp3\) return true/);
    expect(readerSource).toMatch(/if \(!generatedHighlightSyncEnabled\)/);
    expect(readerSource).toMatch(/setGeneratedAudioAvailable\(true\)/);
    expect(readerSource).toMatch(/generatedAudioAvailable && generatedHighlightSyncEnabled/);
  });

  test("loads package audio only on intent and advances immutable segments across chapters", () => {
    const audioElementStart = readerSource.indexOf("<audio");
    const audioElementEnd = readerSource.indexOf("/>", audioElementStart);
    const audioElementSource = readerSource.slice(audioElementStart, audioElementEnd);

    expect(audioElementStart).toBeGreaterThan(-1);
    expect(audioElementEnd).toBeGreaterThan(audioElementStart);
    expect(audioElementSource).toMatch(/preload="none"/);
    expect(audioElementSource).not.toMatch(/\bsrc=/);
    expect(readerSource).not.toMatch(/generatedAudioPrimed/);
    expect(readerSource).toMatch(/audio\.src = generatedAudioUrl/);
    expect(readerSource).toMatch(/selectedGeneratedAudioTrack\.nextSegmentId/);
    expect(readerSource).toMatch(/selectedGeneratedAudioTrack\.nextChapterId/);
    expect(readerSource).toMatch(/setGeneratedAudioSegmentId\(selectedGeneratedAudioTrack\.nextSegmentId\)/);
    expect(readerSource).toMatch(/pendingCrossChapterAudioResumeRef/);
    expect(readerSource).toMatch(/bookId,\s*packageVersion:\s*selectedGeneratedAudioTrack\.packageVersion/);
    expect(readerSource).toMatch(/pendingAudiobookResumeMatches\(pending/);
    expect(readerSource).toMatch(/pending\.bookId !== bookId/);
    expect(readerSource).toMatch(/pendingCrossChapterAudioResumeRef\.current = null/);
    expect(readerSource).toMatch(/chapterId:\s*selectedGeneratedAudioTrack\.nextChapterId/);
    expect(readerSource).not.toMatch(/onMouseEnter=\{primeGeneratedAudio\}/);
    expect(readerSource).not.toMatch(/onFocus=\{primeGeneratedAudio\}/);
    expect(readerSource).not.toMatch(/onTouchStart=\{primeGeneratedAudio\}/);
    expect(readerSource).not.toMatch(/prefetchAsset\(nextTrack\.audioUrl\)/);
    expect(readerSource).not.toMatch(/prefetchAsset\(nextTrack\.timestampsUrl\)/);
  });

  test("requests first-click playback before deferred highlight rendering", () => {
    const start = readerSource.indexOf("const startGeneratedAudio = useCallback");
    const end = readerSource.indexOf("const handleGeneratedAudioMetadata", start);
    const startGeneratedAudioSource = readerSource.slice(start, end);
    const deferredHighlightIndex = startGeneratedAudioSource.indexOf("window.requestAnimationFrame");
    const synchronizedPlaybackIndex = startGeneratedAudioSource.lastIndexOf(
      "requestAudiobookPlayback(audio)",
    );

    expect(start).toBeGreaterThan(-1);
    expect(end).toBeGreaterThan(start);
    expect(startGeneratedAudioSource).toMatch(
      /pendingAudioOffsetRef\.current = audioTimestampStartMs\(firstTimestamp\) \/ 1000/,
    );
    expect(synchronizedPlaybackIndex).toBeGreaterThan(-1);
    expect(deferredHighlightIndex).toBeGreaterThan(synchronizedPlaybackIndex);
    expect(startGeneratedAudioSource).not.toMatch(/window\.requestAnimationFrame[\s\S]*audio\.play\(/);
    expect(readerSource).not.toMatch(/\baudio\.play\(\)/);
    expect(readerSource).not.toMatch(/generatedAudioRef\.current\?\.play/);
  });

  test("persists only immutable package-bound audiobook progress", () => {
    expect(readerSource).toMatch(/loadAudiobookProgress\(bookId,\s*normalizedManifest\.packageVersion\)/);
    expect(readerSource).toMatch(/saveAudiobookProgress\(bookId/);
    expect(readerSource).toMatch(/packageVersion/);
    expect(readerSource).toMatch(/segmentId/);
    expect(readerSource).toMatch(/offset:/);
    expect(readerSource).toMatch(/speed:/);
    expect(readerSource).toMatch(/window\.addEventListener\('pagehide'/);
    expect(readerSource).toMatch(/savedSegmentChapterId === visibleChapterId/);
    expect(readerSource).toMatch(/chapterIdForAudioSegment/);
  });

  test("binds package manifests to exact reader release truth", () => {
    expect(readerSource).toMatch(/expectedSlug:\s*bookId/);
    expect(readerSource).toMatch(/expectedPackageVersion:\s*generatedAudioReleaseState\.packageVersion/);
    expect(readerSource).toMatch(/if \(!normalizedManifest\.valid\)/);
    expect(readerSource).not.toMatch(/!generatedAudioReleaseState\.packageVersion\)/);
  });

  test("prefetches only next-segment metadata after playback reaches the threshold", () => {
    expect(readerSource).toMatch(/shouldPrefetchNextSegment\(audio\?\.currentTime,\s*audio\?\.duration,\s*nextSegmentId\)/);
    expect(readerSource).toMatch(/prefetchAudioMetadata\(selectedGeneratedAudioTrack\.nextAudioUrl\)/);
    expect(readerSource).toMatch(/prefetchAsset\(selectedGeneratedAudioTrack\.nextTimestampsUrl,\s*\{\s*credentials:\s*'include'\s*\}\)/);
    expect(readerSource).toMatch(/method:\s*'HEAD'/);
    expect(readerSource).toMatch(/crossOrigin="use-credentials"/);
    expect(readerSource).toMatch(/fetch\(generatedAudioManifestUrl,\s*\{\s*cache:\s*'force-cache',\s*credentials:\s*'include'\s*\}\)/);
    expect(readerSource).not.toMatch(/prefetchAsset\(selectedGeneratedAudioTrack\.nextAudioUrl\)/);
  });

  test("records real playback, stall, seek, and transition timing events", () => {
    expect(readerSource).toMatch(/reader_audio_ttfa/);
    expect(readerSource).toMatch(/reader_audio_stall/);
    expect(readerSource).toMatch(/reader_audio_seek/);
    expect(readerSource).toMatch(/reader_audio_segment_transition/);
    expect(readerSource).toMatch(/onPlaying=\{handleGeneratedAudioPlaying\}/);
    expect(readerSource).toMatch(/onWaiting=\{markGeneratedAudioStall\}/);
    expect(readerSource).toMatch(/onStalled=\{markGeneratedAudioStall\}/);
    expect(readerSource).toMatch(/onSeeking=\{handleGeneratedAudioSeeking\}/);
    expect(readerSource).toMatch(/onSeeked=\{handleGeneratedAudioSeeked\}/);
  });

  test("shows explicit AI narration disclosure beside approved controls", () => {
    expect(readerSource).toMatch(/audiobookNarrationDisclosure/);
    expect(readerSource).toMatch(/reader-audio-control__disclosure/);
    expect(readerSource).toMatch(/reader-audio-disclosure/);
  });

  test("represents premium reading settings for bilingual long-form reading", () => {
    expect(readerSource).toMatch(/label:\s*'Light'/);
    expect(readerSource).toMatch(/label:\s*'Sepia'/);
    expect(readerSource).toMatch(/label:\s*'Night'/);
    expect(readerSource).toMatch(/Bengali font mode/);
    expect(readerSource).toMatch(/Literary Bengali serif/);
    expect(readerSource).toMatch(/Clear Bengali sans/);
    expect(readerSource).toMatch(/Reduced motion/);
    expect(readerSource).toMatch(/Highlight intensity/);
    expect(readerSource).toMatch(/aria-labelledby="reader-settings-title"/);
  });

  test("hardens Reader settings for persistence and accessibility", () => {
    expect(readerSource).toMatch(/loadReaderSettings/);
    expect(readerSource).toMatch(/saveReaderSettings/);
    expect(readerSource).toMatch(/resetReaderSettings/);
    expect(readerSource).toMatch(/Reset comfort defaults/);
    expect(readerSource).toMatch(/aria-modal="true"/);
    expect(readerSource).toMatch(/data-testid="reader-settings-panel"/);
    expect(readerSource).toMatch(/data-reader-settings-initial-focus/);
    expect(readerSource).toMatch(/event\.key === 'Escape'/);
  });

  test("keeps Settings copy free of public audiobook claims", () => {
    const settingsSource = readerSource.slice(readerSource.indexOf('{showSettings && ('));
    expect(settingsSource).not.toMatch(/Listen CTA|AudioObject|browser speech|system speech|word-level|word sync/i);
    expect(settingsSource).toMatch(/Reading tone/);
    expect(settingsSource).toMatch(/Typography/);
    expect(settingsSource).toMatch(/Bengali comfort/);
    expect(settingsSource).toMatch(/Focus and motion/);
  });
});
