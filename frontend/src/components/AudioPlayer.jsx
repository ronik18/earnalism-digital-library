import { useCallback, useEffect, useRef, useState } from "react";
import { Pause, Play, ShieldCheck, Volume2, VolumeX } from "lucide-react";
import {
  audiobookAssetsForBook,
  audiobookReleaseState,
} from "../lib/audioReleaseSafety";
import "./AudioPlayer.css";

function firstText(...values) {
  return values.map((value) => String(value || "").trim()).find(Boolean) || "";
}

function formatClock(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "0:00";
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function hasSectionTimingEvidence(book = {}) {
  const assets = audiobookAssetsForBook(book);
  return Boolean(
    assets.timestamps ||
      assets.vtt ||
      assets.highlight_vtt ||
      assets.chapters ||
      assets.meta ||
      assets.manifest ||
      book?._readerManifest?.audio?.assets?.timestamps ||
      book?._readerManifest?.audio?.assets?.vtt
  );
}

export function audioPlayerPresentationForBook(book = {}) {
  const releaseState = audiobookReleaseState(book);

  if (!releaseState.canShowControls || !releaseState.audioUrl) {
    return {
      canRender: false,
      releaseState,
      reason: releaseState.reason || "Approved audiobook evidence is missing.",
    };
  }

  const title = firstText(
    book.public_title,
    book.display_title,
    book.title,
    book.name,
    "Approved audiobook"
  );
  const author = firstText(book.author, book.author_name, book.creator);
  const sectionTiming = hasSectionTimingEvidence(book);

  return {
    canRender: true,
    audioUrl: releaseState.audioUrl,
    title,
    author,
    releaseState,
    sectionTiming,
    syncLabel: "Section-following narration",
    syncDescription: sectionTiming
      ? "Measured paragraph or stanza timing is attached to this approved audiobook."
      : "Playback is available from approved release evidence; section timing appears when approved sidecars are present.",
  };
}

export default function AudioPlayer({
  book,
  className = "",
  onPlaybackStateChange = null,
}) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [mediaReady, setMediaReady] = useState(false);
  const presentation = audioPlayerPresentationForBook(book);

  useEffect(() => {
    onPlaybackStateChange?.(isPlaying ? "playing" : "paused");
  }, [isPlaying, onPlaybackStateChange]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return undefined;

    const handleLoadedMetadata = () => {
      setDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
      setMediaReady(true);
    };
    const handleTimeUpdate = () => setCurrentTime(audio.currentTime || 0);
    const handleEnded = () => setIsPlaying(false);
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("durationchange", handleLoadedMetadata);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);

    return () => {
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("durationchange", handleLoadedMetadata);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
    };
  }, [presentation.audioUrl]);

  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
      return;
    }
    audio.play().catch(() => setIsPlaying(false));
  }, [isPlaying]);

  const toggleMute = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const nextMuted = !audio.muted;
    audio.muted = nextMuted;
    setIsMuted(nextMuted);
  }, []);

  const handleSeek = useCallback((event) => {
    const audio = audioRef.current;
    if (!audio) return;
    const nextTime = Number(event.target.value) || 0;
    audio.currentTime = nextTime;
    setCurrentTime(nextTime);
  }, []);

  if (!presentation.canRender) return null;

  const progressPercent = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;
  const labelTitle = presentation.title || "approved audiobook";

  return (
    <section
      className={`audio-player ${className}`.trim()}
      aria-label={`Approved audiobook player for ${labelTitle}`}
      data-testid="approved-audiobook-player"
    >
      <audio
        ref={audioRef}
        src={presentation.audioUrl}
        preload="metadata"
        data-testid="approved-audiobook-audio"
      />

      <div className="audio-player__header">
        <div className="audio-player__copy">
          <span className="audio-player__eyebrow">
            <ShieldCheck size={14} aria-hidden="true" />
            Approved audiobook
          </span>
          <h2 className="audio-player__title">{presentation.title}</h2>
          {presentation.author && (
            <p className="audio-player__summary">Narration for {presentation.author}</p>
          )}
        </div>
        <span className="audio-player__sync-badge" data-testid="approved-audiobook-sync">
          {presentation.syncLabel}
        </span>
      </div>

      <p className="audio-player__status">{presentation.syncDescription}</p>

      <div className="audio-player__controls">
        <button
          type="button"
          onClick={togglePlayPause}
          className="audio-player__btn audio-player__btn--play"
          aria-label={isPlaying ? "Pause approved audiobook" : "Play approved audiobook"}
        >
          {isPlaying ? <Pause size={20} strokeWidth={1.5} /> : <Play size={20} strokeWidth={1.5} />}
        </button>

        <div className="audio-player__time" aria-live="off">
          <span>{formatClock(currentTime)}</span>
          <span aria-hidden="true">/</span>
          <span>{formatClock(duration)}</span>
        </div>

        <div className="audio-player__progress-container">
          <input
            type="range"
            min="0"
            max={duration || 0}
            step="0.1"
            value={Math.min(currentTime, duration || currentTime)}
            onChange={handleSeek}
            className="audio-player__progress"
            aria-label="Seek within approved audiobook"
            disabled={!mediaReady || !duration}
          />
          <div
            className="audio-player__progress-fill"
            style={{ width: `${progressPercent}%` }}
            aria-hidden="true"
          />
        </div>

        <button
          type="button"
          onClick={toggleMute}
          className="audio-player__btn audio-player__btn--mute"
          aria-label={isMuted ? "Unmute approved audiobook" : "Mute approved audiobook"}
        >
          {isMuted ? <VolumeX size={20} strokeWidth={1.5} /> : <Volume2 size={20} strokeWidth={1.5} />}
        </button>
      </div>
    </section>
  );
}
