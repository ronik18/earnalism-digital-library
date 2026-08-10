import { useEffect } from 'react';
import {
  BookOpen,
  Gauge,
  Pause,
  Play,
  RotateCcw,
  RotateCw,
  ShieldCheck,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react';
import './ReaderAudiobookPanel.css';

const PLAYBACK_RATES = [0.75, 1, 1.25, 1.5, 1.75];

export function formatAudiobookTime(value = 0) {
  const seconds = Math.max(0, Math.floor(Number(value) || 0));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = String(seconds % 60).padStart(2, '0');
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, '0')}:${remainder}`
    : `${minutes}:${remainder}`;
}

export default function ReaderAudiobookPanel({
  title,
  bookSlug,
  author,
  coverUrl,
  isPlaying,
  isPaused,
  canPlay,
  isReadingPage,
  currentTime,
  duration,
  playbackRate,
  volume,
  muted,
  syncLabel,
  disclosure,
  onClose,
  onPlayPause,
  onSkip,
  onSeek,
  onPlaybackRateChange,
  onVolumeChange,
  onToggleMute,
  onOpenReadingPage,
}) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose?.();
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  const safeDuration = Math.max(0, Number(duration) || 0);
  const safeCurrentTime = Math.min(safeDuration || Infinity, Math.max(0, Number(currentTime) || 0));
  const progressPercent = safeDuration > 0 ? Math.min(100, (safeCurrentTime / safeDuration) * 100) : 0;
  const playbackLabel = isPlaying && !isPaused ? 'Pause audiobook' : 'Play audiobook';
  const statusText = !isReadingPage
    ? 'Open the first narrated page, then press Play when the section is ready.'
    : canPlay
      ? (isPlaying && !isPaused ? 'Narration is following the current reading section.' : 'Your narrated section is ready when you are.')
      : 'Preparing approved audio for this reading section…';

  return (
    <section
      className="reader-listening-room"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reader-listening-room-title"
      aria-describedby="reader-listening-room-status"
      data-testid="reader-audiobook-panel"
      data-book-slug={bookSlug || undefined}
    >
      {coverUrl ? (
        <img className="reader-listening-room__backdrop" src={coverUrl} alt="" aria-hidden="true" decoding="async" />
      ) : null}
      <div className="reader-listening-room__veil" aria-hidden="true" />

      <div className="reader-listening-room__shell">
        <header className="reader-listening-room__topline">
          <span className="reader-listening-room__eyebrow">
            <ShieldCheck size={15} aria-hidden="true" />
            Now listening
          </span>
          <button type="button" className="reader-listening-room__close" onClick={onClose} aria-label="Close audiobook player" autoFocus>
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        <h1 id="reader-listening-room-title" className="sr-only">
          {title || 'Audiobook'} audiobook player
        </h1>

        <div className="reader-listening-room__artwork-shell">
          {coverUrl ? (
            <img
              className="reader-listening-room__artwork"
              src={coverUrl}
              alt={`${title || 'Audiobook'} front cover`}
              width="560"
              height="840"
              loading="eager"
              fetchPriority="high"
              decoding="async"
            />
          ) : (
            <div className="reader-listening-room__artwork reader-listening-room__artwork--empty" role="img" aria-label={`${title || 'Audiobook'} cover artwork is being prepared`}>
              <span>Earnalism listening edition</span>
              <strong>{title || 'Audiobook'}</strong>
              {author ? <small>{author}</small> : null}
            </div>
          )}
        </div>

        <div className="reader-listening-room__timeline">
          <div className="reader-listening-room__progress-shell">
            <input
              type="range"
              min="0"
              max={safeDuration || 0}
              step="0.1"
              value={safeCurrentTime}
              onChange={(event) => onSeek?.(Number(event.target.value))}
              disabled={!canPlay || safeDuration <= 0}
              aria-label="Seek within current audiobook section"
            />
            <span style={{ '--listening-progress': `${progressPercent}%` }} aria-hidden="true" />
          </div>
          <div className="reader-listening-room__time" aria-live="off">
            <span>{formatAudiobookTime(safeCurrentTime)}</span>
            <span>{safeDuration > 0 ? formatAudiobookTime(safeDuration) : '—:—'}</span>
          </div>
        </div>

        <div className="reader-listening-room__controls" aria-label="Audiobook playback controls">
          <button type="button" onClick={() => onSkip?.(-15)} disabled={!canPlay} aria-label="Skip back 15 seconds">
            <RotateCcw size={23} strokeWidth={1.55} aria-hidden="true" />
            <span>15</span>
          </button>
          <button
            type="button"
            className="reader-listening-room__play"
            onClick={onPlayPause}
            disabled={!canPlay}
            aria-label={playbackLabel}
          >
            {isPlaying && !isPaused
              ? <Pause size={27} strokeWidth={1.5} aria-hidden="true" />
              : <Play size={27} strokeWidth={1.5} aria-hidden="true" />}
          </button>
          <button type="button" onClick={() => onSkip?.(30)} disabled={!canPlay} aria-label="Skip forward 30 seconds">
            <RotateCw size={23} strokeWidth={1.55} aria-hidden="true" />
            <span>30</span>
          </button>
        </div>

        <p id="reader-listening-room-status" className="reader-listening-room__status" aria-live="polite">
          {statusText}
        </p>

        <div className="reader-listening-room__utilities">
          <label>
            <Gauge size={17} aria-hidden="true" />
            <span className="sr-only">Playback speed</span>
            <select value={playbackRate} onChange={(event) => onPlaybackRateChange?.(Number(event.target.value))} aria-label="Playback speed">
              {PLAYBACK_RATES.map((rate) => <option key={rate} value={rate}>{rate}×</option>)}
            </select>
          </label>

          <label className="reader-listening-room__volume">
            <button type="button" onClick={onToggleMute} aria-label={muted ? 'Unmute audiobook' : 'Mute audiobook'}>
              {muted ? <VolumeX size={18} aria-hidden="true" /> : <Volume2 size={18} aria-hidden="true" />}
            </button>
            <span className="sr-only">Audiobook volume</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={muted ? 0 : volume}
              onChange={(event) => onVolumeChange?.(Number(event.target.value))}
              aria-label="Audiobook volume"
            />
          </label>
        </div>

        <div className="reader-listening-room__meta">
          <span>{syncLabel || 'Section-following narration'}</span>
          {disclosure ? <small>{disclosure}</small> : null}
        </div>

        <button type="button" className="reader-listening-room__reading-cta" onClick={onOpenReadingPage}>
          <BookOpen size={18} aria-hidden="true" />
          {isReadingPage ? 'Read along' : 'Open first narrated page'}
        </button>
      </div>
    </section>
  );
}
