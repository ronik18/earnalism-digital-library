import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Clock3, Ellipsis, Pause, Play, RotateCcw, RotateCw, TimerReset } from "lucide-react";
import ExperienceBottomNavigation from "../shared/ExperienceBottomNavigation";
import ExperienceHeader from "../shared/ExperienceHeader";
import ExperienceIconButton from "../shared/ExperienceIconButton";
import ExperiencePanel from "../shared/ExperiencePanel";
import ExperienceShell from "../shared/ExperienceShell";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";
import { LISTENING_ACCESS_COPY, READING_TIME_COPY } from "../../lib/publicAccessCopy";
import "./listener-v2.css";

const clock = (seconds = 0) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

export function clampPlaybackTime(seconds, durationSeconds) {
  const value = Math.max(0, Number(seconds) || 0);
  return durationSeconds > 0 ? Math.min(value, durationSeconds) : value;
}

export default function ListenerExperienceV2({ book = {}, fixture = false, access = {}, onAuthorize, onPlaybackStateChange, onNavigate, onAddToLibrary, onReadAlong, readAlongSupported = false }) {
  const presentation = listenerReleasePresentation(book, { fixture });
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(presentation.durationSeconds || 0);
  const [speed, setSpeed] = useState(1);

  useEffect(() => () => { audioRef.current?.pause(); }, []);
  const seek = useCallback((next) => {
    const audio = audioRef.current;
    if (!audio) return;
    const safeTime = clampPlaybackTime(next, duration);
    audio.currentTime = safeTime;
    setTime(safeTime);
  }, [duration]);
  const togglePlayback = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) audio.play().catch(() => setPlaying(false)); else audio.pause();
  }, []);
  const onTimeUpdate = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const safeTime = clampPlaybackTime(audio.currentTime, duration);
    if (safeTime !== audio.currentTime) { audio.pause(); audio.currentTime = safeTime; }
    setTime(safeTime);
  }, [duration]);

  if (!presentation.canRender) return null;
  const effectiveDuration = duration;
  const progress = effectiveDuration > 0 ? Math.min(100, (time / effectiveDuration) * 100) : 0;

  return (
    <ExperienceShell className="listener-v2" labelledBy="listener-v2-title">
      <ExperienceHeader onSearch={() => onNavigate?.("search")} trailingLabel="Library" />
      <section className="listener-v2__layout">
        <div className="listener-v2__main">
          <div className="listener-v2__art" aria-hidden="true"><span>Earnalism</span><strong>{presentation.title}</strong></div>
          <div className="listener-v2__copy"><span className="listener-v2__eyebrow">{presentation.fixture ? "Approved-audio visual fixture" : "Audiobook available"}</span><h1 id="listener-v2-title">{presentation.title}</h1><p>{presentation.author}</p><small>{presentation.chapterLabel}</small></div>
          {!presentation.fixture && access.authorized && presentation.mediaUrl && <audio ref={audioRef} src={presentation.mediaUrl} preload="metadata" onLoadedMetadata={(event) => setDuration(Number(event.currentTarget.duration) || 0)} onTimeUpdate={onTimeUpdate} onPlay={() => { setPlaying(true); onPlaybackStateChange?.("playing"); }} onPause={() => { setPlaying(false); onPlaybackStateChange?.("paused"); }} />}
          <div className="listener-v2__timeline"><div><span>{clock(time)}</span><input aria-label="Seek within approved audiobook" type="range" min="0" max={effectiveDuration || 0} step="0.1" value={Math.min(time, effectiveDuration || time)} onChange={(event) => seek(event.target.value)} disabled={presentation.fixture || !access.authorized || !effectiveDuration} /><b style={{ width: `${progress}%` }} aria-hidden="true" /><span>{clock(effectiveDuration)}</span></div><p>{presentation.chapterLabel}</p></div>
          <div className="listener-v2__controls">{access.authorized || presentation.fixture ? <><ExperienceIconButton label="Back 15 seconds" onClick={() => seek(time - 15)} disabled={presentation.fixture}><RotateCcw size={22} /><em>15</em></ExperienceIconButton><button type="button" className="listener-v2__play" onClick={togglePlayback} disabled={presentation.fixture} aria-label={playing ? "Pause approved audiobook" : "Play approved audiobook"}>{playing ? <Pause size={30} /> : <Play size={30} fill="currentColor" />}</button><ExperienceIconButton label="Forward 15 seconds" onClick={() => seek(time + 15)} disabled={presentation.fixture}><RotateCw size={22} /><em>15</em></ExperienceIconButton></> : <button type="button" className="listener-v2__authorize" onClick={onAuthorize}>Authorize Listening</button>}</div>
          <div className="listener-v2__utilities"><label>Speed<select value={speed} onChange={(event) => { const next = Number(event.target.value); setSpeed(next); if (audioRef.current) audioRef.current.playbackRate = next; }} disabled={presentation.fixture}><option value="1">1.0×</option><option value="1.25">1.25×</option><option value="1.5">1.5×</option></select></label><button type="button" onClick={() => onNavigate?.("timer")}><TimerReset size={16} /> Sleep</button>{readAlongSupported && <button type="button" onClick={onReadAlong}>Read Along</button>}<button type="button" onClick={() => onNavigate?.("more")}><Ellipsis size={18} /> More</button></div>
          <div className="listener-v2__mobile-top"><button type="button" onClick={() => onNavigate?.("back")} aria-label="Back"><ChevronLeft size={18} /></button><button type="button" onClick={() => onNavigate?.("more")} aria-label="More options"><Ellipsis size={20} /></button></div>
        </div>
        <aside className="listener-v2__side">
          {presentation.fixture ? <ExperiencePanel eyebrow="Up next"><ol><li><span>Chapter 4</span><b>The Visitors</b><small>22:18</small></li><li><span>Chapter 5</span><b>Jonathan’s Diary</b><small>18:05</small></li><li><span>Chapter 6</span><b>Lucy’s Diary</b><small>10:40</small></li></ol><button type="button" onClick={() => onNavigate?.("chapters")}>View all chapters <ChevronRight size={14} /></button></ExperiencePanel> : null}
          <ExperiencePanel eyebrow="Listening access"><p>{LISTENING_ACCESS_COPY} Playback starts only after server authorization from second 0.</p>{onAddToLibrary ? <button type="button" onClick={onAddToLibrary}>Add to Library</button> : null}</ExperiencePanel>
          <ExperiencePanel eyebrow="Reading Pass"><p><Clock3 size={15} /> {READING_TIME_COPY}</p><button type="button" onClick={() => onNavigate?.("passes")}>Explore Reading Passes</button></ExperiencePanel>
        </aside>
      </section>
      <ExperienceBottomNavigation active="library" onNavigate={onNavigate} />
    </ExperienceShell>
  );
}
