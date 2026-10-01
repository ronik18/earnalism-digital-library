import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, Clock3, Pause, Play, RotateCcw, RotateCw } from "lucide-react";
import ExperienceBottomNavigation from "../shared/ExperienceBottomNavigation";
import ExperienceHeader from "../shared/ExperienceHeader";
import ExperienceIconButton from "../shared/ExperienceIconButton";
import ExperiencePanel from "../shared/ExperiencePanel";
import ExperienceShell from "../shared/ExperienceShell";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";
import { LISTENING_ACCESS_COPY, READING_TIME_COPY } from "../../lib/publicAccessCopy";
import { audioSegmentAtMediaPosition, selectAudioTrack } from "../../lib/audioPackageManifest";
import { loadAudiobookProgress, requestAudiobookPlayback, saveAudiobookProgress, shouldPrefetchNextSegment } from "../../lib/audiobookPlayback";
import BookCoverImage from "../../components/BookCoverImage";
import "./listener-v2.css";

const clock = (seconds = 0) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

export function clampPlaybackTime(seconds, durationSeconds) {
  const value = Math.max(0, Number(seconds) || 0);
  return durationSeconds > 0 ? Math.min(value, durationSeconds) : value;
}

export default function ListenerExperienceV2({ book = {}, fixture = false, access = {}, audioManifest = null, authorizing = false, onAuthorize, onPlaybackStateChange, onStop, onPlaybackComplete, onMediaError, onNavigate, onAddToLibrary, onReadAlong, readAlongSupported = false }) {
  const presentation = listenerReleasePresentation(book, { fixture });
  const audioRef = useRef(null);
  const pendingOffsetRef = useRef(null);
  const pendingOffsetSegmentRef = useRef("");
  const resumeAfterTransitionRef = useRef(false);
  const prefetchedSegmentsRef = useRef(new Set());
  const progressSavedAtRef = useRef(0);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [segmentId, setSegmentId] = useState("");

  const activeSegment = useMemo(() => (
    audioManifest?.valid
      ? selectAudioTrack({ manifest: audioManifest, preferredSegmentId: segmentId })
      : null
  ), [audioManifest, segmentId]);
  const totalDuration = Number(audioManifest?.durationMs || 0) / 1000 || presentation.durationSeconds || 0;
  const canPlay = !presentation.fixture && Boolean(access.authorized && audioManifest?.valid && activeSegment?.audioUrl);
  const chapters = useMemo(() => {
    const tracks = audioManifest?.valid ? audioManifest.tracks : [];
    const trackByChapter = new Map(tracks.map((track) => [track.chapterId, track]));
    return (Array.isArray(book.chapters) ? book.chapters : []).map((chapter, index) => {
      const chapterId = String(chapter.id || chapter.chapter_id || "");
      const track = trackByChapter.get(chapterId);
      return {
        chapterId,
        title: String(chapter.title || `Chapter ${index + 1}`),
        order: Number(chapter.order || index + 1),
        track,
      };
    }).sort((left, right) => left.order - right.order);
  }, [audioManifest, book.chapters]);
  const passBalance = Number(access.readingPassBalanceSeconds);
  const passBalanceLabel = Number.isSafeInteger(passBalance) && passBalance >= 0
    ? `${Math.floor(passBalance / 60)} minutes left`
    : "Reading Pass required";

  useEffect(() => () => { audioRef.current?.pause(); }, []);

  useEffect(() => {
    if (!audioManifest?.valid) return;
    const saved = loadAudiobookProgress(book.slug, audioManifest.packageVersion);
    const savedTrack = saved?.segmentId
      ? selectAudioTrack({ manifest: audioManifest, preferredSegmentId: saved.segmentId })
      : null;
    const validSaved = Boolean(saved?.segmentId && savedTrack?.segmentId === saved.segmentId);
    const initial = validSaved
      ? savedTrack
      : selectAudioTrack({ manifest: audioManifest });
    prefetchedSegmentsRef.current.clear();
    pendingOffsetRef.current = validSaved ? saved.offset : 0;
    pendingOffsetSegmentRef.current = initial.segmentId;
    setSegmentId(initial.segmentId);
    setTime((Number(initial.cumulativeStartMs || 0) / 1000) + (validSaved ? saved.offset : 0));
    setSpeed(validSaved ? saved.speed : 1);
  }, [audioManifest, book.slug]);

  const persistProgress = useCallback(({ force = false } = {}) => {
    const audio = audioRef.current;
    if (!audioManifest?.valid || !audio || !activeSegment?.segmentId) return;
    if (!force && Date.now() - progressSavedAtRef.current < 5000) return;
    progressSavedAtRef.current = Date.now();
    saveAudiobookProgress(book.slug, {
      packageVersion: audioManifest.packageVersion,
      segmentId: activeSegment.segmentId,
      offset: Math.max(0, Number(audio.currentTime) || 0),
      speed,
    });
  }, [activeSegment?.segmentId, audioManifest, book.slug, speed]);

  const prefetchNextSegmentMetadata = useCallback((audio) => {
    if (!activeSegment?.nextSegmentId || !shouldPrefetchNextSegment(audio?.currentTime, audio?.duration, activeSegment.nextSegmentId)) return;
    const key = `${audioManifest?.packageVersion || ""}:${activeSegment.nextSegmentId}`;
    if (prefetchedSegmentsRef.current.has(key)) return;
    prefetchedSegmentsRef.current.add(key);
    // Warm only metadata. The next protected audio body remains unavailable
    // until ordinary playback reaches its ordered segment transition.
    void fetch(activeSegment.nextAudioUrl, { method: "HEAD", credentials: "include", cache: "no-store" }).catch(() => null);
  }, [activeSegment, audioManifest?.packageVersion]);

  const applyPendingOffset = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || audio.readyState < 1 || pendingOffsetSegmentRef.current !== activeSegment?.segmentId) return false;
    const requested = Math.max(0, Number(pendingOffsetRef.current) || 0);
    const maximum = Number.isFinite(audio.duration) && audio.duration > 0 ? Math.max(0, audio.duration - 0.05) : requested;
    audio.currentTime = Math.min(requested, maximum);
    pendingOffsetRef.current = null;
    pendingOffsetSegmentRef.current = "";
    return true;
  }, [activeSegment?.segmentId]);

  const seek = useCallback((next) => {
    if (!audioManifest?.valid) return;
    const target = audioSegmentAtMediaPosition(audioManifest, clampPlaybackTime(next, totalDuration));
    if (!target?.segmentId) return;
    if (target.segmentId !== activeSegment?.segmentId) {
      pendingOffsetRef.current = target.offsetSeconds;
      pendingOffsetSegmentRef.current = target.segmentId;
      resumeAfterTransitionRef.current = playing;
      setSegmentId(target.segmentId);
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = target.offsetSeconds;
    setTime((Number(activeSegment?.cumulativeStartMs || 0) / 1000) + target.offsetSeconds);
  }, [activeSegment, audioManifest, playing, totalDuration]);

  const togglePlayback = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !canPlay) return;
    if (audio.paused) requestAudiobookPlayback(audio).catch(() => onMediaError?.());
    else audio.pause();
  }, [canPlay, onMediaError]);

  const handleLoadedMetadata = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.playbackRate = speed;
    applyPendingOffset();
    if (!resumeAfterTransitionRef.current) return;
    resumeAfterTransitionRef.current = false;
    requestAudiobookPlayback(audio).catch(() => onMediaError?.());
  }, [applyPendingOffset, onMediaError, speed]);

  const handleTimeUpdate = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !activeSegment) return;
    setTime((Number(activeSegment.cumulativeStartMs || 0) / 1000) + (Number(audio.currentTime) || 0));
    persistProgress();
    prefetchNextSegmentMetadata(audio);
  }, [activeSegment, persistProgress, prefetchNextSegmentMetadata]);

  const handleEnded = useCallback(() => {
    persistProgress({ force: true });
    if (activeSegment?.nextSegmentId) {
      pendingOffsetRef.current = 0;
      pendingOffsetSegmentRef.current = activeSegment.nextSegmentId;
      resumeAfterTransitionRef.current = true;
      setSegmentId(activeSegment.nextSegmentId);
      return;
    }
    setPlaying(false);
    onPlaybackStateChange?.("paused");
    void onPlaybackComplete?.();
  }, [activeSegment?.nextSegmentId, onPlaybackComplete, onPlaybackStateChange, persistProgress]);

  const stop = useCallback(() => {
    audioRef.current?.pause();
    persistProgress({ force: true });
    void onStop?.();
  }, [onStop, persistProgress]);

  if (!presentation.canRender) return null;
  const progress = totalDuration > 0 ? Math.min(100, (time / totalDuration) * 100) : 0;

  return (
    <ExperienceShell className="listener-v2" labelledBy="listener-v2-title">
      <ExperienceHeader onSearch={() => onNavigate?.("search")} onNavigatePath={(item) => onNavigate?.(item.key === "reading-pass" ? "passes" : item.key, item.to)} trailingLabel="Library" showDesktopNavigation />
      <section className="listener-v2__layout">
        <div className="listener-v2__main">
          <div className="listener-v2__mobile-top"><button type="button" onClick={() => onNavigate?.("back")} aria-label="Back to book"><ChevronLeft size={18} /></button></div>
          <div className="listener-v2__art"><BookCoverImage book={book} alt={`${presentation.title} cover`} loading="eager" fetchPriority="high" width={480} widths={[240, 360, 480]} sizes="(min-width: 768px) 230px, 48vw" allowGraphicalFallback={false} fallback="" /></div>
          <div className="listener-v2__copy"><span className="listener-v2__eyebrow">{presentation.fixture ? "Visual review preview" : "Listening experience"}</span><h1 id="listener-v2-title">{presentation.title}</h1><p>{presentation.author}</p><small>{presentation.chapterLabel}</small>{presentation.fixture && <p className="listener-v2__fixture-notice" role="status">Playback is disabled until an approved recording is available.</p>}</div>
          {!presentation.fixture && canPlay && <audio ref={audioRef} src={activeSegment.audioUrl} preload="metadata" data-testid="listener-package-audio" data-package-version={audioManifest.packageVersion} data-segment-id={activeSegment.segmentId} onLoadedMetadata={handleLoadedMetadata} onTimeUpdate={handleTimeUpdate} onEnded={handleEnded} onPlay={() => { setPlaying(true); onPlaybackStateChange?.("playing"); }} onPause={() => { setPlaying(false); onPlaybackStateChange?.("paused"); persistProgress({ force: true }); }} onError={() => onMediaError?.()} />}
          {!presentation.fixture && <><div className="listener-v2__timeline"><div><span>{clock(time)}</span><input aria-label="Seek within approved audiobook" type="range" min="0" max={totalDuration || 0} step="0.1" value={Math.min(time, totalDuration || time)} onChange={(event) => seek(event.target.value)} disabled={!canPlay || !totalDuration} /><b style={{ width: `${progress}%` }} aria-hidden="true" /><span>{clock(totalDuration)}</span></div><p>{presentation.chapterLabel}</p></div>
          <div className="listener-v2__controls">{canPlay ? <><ExperienceIconButton label="Back 15 seconds" onClick={() => seek(time - 15)}><RotateCcw size={22} /><em>15</em></ExperienceIconButton><button type="button" className="listener-v2__play" onClick={togglePlayback} aria-label={playing ? "Pause approved audiobook" : "Play approved audiobook"}>{playing ? <Pause size={30} /> : <Play size={30} fill="currentColor" />}</button><ExperienceIconButton label="Forward 15 seconds" onClick={() => seek(time + 15)}><RotateCw size={22} /><em>15</em></ExperienceIconButton></> : <button type="button" className="listener-v2__authorize" onClick={onAuthorize} disabled={authorizing}>{authorizing ? "Authorizing listening…" : "Authorize Listening"}</button>}</div>
          {canPlay && <button type="button" className="listener-v2__stop" onClick={stop}>Stop listening</button>}
          <div className="listener-v2__utilities"><label>Speed<select value={speed} onChange={(event) => { const next = Number(event.target.value); setSpeed(next); if (audioRef.current) audioRef.current.playbackRate = next; }} disabled={!canPlay}><option value="1">1.0×</option><option value="1.25">1.25×</option><option value="1.5">1.5×</option></select></label>{readAlongSupported && <button type="button" onClick={onReadAlong}>Read Along</button>}</div></>}
        </div>
        <aside className="listener-v2__side" aria-label="Listening details">
          <section className="listener-v2__chapters" aria-labelledby="listener-v2-chapters-title">
            <div className="listener-v2__chapters-header"><h2 id="listener-v2-chapters-title">Chapters</h2><span>{chapters.length || audioManifest?.tracks?.length || 0}</span></div>
            {chapters.length > 0 ? <ol>{chapters.map((chapter, index) => {
              const current = Boolean(activeSegment?.chapterId && activeSegment.chapterId === chapter.chapterId);
              const duration = Number(chapter.track?.durationMs || 0) / 1000;
              return <li key={chapter.chapterId || chapter.title}>
                <button type="button" disabled={!canPlay || !chapter.track} aria-current={current ? "location" : undefined} onClick={() => chapter.track && seek(Number(chapter.track.cumulativeStartMs || 0) / 1000)}>
                  <span className="listener-v2__chapter-number">{String(index + 1).padStart(2, "0")}</span>
                  <span className="listener-v2__chapter-title">{chapter.title}</span>
                  {duration > 0 && <time>{clock(duration)}</time>}
                </button>
              </li>;
            })}</ol> : <p className="listener-v2__chapter-empty">Chapter details will appear with the approved listening package.</p>}
          </section>
          <ExperiencePanel eyebrow="Listening access"><p>{presentation.fixture ? "Listening requires an active Reading Pass from second 0." : `${LISTENING_ACCESS_COPY} Playback starts only after server authorization from second 0.`}</p>{onAddToLibrary ? <button type="button" onClick={onAddToLibrary}>Add to Library</button> : null}</ExperiencePanel>
          <ExperiencePanel eyebrow="Listening Pass"><p><Clock3 size={15} /> {passBalanceLabel}</p><p>{READING_TIME_COPY}</p><button type="button" onClick={() => onNavigate?.("passes")}>Extend Listening Time</button></ExperiencePanel>
        </aside>
      </section>
      <ExperienceBottomNavigation active="library" onNavigate={onNavigate} />
    </ExperienceShell>
  );
}
