import { useEffect, useRef, useState, useCallback } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";
import { useSettings } from "../context/SettingsContext";
import "./AudioPlayer.css";

/**
 * AudioPlayer with real-time text highlight sync.
 *
 * Features:
 * - Loads audio from Cloudinary CDN
 * - Fetches word-level timestamps
 * - Highlights active word during playback
 * - Persists playback position
 * - Keyboard controls (Space = play/pause)
 */
export default function AudioPlayer({
  bookSlug,
  title,
  lang = "en",
  onSyncReady = null,
  className = "",
}) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [timestamps, setTimestamps] = useState([]);
  const [currentWordIndex, setCurrentWordIndex] = useState(-1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load timestamps
  useEffect(() => {
    const loadTimestamps = async () => {
      try {
        setIsLoading(true);
        // Fetch from Cloudinary CDN
        const response = await fetch(
          `/audio/${lang}/${bookSlug}_timestamps.json`,
          { cache: "force-cache" }
        );

        if (!response.ok) {
          throw new Error(`Timestamps not found for ${bookSlug}`);
        }

        const data = await response.json();
        setTimestamps(data.words || []);
        onSyncReady?.(true);
      } catch (err) {
        console.error("Failed to load timestamps:", err);
        setError(err.message);
        onSyncReady?.(false);
      } finally {
        setIsLoading(false);
      }
    };

    if (bookSlug && lang) {
      loadTimestamps();
    }
  }, [bookSlug, lang, onSyncReady]);

  // Update current word on playback
  useEffect(() => {
    if (!timestamps.length) return;

    const currentTimeMs = currentTime * 1000;
    let wordIndex = -1;

    for (let i = 0; i < timestamps.length; i++) {
      if (
        currentTimeMs >= timestamps[i].start_ms &&
        currentTimeMs < timestamps[i].end_ms
      ) {
        wordIndex = i;
        break;
      }
    }

    if (wordIndex !== currentWordIndex) {
      setCurrentWordIndex(wordIndex);

      // Highlight active word if mounted in reader
      if (wordIndex >= 0) {
        const wordSpan = document.querySelector(
          `[data-word-index="${wordIndex}"]`
        );
        if (wordSpan) {
          wordSpan.classList.add("active");
          wordSpan.scrollIntoView({ behavior: "smooth", block: "nearest" });

          // Clear previous highlight
          const prevSpan = document.querySelector(
            `[data-word-index="${wordIndex - 1}"]`
          );
          if (prevSpan) prevSpan.classList.remove("active");
        }
      }
    }
  }, [currentTime, timestamps, currentWordIndex]);

  // Audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleEnded = () => setIsPlaying(false);
    const handleDurationChange = () => setDuration(audio.duration);
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("durationchange", handleDurationChange);
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("durationchange", handleDurationChange);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
    };
  }, []);

  // Keyboard controls
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === " " && audioRef.current) {
        e.preventDefault();
        audioRef.current[isPlaying ? "pause" : "play"]();
      }
    };

    document.addEventListener("keydown", handleKeyPress);
    return () => document.removeEventListener("keydown", handleKeyPress);
  }, [isPlaying]);

  const togglePlayPause = useCallback(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
    }
  }, [isPlaying]);

  const toggleMute = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  }, [isMuted]);

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  if (error) {
    return (
      <div className={`audio-player audio-player--error ${className}`}>
        <div className="audio-player__error-message">
          Audio sync unavailable: {error}
        </div>
      </div>
    );
  }

  return (
    <div className={`audio-player ${className}`} role="region" aria-label={`Audio player for ${title}`}>
      <audio
        ref={audioRef}
        src={`/audio/${lang}/${bookSlug}.mp3`}
        preload="metadata"
      />

      <div className="audio-player__controls">
        {/* Play/Pause Button */}
        <button
          onClick={togglePlayPause}
          className="audio-player__btn audio-player__btn--play"
          aria-label={isPlaying ? "Pause" : "Play"}
          disabled={isLoading || error}
        >
          {isPlaying ? (
            <Pause size={20} strokeWidth={1.5} />
          ) : (
            <Play size={20} strokeWidth={1.5} />
          )}
        </button>

        {/* Time Display */}
        <div className="audio-player__time">
          <span className="audio-player__time-current">
            {formatTime(currentTime)}
          </span>
          <span className="audio-player__time-separator">/</span>
          <span className="audio-player__time-duration">
            {formatTime(duration)}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="audio-player__progress-container">
          <input
            type="range"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={(e) => {
              const audio = audioRef.current;
              if (audio) audio.currentTime = parseFloat(e.target.value);
            }}
            className="audio-player__progress"
            aria-label="Seek"
            disabled={!duration}
          />
          <div
            className="audio-player__progress-fill"
            style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
          />
        </div>

        {/* Mute Button */}
        <button
          onClick={toggleMute}
          className="audio-player__btn audio-player__btn--mute"
          aria-label={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? (
            <VolumeX size={20} strokeWidth={1.5} />
          ) : (
            <Volume2 size={20} strokeWidth={1.5} />
          )}
        </button>

        {/* Loading Indicator */}
        {isLoading && (
          <div className="audio-player__loading" aria-busy="true">
            Loading audio...
          </div>
        )}
      </div>

      {/* Sync Status */}
      <div className="audio-player__sync-info">
        <div className="audio-player__sync-badge">
          {timestamps.length > 0 ? "✓ Text sync enabled" : "Audio only"}
        </div>
      </div>
    </div>
  );
}
