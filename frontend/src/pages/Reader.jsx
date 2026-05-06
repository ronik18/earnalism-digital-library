import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Menu, X, Sun, Moon, Type, ArrowLeft, Clock, Lock } from "lucide-react";
import { api, userApi, formatMinutes } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const PREFS_KEY = "earnalism_reader_prefs";
const DEFAULT_PREFS = { theme: "light", fontSize: 18 };
const FONT_SIZES = [16, 18, 20, 22];
const THEMES = ["light", "sepia", "dark"];
const HEARTBEAT_MS = 30_000;
const IDLE_MS = 60_000; // 60s without input = idle

function loadPrefs() {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
}
function savePrefs(p) {
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(p)); } catch { /* storage unavailable */ }
}

export default function Reader() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { user, refreshUser, setUserBalance } = useAuth();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prefs, setPrefs] = useState(loadPrefs);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // session state
  const [sessionId, setSessionId] = useState(null);
  const [remaining, setRemaining] = useState(0);
  const [depleted, setDepleted] = useState(false);
  const idleSinceRef = useRef(Date.now());
  const visibleRef = useRef(typeof document !== "undefined" ? document.visibilityState !== "hidden" : true);

  useEffect(() => { savePrefs(prefs); }, [prefs]);

  useEffect(() => {
    setLoading(true);
    api.get(`/books/${slug}`).then((r) => setBook(r.data))
      .catch(() => setBook(null)).finally(() => setLoading(false));
  }, [slug]);

  const chapters = useMemo(() => (book?.chapters || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0)), [book]);
  const currentCid = params.get("c");
  const currentIndex = useMemo(() => {
    if (!chapters.length) return 0;
    if (currentCid) {
      const i = chapters.findIndex((c) => c.id === currentCid);
      return i >= 0 ? i : 0;
    }
    return 0;
  }, [chapters, currentCid]);
  const current = chapters[currentIndex];
  const isPreview = currentIndex === 0;
  const isAuthed = !!user && typeof user === "object";

  // Sync local remaining from auth context whenever user balance updates externally
  useEffect(() => {
    if (isAuthed) setRemaining(Number(user.reading_seconds_balance || 0));
  }, [isAuthed, user]);

  // Reader access gate: chapter > 0 requires login + balance > 0
  const accessLocked = !isPreview && (!isAuthed || (remaining <= 0 && depleted));

  const goTo = useCallback((i) => {
    if (i < 0 || i >= chapters.length) return;
    const c = chapters[i];
    const next = new URLSearchParams(params);
    next.set("c", c.id);
    setParams(next, { replace: false });
    setDepleted(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [chapters, params, setParams]);

  const prev = useCallback(() => goTo(currentIndex - 1), [goTo, currentIndex]);
  const next = useCallback(() => goTo(currentIndex + 1), [goTo, currentIndex]);

  // Keyboard navigation
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === "ArrowLeft") prev();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [prev, next]);

  // Activity / visibility tracking for heartbeat semantics
  useEffect(() => {
    const onActivity = () => { idleSinceRef.current = Date.now(); };
    const onVisibility = () => {
      visibleRef.current = document.visibilityState !== "hidden";
      if (visibleRef.current) idleSinceRef.current = Date.now();
    };
    const events = ["mousemove", "keydown", "scroll", "touchstart", "click", "wheel"];
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      events.forEach((e) => window.removeEventListener(e, onActivity));
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  // Start a reading session whenever we enter a chargeable chapter while authed.
  useEffect(() => {
    let cancelled = false;
    const startSession = async () => {
      if (!book || !current) return;
      if (isPreview || !isAuthed) { setSessionId(null); return; }
      try {
        const { data } = await userApi.post("/reader/session/start", {
          book_slug: book.slug,
          chapter_id: current.id,
        });
        if (cancelled) return;
        setSessionId(data.session_id);
        setRemaining(Number(data.remaining_seconds || 0));
        setDepleted(Number(data.remaining_seconds || 0) <= 0 && !data.is_preview);
      } catch (err) {
        if (cancelled) return;
        // 402 Payment Required = no balance for this chapter
        if (err.response?.status === 402) setDepleted(true);
        setSessionId(null);
      }
    };
    startSession();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [book?.slug, current?.id, isPreview, isAuthed]);

  // End session on unmount / chapter change
  useEffect(() => {
    return () => {
      const sid = sessionId;
      if (sid) {
        userApi.post("/reader/session/end", { session_id: sid }).catch(() => {});
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Heartbeat ticker — only when we have an active session (chargeable chapter, authed)
  useEffect(() => {
    if (!sessionId || !current) return;
    const tick = async () => {
      const idle = Date.now() - idleSinceRef.current > IDLE_MS;
      const visible = visibleRef.current;
      try {
        const { data } = await userApi.post("/reader/heartbeat", {
          session_id: sessionId,
          visible,
          idle,
          chapter_id: current.id,
        });
        const newRemaining = Number(data.remaining_seconds || 0);
        setRemaining(newRemaining);
        setUserBalance(newRemaining);
        if (data.status === "depleted") setDepleted(true);
      } catch {
        // ignore transient heartbeat errors
      }
    };
    const id = setInterval(tick, HEARTBEAT_MS);
    return () => clearInterval(id);
  }, [sessionId, current, setUserBalance]);

  // Pause/blur the reader when tab hidden (visual only, deduction already paused)
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const onVis = () => setHidden(document.visibilityState === "hidden");
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  // After depletion, refresh user wallet (in case admin tops up while reader is open)
  useEffect(() => {
    if (!depleted || !isAuthed) return;
    const id = setInterval(() => { refreshUser().then((u) => {
      const bal = Number(u?.reading_seconds_balance || 0);
      if (bal > 0) { setRemaining(bal); setDepleted(false); }
    }); }, 15_000);
    return () => clearInterval(id);
  }, [depleted, isAuthed, refreshUser]);

  // Swipe
  const [touchStart, setTouchStart] = useState(null);
  const onTouchStart = (e) => setTouchStart(e.touches[0].clientX);
  const onTouchEnd = (e) => {
    if (touchStart == null) return;
    const dx = e.changedTouches[0].clientX - touchStart;
    if (dx > 80) prev();
    else if (dx < -80) next();
    setTouchStart(null);
  };

  useEffect(() => { document.title = book ? `${book.title} — Reader · The Earnalism` : "Reader · The Earnalism"; }, [book]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-[#FDFCF8] text-charcoal-soft">Loading…</div>;
  }
  if (!book) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFCF8] text-center px-6">
        <div>
          <h1 className="font-serif-light text-3xl text-burgundy mb-4">Book not found</h1>
          <Link to="/library" className="btn-secondary">Back to Library</Link>
        </div>
      </div>
    );
  }
  if (!chapters.length) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFCF8] text-center px-6">
        <div className="max-w-md">
          <h1 className="font-serif-light text-3xl text-burgundy mb-3">This book is being prepared.</h1>
          <p className="text-charcoal-soft mb-6 font-light leading-relaxed">Chapters will appear here as soon as they are added. Return soon.</p>
          <Link to={`/book/${book.slug}`} className="btn-secondary">Back to book</Link>
        </div>
      </div>
    );
  }

  const theme = prefs.theme;
  const themeCls = theme === "dark" ? "bg-[#1a1513] text-[#e5dfd5]" : theme === "sepia" ? "bg-[#f5ecd9] text-[#3b2f23]" : "bg-[#fdfcf8] text-[#2c2420]";
  const headingCls = theme === "dark" ? "text-[#e8c78d]" : theme === "sepia" ? "text-[#6b3a1f]" : "text-burgundy";
  const ruleCls = theme === "dark" ? "bg-[#e8c78d]/50" : "bg-[var(--brand-gold)]/70";
  const barCls = theme === "dark" ? "bg-[#14100e]/95 border-[#322923]" : theme === "sepia" ? "bg-[#f5ecd9]/95 border-[#d9cba6]" : "bg-[#fdfcf8]/95 border-[var(--brand-border)]";
  const progress = Math.round(((currentIndex + 1) / chapters.length) * 100);

  return (
    <div
      className={`min-h-screen ${themeCls} transition-colors duration-300 ${hidden ? "blur-sm" : ""}`}
      style={{ userSelect: "none", WebkitUserSelect: "none" }}
      onContextMenu={(e) => e.preventDefault()}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
      data-testid="reader-page"
    >
      {/* Top bar */}
      <header className={`sticky top-0 z-30 ${barCls} backdrop-blur-md border-b`} data-testid="reader-topbar">
        <div className="max-w-5xl mx-auto px-4 sm:px-8 h-14 sm:h-16 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <Link to={`/book/${book.slug}`} aria-label="Back to book" className="p-2 -ml-2 hover:opacity-70 transition-opacity" data-testid="reader-back">
              <ArrowLeft size={18} strokeWidth={1.5} />
            </Link>
            <button onClick={() => setDrawerOpen(true)} className="p-2 hover:opacity-70 transition-opacity" aria-label="Open chapters" data-testid="reader-drawer-open">
              <Menu size={18} strokeWidth={1.5} />
            </button>
            <div className="min-w-0 ml-2">
              <div className="font-serif-display italic text-[0.88rem] sm:text-[0.95rem] truncate opacity-80 leading-none">{book.title}</div>
              <div className="text-[0.65rem] tracking-[0.22em] uppercase opacity-50 leading-none mt-1 truncate">Ch {currentIndex + 1} / {chapters.length}{isPreview ? " · Free preview" : ""}</div>
            </div>
          </div>

          <div className="flex items-center gap-1 sm:gap-2" data-testid="reader-controls">
            {/* Reading-time pill */}
            {isAuthed && !isPreview && (
              <div className="hidden sm:flex items-center gap-1.5 mr-2 px-2.5 py-1 rounded-full border border-current/15" data-testid="reader-time-pill">
                <Clock size={12} strokeWidth={1.5} />
                <span className="font-serif-display text-[0.85rem]">{formatMinutes(remaining)}</span>
              </div>
            )}
            <button onClick={() => setPrefs((p) => ({ ...p, fontSize: FONT_SIZES[Math.max(0, FONT_SIZES.indexOf(p.fontSize) - 1)] }))} className="p-2 hover:opacity-70" aria-label="Smaller text" data-testid="reader-font-smaller">
              <Type size={14} strokeWidth={1.5} />
            </button>
            <button onClick={() => setPrefs((p) => ({ ...p, fontSize: FONT_SIZES[Math.min(FONT_SIZES.length - 1, FONT_SIZES.indexOf(p.fontSize) + 1)] }))} className="p-2 hover:opacity-70" aria-label="Larger text" data-testid="reader-font-larger">
              <Type size={18} strokeWidth={1.5} />
            </button>
            <div className="mx-1 w-px h-5 bg-current opacity-15" />
            {THEMES.map((t) => (
              <button
                key={t}
                onClick={() => setPrefs((p) => ({ ...p, theme: t }))}
                aria-label={`${t} theme`}
                data-testid={`reader-theme-${t}`}
                className={`p-2 hover:opacity-100 transition-opacity ${prefs.theme === t ? "opacity-100" : "opacity-40"}`}
              >
                {t === "dark" ? <Moon size={14} strokeWidth={1.5} /> : t === "sepia" ? <span className="text-[0.72rem] font-serif-display italic">Aa</span> : <Sun size={14} strokeWidth={1.5} />}
              </button>
            ))}
          </div>
        </div>
        {/* Mobile time pill row */}
        {isAuthed && !isPreview && (
          <div className="sm:hidden px-4 pb-2 flex items-center justify-end" data-testid="reader-time-pill-mobile">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-current/15">
              <Clock size={12} strokeWidth={1.5} />
              <span className="font-serif-display text-[0.85rem]">{formatMinutes(remaining)}</span>
            </div>
          </div>
        )}
        {/* Progress bar */}
        <div className="h-[2px] w-full bg-current/5">
          <div className={`h-full ${ruleCls}`} style={{ width: `${progress}%` }} data-testid="reader-progress" />
        </div>
      </header>

      {/* Content column */}
      <main className="max-w-[65ch] mx-auto px-6 sm:px-10 py-14 sm:py-20 relative" data-testid="reader-content">
        <div className="italic-eyebrow opacity-80">{isPreview ? "Free preview · Chapter 1" : `Chapter ${currentIndex + 1}`}</div>
        <h1 className={`font-serif-light ${headingCls} text-3xl sm:text-[2.5rem] leading-[1.1] mt-3 tracking-tight`}>{current.title}</h1>
        <div className={`h-px w-10 ${ruleCls} mt-6 mb-10`} />
        <article
          className={`font-serif-display leading-[1.9] ${accessLocked ? "blur-md select-none" : ""}`}
          style={{ fontSize: `${prefs.fontSize}px` }}
          data-testid="reader-article"
          aria-hidden={accessLocked ? "true" : undefined}
        >
          {(current.content || "").split("\n\n").filter(Boolean).map((para, i) => (
            <p key={`${current.id}-p-${i}`} className={i === 0 ? "" : "mt-6"}>{para}</p>
          ))}
          {!(current.content || "").trim() && (
            <p className="italic opacity-60">This chapter has no content yet.</p>
          )}
        </article>

        {/* Chapter nav (bottom) */}
        {!accessLocked && (
          <nav className="mt-16 flex items-center justify-between gap-4 pt-8 border-t border-current/10">
            <button onClick={prev} disabled={currentIndex === 0} className="inline-flex items-center gap-2 text-[0.72rem] tracking-[0.22em] uppercase disabled:opacity-30 hover:opacity-70" data-testid="reader-prev">
              <ChevronLeft size={14} /> Previous
            </button>
            <span className="text-[0.72rem] tracking-[0.22em] uppercase opacity-50">{currentIndex + 1} / {chapters.length}</span>
            <button onClick={next} disabled={currentIndex === chapters.length - 1} className="inline-flex items-center gap-2 text-[0.72rem] tracking-[0.22em] uppercase disabled:opacity-30 hover:opacity-70" data-testid="reader-next">
              Next <ChevronRight size={14} />
            </button>
          </nav>
        )}
      </main>

      {/* Locked / Depleted overlay */}
      {accessLocked && (
        <div className="fixed inset-0 z-40 flex items-center justify-center px-6 pointer-events-auto" data-testid="reader-locked-overlay">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
          <div className={`relative w-full max-w-md ${themeCls} border border-current/15 rounded-sm p-8 sm:p-10 shadow-2xl`}>
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <Lock size={13} strokeWidth={1.5} /> {isAuthed ? "Reading time ended" : "Sign in to read on"}
            </div>
            <h2 className={`font-serif-light text-3xl sm:text-[2.2rem] ${headingCls} mt-3 leading-tight`}>
              {isAuthed
                ? <>Your reading time has <span className="italic-accent">ended.</span></>
                : <>Open an account to continue <span className="italic-accent">reading.</span></>}
            </h2>
            <div className={`h-px w-10 ${ruleCls} mt-5 mb-6`} />
            <p className="opacity-80 font-light leading-relaxed text-[0.95rem]">
              {isAuthed
                ? "Top up to continue this chapter. Your place in the book is saved."
                : "The first chapter is open for everyone. From the second chapter on, sign in and add reading time to keep going."}
            </p>
            <div className="mt-7 flex flex-col sm:flex-row gap-3">
              {isAuthed ? (
                <button onClick={() => navigate("/pricing")} className="btn-primary w-full sm:w-auto" data-testid="overlay-buy-time">Buy reading time</button>
              ) : (
                <button onClick={() => navigate(`/login?next=/reader/${book.slug}${currentCid ? `?c=${currentCid}` : ""}`)} className="btn-primary w-full sm:w-auto" data-testid="overlay-signin">Sign In</button>
              )}
              <button onClick={() => navigate("/library")} className="btn-secondary w-full sm:w-auto" data-testid="overlay-library">Return to Library</button>
            </div>
            {isPreview ? null : (
              <button onClick={() => goTo(0)} className="mt-5 text-[0.72rem] tracking-[0.22em] uppercase opacity-60 hover:opacity-100" data-testid="overlay-read-preview">
                ← Read free preview chapter
              </button>
            )}
          </div>
        </div>
      )}

      {/* Watermark — show user email when authed, else "guest preview" */}
      <div className="fixed bottom-3 right-4 text-[0.65rem] tracking-[0.22em] uppercase opacity-30 pointer-events-none select-none" data-testid="reader-watermark">
        {isAuthed ? `Reader copy · ${user.email}` : "Reader copy · guest preview"}
      </div>

      {/* Chapter drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40" data-testid="reader-drawer" onClick={() => setDrawerOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <aside
            className={`relative h-full w-[86%] max-w-sm ${themeCls} border-r border-current/10 overflow-y-auto`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-5 border-b border-current/10">
              <div>
                <div className="italic-eyebrow opacity-80">Table of Contents</div>
                <div className="font-serif-display italic text-base opacity-80 mt-1">{book.title}</div>
              </div>
              <button onClick={() => setDrawerOpen(false)} aria-label="Close" className="p-2" data-testid="reader-drawer-close"><X size={18} strokeWidth={1.5} /></button>
            </div>
            <ol className="p-5 space-y-1">
              {chapters.map((c, i) => (
                <li key={c.id}>
                  <button
                    onClick={() => { goTo(i); setDrawerOpen(false); }}
                    data-testid={`reader-toc-${c.id}`}
                    className={`w-full text-left flex items-baseline gap-4 py-3 px-2 rounded-md hover:bg-current/5 transition-colors ${i === currentIndex ? "" : "opacity-70"}`}
                  >
                    <span className="italic-accent shrink-0 w-10 opacity-70">{String(i + 1).padStart(2, "0")}</span>
                    <span className="font-serif-display text-[1.05rem] leading-snug flex-1">{c.title}</span>
                    {i === 0 ? (
                      <span className="text-[0.6rem] tracking-[0.22em] uppercase opacity-50">Free</span>
                    ) : (!isAuthed || (remaining <= 0 && depleted)) ? (
                      <Lock size={11} strokeWidth={1.5} className="opacity-40" />
                    ) : null}
                  </button>
                </li>
              ))}
            </ol>
          </aside>
        </div>
      )}
    </div>
  );
}
