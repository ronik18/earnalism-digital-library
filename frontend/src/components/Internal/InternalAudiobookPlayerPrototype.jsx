import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Bookmark,
  BookmarkCheck,
  Clock,
  Forward,
  ListMusic,
  Pause,
  Play,
  Rewind,
  Timer,
} from "lucide-react";

export const INTERNAL_AUDIOBOOK_PLAYER_FLAG = "REACT_APP_ENABLE_INTERNAL_AUDIOBOOK_PLAYER_PROTOTYPE";

export function isInternalAudiobookPlayerPrototypeEnabled(env = process.env) {
  return env?.[INTERNAL_AUDIOBOOK_PLAYER_FLAG] === "true" && env?.NODE_ENV !== "production";
}

const MOCK_CHAPTERS = [
  { id: "chapter-1-preview", title: "Chapter 1 Preview", durationSeconds: 540 },
  { id: "chapter-2-placeholder", title: "Chapter 2 Placeholder", durationSeconds: 480 },
  { id: "chapter-3-placeholder", title: "Chapter 3 Placeholder", durationSeconds: 510 },
];

const PLAYBACK_SPEEDS = ["0.8", "1", "1.15", "1.3"];

function formatTime(seconds) {
  const safeSeconds = Math.max(0, Math.round(Number(seconds) || 0));
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = safeSeconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function PrototypeUnavailable() {
  return (
    <section
      className="card-elegant mx-auto max-w-3xl p-6 sm:p-8"
      data-testid="internal-audiobook-prototype-blocked"
      aria-labelledby="internal-audiobook-prototype-blocked-title"
    >
      <div className="overline mb-3">Internal prototype unavailable</div>
      <h2 id="internal-audiobook-prototype-blocked-title" className="font-serif-display text-3xl text-burgundy">
        Audiobook player prototype is gated.
      </h2>
      <p className="mt-4 text-charcoal-soft leading-relaxed">
        This internal-only interface is hidden in public builds. Public audiobook release remains blocked until rights,
        QA, owner approval, and assistive-technology review are complete.
      </p>
    </section>
  );
}

export default function InternalAudiobookPlayerPrototype({
  enabled = isInternalAudiobookPlayerPrototypeEnabled(),
  initialState = "ready",
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [activeChapterId, setActiveChapterId] = useState(MOCK_CHAPTERS[0].id);
  const [elapsedSeconds, setElapsedSeconds] = useState(84);
  const [playbackSpeed, setPlaybackSpeed] = useState("1");
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  const [sleepTimer, setSleepTimer] = useState("off");
  const [statusMessage, setStatusMessage] = useState("Prototype ready. No audio file is loaded.");

  const activeChapter = useMemo(
    () => MOCK_CHAPTERS.find((chapter) => chapter.id === activeChapterId) || MOCK_CHAPTERS[0],
    [activeChapterId],
  );
  const durationSeconds = activeChapter.durationSeconds;
  const remainingSeconds = Math.max(0, durationSeconds - elapsedSeconds);
  const progressPercent = durationSeconds ? Math.round((elapsedSeconds / durationSeconds) * 100) : 0;
  const isLoading = initialState === "loading";
  const hasError = initialState === "error";
  const isBlocked = initialState === "blocked";

  if (!enabled) {
    return <PrototypeUnavailable />;
  }

  function announce(nextMessage) {
    setStatusMessage(nextMessage);
  }

  function togglePlayback() {
    if (isLoading || hasError || isBlocked) return;
    setIsPlaying((value) => {
      const next = !value;
      announce(next ? "Prototype playback state changed to playing." : "Prototype playback state changed to paused.");
      return next;
    });
  }

  function moveBy(seconds) {
    if (isLoading || hasError || isBlocked) return;
    setElapsedSeconds((value) => {
      const next = clamp(value + seconds, 0, durationSeconds);
      announce(`Prototype position moved to ${formatTime(next)} in ${activeChapter.title}.`);
      return next;
    });
  }

  function changeChapter(chapter) {
    setActiveChapterId(chapter.id);
    setElapsedSeconds(0);
    setIsPlaying(false);
    announce(`Chapter changed to ${chapter.title}.`);
  }

  function toggleBookmark() {
    setBookmarked((value) => {
      const next = !value;
      announce(next ? "Prototype bookmark saved for this position." : "Prototype bookmark removed.");
      return next;
    });
  }

  return (
    <section
      className="mx-auto max-w-5xl rounded-xl border border-brand-soft bg-[#FFFDF8] p-5 shadow-[0_32px_80px_-56px_rgba(74,28,39,0.72)] sm:p-8"
      data-testid="internal-audiobook-player-prototype"
      aria-labelledby="internal-audiobook-player-title"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="overline mb-3">Internal listening-room prototype</div>
          <h2 id="internal-audiobook-player-title" className="font-serif-display text-3xl leading-tight text-burgundy sm:text-4xl">
            Premium audiobook controls, blocked from public release.
          </h2>
          <p className="mt-4 max-w-2xl text-charcoal-soft leading-relaxed">
            Safe mock metadata only. No audio file, provider URL, generated voice, public claim, or real playback asset is loaded here.
          </p>
        </div>
        <div className="rounded-lg border border-brand-soft bg-ivory-warm px-4 py-3 text-sm text-charcoal-soft" data-testid="prototype-release-state">
          <strong className="text-burgundy">Release state:</strong> PUBLIC_AUDIO_RELEASE_BLOCKED
        </div>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-xl border border-brand-soft bg-white p-5 sm:p-6">
          {isLoading && (
            <div role="status" aria-live="polite" className="mb-5 rounded-lg border border-brand-soft bg-ivory-warm p-4 text-charcoal-soft">
              Loading safe prototype metadata. No audio request is being made.
            </div>
          )}
          {hasError && (
            <div role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-red-900">
              Prototype error state: audio remains unavailable and no media asset can be loaded.
            </div>
          )}
          {isBlocked && (
            <div role="alert" className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950">
              Blocked state: release evidence is incomplete, so public audiobook controls stay unavailable.
            </div>
          )}

          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-burgundy text-ivory shadow-[0_16px_34px_-24px_rgba(74,28,39,0.9)]" aria-hidden="true">
              <ListMusic size={24} strokeWidth={1.5} />
            </div>
            <div>
              <p className="overline mb-2">Current chapter</p>
              <h3 className="font-serif-display text-2xl text-burgundy">{activeChapter.title}</h3>
              <p className="mt-2 text-sm text-charcoal-soft">
                Resume position: {formatTime(elapsedSeconds)}. Remaining time: {formatTime(remainingSeconds)}.
              </p>
            </div>
          </div>

          <div className="mt-7" aria-label="Prototype progress">
            <div
              className="h-3 overflow-hidden rounded-full bg-ivory-warm"
              role="progressbar"
              aria-valuemin="0"
              aria-valuemax="100"
              aria-valuenow={progressPercent}
              aria-valuetext={`${progressPercent}% complete, ${formatTime(elapsedSeconds)} elapsed, ${formatTime(remainingSeconds)} remaining`}
            >
              <div className="h-full rounded-full bg-gold" style={{ width: `${progressPercent}%` }} />
            </div>
            <div className="mt-3 flex justify-between text-sm text-charcoal-soft">
              <span>Elapsed {formatTime(elapsedSeconds)}</span>
              <span>Remaining {formatTime(remainingSeconds)}</span>
            </div>
          </div>

          <div className="mt-7 grid grid-cols-3 gap-3 sm:grid-cols-[auto_auto_auto_1fr] sm:items-center">
            <button
              type="button"
              className="btn-secondary justify-center"
              onClick={() => moveBy(-10)}
              aria-label="Rewind prototype by 10 seconds"
              disabled={isLoading || hasError || isBlocked}
            >
              <Rewind size={17} strokeWidth={1.6} />
              <span>10 sec</span>
            </button>
            <button
              type="button"
              className="btn-primary justify-center text-base"
              onClick={togglePlayback}
              aria-label={isPlaying ? "Pause internal audiobook prototype" : "Play internal audiobook prototype"}
              aria-pressed={isPlaying}
              disabled={isLoading || hasError || isBlocked}
            >
              {isPlaying ? <Pause size={19} strokeWidth={1.6} /> : <Play size={19} strokeWidth={1.6} />}
              <span>{isPlaying ? "Pause prototype" : "Play prototype"}</span>
            </button>
            <button
              type="button"
              className="btn-secondary justify-center"
              onClick={() => moveBy(30)}
              aria-label="Forward prototype by 30 seconds"
              disabled={isLoading || hasError || isBlocked}
            >
              <Forward size={17} strokeWidth={1.6} />
              <span>30 sec</span>
            </button>
            <p className="col-span-3 text-sm text-charcoal-soft sm:col-span-1">
              Poor network state: keep the place saved, explain the retry, and never start a full-file download.
            </p>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <label className="block text-sm text-charcoal-soft">
              <span className="mb-2 block font-medium text-burgundy">Playback speed</span>
              <select
                className="w-full rounded-lg border border-brand-soft bg-white px-3 py-2 text-charcoal"
                value={playbackSpeed}
                onChange={(event) => {
                  setPlaybackSpeed(event.target.value);
                  announce(`Prototype playback speed set to ${event.target.value} times.`);
                }}
                aria-label="Prototype playback speed"
              >
                {PLAYBACK_SPEEDS.map((speed) => (
                  <option key={speed} value={speed}>{speed}x</option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-charcoal-soft">
              <span className="mb-2 block font-medium text-burgundy">Sleep timer</span>
              <select
                className="w-full rounded-lg border border-brand-soft bg-white px-3 py-2 text-charcoal"
                value={sleepTimer}
                onChange={(event) => {
                  setSleepTimer(event.target.value);
                  announce(`Prototype sleep timer set to ${event.target.value}.`);
                }}
                aria-label="Prototype sleep timer"
              >
                <option value="off">Off</option>
                <option value="10 minutes">10 minutes</option>
                <option value="20 minutes">20 minutes</option>
                <option value="end of chapter">End of chapter</option>
              </select>
            </label>
            <button
              type="button"
              className="btn-secondary justify-center self-end"
              onClick={toggleBookmark}
              aria-label={bookmarked ? "Remove prototype bookmark" : "Bookmark prototype position"}
              aria-pressed={bookmarked}
            >
              {bookmarked ? <BookmarkCheck size={17} strokeWidth={1.6} /> : <Bookmark size={17} strokeWidth={1.6} />}
              <span>{bookmarked ? "Bookmarked" : "Bookmark"}</span>
            </button>
          </div>

          <div className="sr-only" aria-live="polite" data-testid="prototype-live-region">
            {statusMessage}
          </div>
        </div>

        <aside className="space-y-5">
          <section className="rounded-xl border border-brand-soft bg-white p-5" aria-labelledby="prototype-chapters-title">
            <h3 id="prototype-chapters-title" className="font-serif-display text-2xl text-burgundy">Chapters</h3>
            <div className="mt-4 space-y-2">
              {MOCK_CHAPTERS.map((chapter, index) => (
                <button
                  key={chapter.id}
                  type="button"
                  className={`w-full rounded-lg border px-4 py-3 text-left transition-colors ${
                    chapter.id === activeChapterId
                      ? "border-burgundy bg-ivory-warm text-burgundy"
                      : "border-brand-soft bg-white text-charcoal-soft hover:border-gold"
                  }`}
                  onClick={() => changeChapter(chapter)}
                  aria-current={chapter.id === activeChapterId ? "true" : undefined}
                >
                  <span className="block text-xs uppercase tracking-[0.16em] text-gold-deep">Chapter {index + 1}</span>
                  <span className="block font-serif-display text-lg">{chapter.title}</span>
                  <span className="block text-sm">{formatTime(chapter.durationSeconds)}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-brand-soft bg-white p-5" aria-labelledby="prototype-transcript-title">
            <div className="flex items-center justify-between gap-3">
              <h3 id="prototype-transcript-title" className="font-serif-display text-2xl text-burgundy">Transcript</h3>
              <button
                type="button"
                className="text-sm text-burgundy underline decoration-gold/60 underline-offset-4"
                onClick={() => {
                  setTranscriptOpen((value) => !value);
                  announce(transcriptOpen ? "Prototype transcript panel collapsed." : "Prototype transcript panel expanded.");
                }}
                aria-expanded={transcriptOpen}
                aria-controls="prototype-transcript-panel"
              >
                {transcriptOpen ? "Hide" : "Show"}
              </button>
            </div>
            <div id="prototype-transcript-panel" className="mt-4 text-sm leading-relaxed text-charcoal-soft">
              {transcriptOpen ? (
                <p>
                  Transcript placeholder only. Future release requires source-matched text, sync tolerance evidence, and
                  human listening review before public audio can appear.
                </p>
              ) : (
                <p>Transcript placeholder is collapsed.</p>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-brand-soft bg-ivory-warm p-5" aria-labelledby="prototype-safety-title">
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} strokeWidth={1.6} className="text-gold-deep" aria-hidden="true" />
              <h3 id="prototype-safety-title" className="font-serif-display text-xl text-burgundy">Release blockers</h3>
            </div>
            <ul className="mt-3 space-y-2 text-sm leading-relaxed text-charcoal-soft">
              <li><Clock size={14} className="mr-2 inline text-gold-deep" aria-hidden="true" />Derivative audiobook rights not approved.</li>
              <li><Timer size={14} className="mr-2 inline text-gold-deep" aria-hidden="true" />Manual assistive-technology review still required.</li>
              <li>No public audio URL, media asset, or listening CTA is present.</li>
            </ul>
          </section>
        </aside>
      </div>
    </section>
  );
}
