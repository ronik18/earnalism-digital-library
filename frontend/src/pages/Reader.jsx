import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  Bookmark,
  BookmarkCheck,
  ChevronLeft,
  ChevronRight,
  Clock,
  List,
  Loader2,
  Settings,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import axios from "axios";
import { api, userApi, formatMinutes, API, TOKEN_KEY, USER_TOKEN_KEY } from "../lib/api";
import { useAuth } from "../context/AuthContext";

// ---------- Theme + size constants ----------
const THEMES = {
  beige: { canvas: "#FAF7F0", surface: "#F5F0E8", text: "#1C0A0E", accent: "#6B1020", border: "#E8DDD8", label: "Beige" },
  dark:  { canvas: "#141010", surface: "#1E1518", text: "#EDE0D8", accent: "#D4A843", border: "#2E1F22", label: "Dark" },
  sepia: { canvas: "#EFE4C8", surface: "#E5D8B5", text: "#3B2010", accent: "#8B1A2A", border: "#D5C8A5", label: "Sepia" },
};
const FONT_SIZES = [
  { label: "XS", size: "15px" },
  { label: "S", size: "17px" },
  { label: "M", size: "19px" },
  { label: "L", size: "21px" },
];
const LOW_BALANCE_THRESHOLD = 300;
const HEARTBEAT_MS = 30_000;
const IDLE_MS = 60_000;
const PREFS_KEY = "earnalism_reader_prefs";
const DEFAULT_PREFS = { theme: "beige", fontSizeIdx: 1 };

// ---------- Pure helpers ----------
function loadPrefs() {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
}
function savePrefs(p) {
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(p)); } catch { /* noop */ }
}

function wrapWordsInSpans(html) {
  if (typeof document === "undefined") return { html: html || "", totalWords: 0 };
  const div = document.createElement("div");
  div.innerHTML = html || "";
  let wordIndex = 0;
  const TEXT = 3;
  const ELEMENT = 1;
  function processNode(node) {
    if (node.nodeType === TEXT) {
      const text = node.textContent;
      if (!text || !text.trim()) return;
      const wrapper = document.createElement("span");
      let lastIndex = 0;
      let html = "";
      const re = /\S+/g;
      let m;
      while ((m = re.exec(text)) !== null) {
        html += text.slice(lastIndex, m.index);
        html += `<span class="tts-word" data-word="${wordIndex}">${m[0]}</span>`;
        wordIndex += 1;
        lastIndex = m.index + m[0].length;
      }
      html += text.slice(lastIndex);
      wrapper.innerHTML = html;
      const parent = node.parentNode;
      while (wrapper.firstChild) parent.insertBefore(wrapper.firstChild, node);
      parent.removeChild(node);
    } else if (node.nodeType === ELEMENT) {
      const tag = node.tagName?.toUpperCase();
      if (tag === "SCRIPT" || tag === "STYLE") return;
      Array.from(node.childNodes).forEach(processNode);
    }
  }
  Array.from(div.childNodes).forEach(processNode);
  return { html: div.innerHTML, totalWords: wordIndex };
}

function formatWalletTime(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0));
  if (s >= 3600) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${m}m`;
  }
  if (s >= 60) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}m ${sec}s`;
  }
  return `${s}s`;
}

// Convert plain-text chapter (split on \n\n) into HTML so .reader-content styles apply.
function renderChapterToHtml(content) {
  if (!content) return "";
  if (/<\w+/.test(content)) return content; // looks like HTML — pass through
  return content
    .split(/\n{2,}/)
    .filter(Boolean)
    .map((p) => `<p>${p.trim().replace(/\n/g, "<br/>")}</p>`)
    .join("");
}

export default function Reader() {
  const { slug } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, refreshUser, setUserBalance } = useAuth();

  // ---------- Content state ----------
  const [book, setBook] = useState(null);
  const [chapterPayload, setChapterPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [chapterLoading, setChapterLoading] = useState(false);
  const [error, setError] = useState(null);

  // ---------- Preferences ----------
  const [prefs, setPrefs] = useState(loadPrefs);
  const [showSettings, setShowSettings] = useState(false);
  const [showTOC, setShowTOC] = useState(false);
  const [toolbarVisible, setToolbarVisible] = useState(true);
  const [bookmarked, setBookmarked] = useState(false);
  useEffect(() => { savePrefs(prefs); }, [prefs]);

  // ---------- TTS ----------
  const [ttsActive, setTtsActive] = useState(false);
  const [ttsPaused, setTtsPaused] = useState(false);
  const [ttsWordIndex, setTtsWordIndex] = useState(-1);
  const [ttsSpeed, setTtsSpeed] = useState(1);
  const [processedHtml, setProcessedHtml] = useState("");
  const [totalWords, setTotalWords] = useState(0);

  // ---------- Reading progress + protection ----------
  const [readProgress, setReadProgress] = useState(0);
  const [contentBlurred, setContentBlurred] = useState(false);

  // ---------- Wallet + sessions ----------
  const [walletSeconds, setWalletSeconds] = useState(0);
  const [showLowBalanceWarning, setShowLowBalanceWarning] = useState(false);
  const [showTopUpModal, setShowTopUpModal] = useState(false);
  const [savedScrollPosition, setSavedScrollPosition] = useState(0);
  const [topUpPacks, setTopUpPacks] = useState([]);
  const [selectedPack, setSelectedPack] = useState(1);
  const [topUpProcessing, setTopUpProcessing] = useState(false);
  const [showTopUpSuccess, setShowTopUpSuccess] = useState(false);
  const [topUpSuccessMinutes, setTopUpSuccessMinutes] = useState(0);

  // ---------- Session ----------
  const [sessionId, setSessionId] = useState(null);
  const [clientSessionId] = useState(() => {
    if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
    return Math.random().toString(36).slice(2);
  });

  // ---------- Refs ----------
  const contentRef = useRef(null);
  const utteranceRef = useRef(null);
  const synthRef = useRef(typeof window !== "undefined" ? window.speechSynthesis : null);
  const lastScrollY = useRef(0);
  const wordsRef = useRef([]);
  const idleSinceRef = useRef(Date.now());
  const visibleRef = useRef(typeof document !== "undefined" ? document.visibilityState !== "hidden" : true);
  const heartbeatIntervalRef = useRef(null);
  const scrollContainerRef = useRef(null);

  // ---------- Initial mount: content protection listeners ----------
  useEffect(() => {
    const onContextMenu = (e) => e.preventDefault();
    const onKeyDown = (e) => {
      const key = e.key;
      const block =
        ((e.ctrlKey || e.metaKey) && ["s", "u", "a", "p", "S", "U", "A", "P"].includes(key)) ||
        key === "F12" || key === "PrintScreen";
      if (block) { e.preventDefault(); e.stopPropagation(); }
    };
    const onCopy = (e) => {
      e.preventDefault();
      e.clipboardData?.setData("text/plain", "Content is protected © Earnalism");
    };
    document.addEventListener("contextmenu", onContextMenu);
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("copy", onCopy);

    const devtoolsInterval = setInterval(() => {
      const dx = window.outerWidth - window.innerWidth;
      const dy = window.outerHeight - window.innerHeight;
      setContentBlurred(dx > 160 || dy > 160);
    }, 1000);

    const onVisibility = () => {
      visibleRef.current = document.visibilityState !== "hidden";
      setContentBlurred(document.visibilityState === "hidden");
      if (visibleRef.current) idleSinceRef.current = Date.now();
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      document.removeEventListener("contextmenu", onContextMenu);
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("visibilitychange", onVisibility);
      clearInterval(devtoolsInterval);
    };
  }, []);

  // ---------- Activity tracking (for heartbeat idle/visible) ----------
  useEffect(() => {
    const onActivity = () => { idleSinceRef.current = Date.now(); };
    const events = ["mousemove", "keydown", "scroll", "touchstart", "click", "wheel"];
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    return () => events.forEach((e) => window.removeEventListener(e, onActivity));
  }, []);

  // ---------- Load book + packs ----------
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      api.get(`/books/${slug}`).then((r) => r.data).catch(() => null),
      axios.get(`${API}/payments/packs`).then((r) => r.data).catch(() => null),
    ]).then(([bookData, packsData]) => {
      if (cancelled) return;
      if (!bookData) {
        setError("Book not found");
        setLoading(false);
        return;
      }
      setBook(bookData);
      if (packsData?.packs) {
        const packs = packsData.packs.map((p) => ({
          _id: p.id,
          minutes: p.minutes,
          price: p.price_inr ?? Math.round((p.amount_paise || 0) / 100),
          label: p.label,
          note: p.note,
          amount_paise: p.amount_paise,
        }));
        setTopUpPacks(packs);
        setSelectedPack(Math.min(1, Math.max(0, packs.length - 1)));
      }
      setLoading(false);
    }).catch(() => {
      if (!cancelled) {
        setError("Could not load this book");
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, [slug]);

  // ---------- Sort + select chapter ----------
  const chapters = useMemo(
    () => (book?.chapters || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0)),
    [book]
  );
  const currentCid = searchParams.get("c");
  const currentIdx = useMemo(() => {
    if (!chapters.length) return 0;
    if (currentCid) {
      const i = chapters.findIndex((c) => c.id === currentCid);
      return i >= 0 ? i : 0;
    }
    return 0;
  }, [chapters, currentCid]);
  const chapter = chapters[currentIdx] || null;
  const isPreview = currentIdx === 0;
  const isAuthed = !!user && typeof user === "object";

  // ---------- Sync wallet from auth context ----------
  useEffect(() => {
    if (isAuthed) {
      const bal = Number(user.reading_seconds_balance || 0);
      setWalletSeconds(bal);
      if (bal > 0 && bal <= LOW_BALANCE_THRESHOLD && !isPreview) setShowLowBalanceWarning(true);
    }
  }, [isAuthed, user, isPreview]);

  // ---------- Fetch gated chapter content ----------
  useEffect(() => {
    if (!book || !chapter) { setChapterPayload(null); setProcessedHtml(""); setTotalWords(0); return; }
    let cancelled = false;
    const adminToken = localStorage.getItem(TOKEN_KEY);
    const userToken = localStorage.getItem(USER_TOKEN_KEY);
    const headers = {};
    if (adminToken) headers.Authorization = `Bearer ${adminToken}`;
    else if (userToken) headers.Authorization = `Bearer ${userToken}`;
    setChapterLoading(true);
    axios.get(`${API}/reader/chapter/${book.slug}/${chapter.id}`, { headers })
      .then((r) => {
        if (cancelled) return;
        setChapterPayload(r.data);
        const html = renderChapterToHtml(r.data?.chapter?.content || "");
        const wrapped = wrapWordsInSpans(html);
        setProcessedHtml(wrapped.html);
        setTotalWords(wrapped.totalWords);
      })
      .catch(() => {
        if (cancelled) return;
        setChapterPayload({
          locked: true,
          reason: "ERROR",
          message: "Could not load this chapter. Please try again.",
          chapter: { id: chapter.id, title: chapter.title, order: chapter.order || 0 },
        });
        setProcessedHtml("");
        setTotalWords(0);
      })
      .finally(() => { if (!cancelled) setChapterLoading(false); });
    return () => { cancelled = true; };
  }, [book, chapter]);

  // ---------- Cache word spans after html paint ----------
  useEffect(() => {
    wordsRef.current = Array.from(contentRef.current?.querySelectorAll(".tts-word") || []);
  }, [processedHtml]);

  const serverLocked = chapterPayload?.locked === true;
  const lockedReason = chapterPayload?.reason || null;
  const accessLocked = serverLocked;

  // ---------- Start session when entering chargeable chapter while authed ----------
  useEffect(() => {
    let cancelled = false;
    const startSession = async () => {
      if (!book || !chapter) return;
      if (isPreview || !isAuthed) { setSessionId(null); return; }
      try {
        const { data } = await userApi.post("/reader/session/start", {
          book_slug: book.slug,
          chapter_id: chapter.id,
        });
        if (cancelled) return;
        setSessionId(data.session_id);
        setWalletSeconds(Number(data.remaining_seconds || 0));
      } catch (err) {
        if (cancelled) return;
        if (err.response?.status === 402) {
          setShowTopUpModal(true);
          setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0);
        }
        setSessionId(null);
      }
    };
    startSession();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [book?.slug, chapter?.id, isPreview, isAuthed]);

  // ---------- End session on unmount/chapter change ----------
  useEffect(() => {
    return () => {
      const sid = sessionId;
      if (sid) userApi.post("/reader/session/end", { session_id: sid }).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // ---------- Heartbeat ticker ----------
  useEffect(() => {
    if (!sessionId || !chapter) return;
    const tick = async () => {
      const idle = Date.now() - idleSinceRef.current > IDLE_MS;
      const visible = visibleRef.current;
      try {
        const { data } = await userApi.post("/reader/heartbeat", {
          session_id: sessionId,
          visible,
          idle,
          chapter_id: chapter.id,
        });
        const remaining = Number(data.remaining_seconds || 0);
        setWalletSeconds(remaining);
        setUserBalance(remaining);
        if (data.status === "depleted" || remaining <= 0) {
          setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0);
          setShowTopUpModal(true);
          setShowLowBalanceWarning(false);
          if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
            heartbeatIntervalRef.current = null;
          }
        } else if (remaining <= LOW_BALANCE_THRESHOLD) {
          setShowLowBalanceWarning(true);
        }
      } catch (err) {
        if (err.response?.status === 404) {
          if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        }
      }
    };
    heartbeatIntervalRef.current = setInterval(tick, HEARTBEAT_MS);
    return () => {
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
    };
  }, [sessionId, chapter, setUserBalance]);

  // ---------- Scroll progress + auto-hide toolbar ----------
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const onScroll = () => {
      const max = el.scrollHeight - el.clientHeight;
      const pct = max > 0 ? (el.scrollTop / max) * 100 : 0;
      setReadProgress(Math.min(100, Math.round(pct)));
      if (el.scrollTop > lastScrollY.current + 10) setToolbarVisible(false);
      else if (el.scrollTop < lastScrollY.current - 5) setToolbarVisible(true);
      lastScrollY.current = el.scrollTop;
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [loading]);

  // ---------- TTS ----------
  const buildUtterance = useCallback(() => {
    if (!synthRef.current) return null;
    const plainText = contentRef.current?.innerText || "";
    if (!plainText.trim()) return null;
    const utter = new SpeechSynthesisUtterance(plainText);
    utter.rate = ttsSpeed;
    utter.pitch = 1;
    utter.lang = "en-US";
    const voices = synthRef.current.getVoices();
    const preferred =
      voices.find((v) => /Samantha|Karen|Moira|Daniel/i.test(v.name)) ||
      voices.find((v) => v.lang === "en-US") ||
      voices[0];
    if (preferred) utter.voice = preferred;
    let count = 0;
    utter.onboundary = (e) => {
      if (e.name !== "word") return;
      wordsRef.current.forEach((w) => w.classList.remove("active"));
      const cur = wordsRef.current[count];
      if (cur) {
        cur.classList.add("active");
        cur.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      setTtsWordIndex(count);
      count += 1;
    };
    const reset = () => {
      setTtsActive(false);
      setTtsPaused(false);
      setTtsWordIndex(-1);
      wordsRef.current.forEach((w) => w.classList.remove("active"));
    };
    utter.onend = reset;
    utter.onerror = reset;
    return utter;
  }, [ttsSpeed]);

  const startTTS = useCallback(() => {
    if (!synthRef.current) return;
    synthRef.current.cancel();
    const utter = buildUtterance();
    if (!utter) return;
    utteranceRef.current = utter;
    synthRef.current.speak(utter);
    setTtsActive(true);
    setTtsPaused(false);
  }, [buildUtterance]);

  const pauseTTS = useCallback(() => {
    if (!synthRef.current) return;
    synthRef.current.pause();
    setTtsPaused(true);
  }, []);
  const resumeTTS = useCallback(() => {
    if (!synthRef.current) return;
    synthRef.current.resume();
    setTtsPaused(false);
  }, []);
  const stopTTS = useCallback(() => {
    if (!synthRef.current) return;
    synthRef.current.cancel();
    setTtsActive(false);
    setTtsPaused(false);
    setTtsWordIndex(-1);
    wordsRef.current.forEach((w) => w.classList.remove("active"));
  }, []);

  const handleVoiceToggle = () => {
    if (!ttsActive) startTTS();
    else if (ttsPaused) resumeTTS();
    else pauseTTS();
  };

  // Stop TTS on chapter / unmount
  useEffect(() => stopTTS, [chapter?.id, stopTTS]);

  // ---------- Navigation ----------
  const prevChapter = chapters[currentIdx - 1] || null;
  const nextChapter = chapters[currentIdx + 1] || null;
  const goToChapter = (id) => {
    stopTTS();
    const next = new URLSearchParams(searchParams);
    next.set("c", id);
    setSearchParams(next, { replace: false });
    if (scrollContainerRef.current) scrollContainerRef.current.scrollTop = 0;
  };

  // ---------- Bookmark (best-effort; endpoint may 404) ----------
  const toggleBookmark = async () => {
    setBookmarked((b) => !b);
    if (!book || !chapter) return;
    try {
      await userApi.post("/bookmarks", { book_slug: book.slug, chapter_id: chapter.id });
    } catch { /* endpoint optional */ }
  };

  // ---------- Top-up flow (Razorpay) ----------
  const handleTopUp = async (pack) => {
    if (!pack) return;
    setTopUpProcessing(true);
    try {
      const cfgRes = await axios.get(`${API}/payments/config`).catch(() => null);
      const keyId = cfgRes?.data?.key_id || cfgRes?.data?.razorpay_key_id;
      const { data: order } = await userApi.post("/payments/create-topup", { pack_id: pack._id });
      const RZP = window.Razorpay;
      if (!RZP) {
        // Fallback simulation route for dev/test mode without razorpay-js
        const { data: sim } = await userApi.post("/payments/simulate-topup", { pack_id: pack._id });
        const newBal = Number(sim?.user?.reading_seconds_balance || 0);
        setWalletSeconds(newBal);
        setUserBalance(newBal);
        setShowTopUpModal(false);
        setTopUpProcessing(false);
        setShowTopUpSuccess(true);
        setTopUpSuccessMinutes(pack.minutes);
        setShowLowBalanceWarning(false);
        setTimeout(() => {
          setShowTopUpSuccess(false);
          if (scrollContainerRef.current) scrollContainerRef.current.scrollTop = savedScrollPosition;
        }, 1500);
        await refreshUser();
        return;
      }
      const rzp = new RZP({
        key: keyId,
        order_id: order.razorpay_order_id || order.order_id,
        amount: order.amount_paise || pack.amount_paise,
        currency: "INR",
        name: "The Earnalism",
        description: pack.label || `${pack.minutes} min`,
        handler: async (resp) => {
          try {
            const { data: verified } = await userApi.post("/payments/verify", {
              razorpay_order_id: resp.razorpay_order_id,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature: resp.razorpay_signature,
            });
            const newBal = Number(verified?.user?.reading_seconds_balance || 0);
            setWalletSeconds(newBal);
            setUserBalance(newBal);
            setShowTopUpModal(false);
            setShowTopUpSuccess(true);
            setTopUpSuccessMinutes(pack.minutes);
            setShowLowBalanceWarning(false);
            setTimeout(() => {
              setShowTopUpSuccess(false);
              if (scrollContainerRef.current) scrollContainerRef.current.scrollTop = savedScrollPosition;
            }, 1500);
            await refreshUser();
          } finally {
            setTopUpProcessing(false);
          }
        },
        modal: { ondismiss: () => setTopUpProcessing(false) },
      });
      rzp.open();
    } catch (err) {
      setTopUpProcessing(false);
    }
  };

  // ---------- Render ----------
  const colors = THEMES[prefs.theme] || THEMES.beige;
  const fontSize = FONT_SIZES[prefs.fontSizeIdx]?.size || "17px";

  if (loading) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center"
        style={{ background: THEMES.beige.canvas }}
        data-testid="reader-loading"
      >
        <Loader2 size={32} className="animate-spin" color="#6B1020" />
        <div
          className="mt-4"
          style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 17, color: "#7A5C62" }}
        >
          Opening chapter…
        </div>
      </div>
    );
  }
  if (error || !book) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center gap-4 px-6 text-center"
        style={{ background: THEMES.beige.canvas }}
      >
        <div
          style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 18, color: "#6B1020" }}
        >
          {error || "Book not found"}
        </div>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="px-6 py-2 rounded-full"
          style={{
            background: "#6B1020",
            color: "#FAF7F0",
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
          }}
        >
          Back
        </button>
      </div>
    );
  }

  const lowBal = walletSeconds > 0 && walletSeconds <= LOW_BALANCE_THRESHOLD && !isPreview;
  const watermarkLabel = `${user?.email || "earnalism.com"} · ${new Date().toLocaleDateString()} · ${clientSessionId.slice(0, 8)}`;

  return (
    <div
      ref={scrollContainerRef}
      className="relative flex flex-col min-h-screen overflow-y-auto reader-scroll"
      style={{
        background: colors.canvas,
        color: colors.text,
        height: "100vh",
        transition: "background 400ms ease, color 300ms ease",
      }}
      data-testid="reader-page"
    >
      {/* Reading progress bar */}
      <div className="fixed top-0 left-0 right-0 z-50" style={{ height: 2, background: colors.border }}>
        <div style={{ width: `${readProgress}%`, height: "100%", background: "#6B1020", transition: "width 300ms" }} />
      </div>

      {/* Watermark */}
      <div className="watermark" aria-hidden="true">
        <span className="watermark-text">{watermarkLabel}</span>
      </div>

      {/* Top header */}
      <header
        className="fixed left-0 right-0 z-40"
        style={{
          top: 2,
          background: `${colors.canvas}EE`,
          backdropFilter: "blur(12px)",
          borderBottom: `1px solid ${colors.border}`,
          transform: toolbarVisible ? "translateY(0)" : "translateY(-100%)",
          transition: "transform 300ms ease",
        }}
      >
        <div className="flex items-center justify-between px-4 py-3">
          <button
            type="button"
            onClick={() => navigate(`/book/${book.slug}`)}
            className="flex items-center gap-2"
            style={{ color: colors.accent, fontFamily: "Inter, sans-serif", fontSize: 13 }}
            data-testid="reader-back"
          >
            <ChevronLeft size={16} />
            <span className="hidden sm:inline truncate max-w-[200px]">{book.title}</span>
          </button>

          <div className="flex flex-col items-center text-center min-w-0 px-2">
            <div
              className="truncate"
              style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 14,
                color: colors.text,
                maxWidth: 180,
              }}
            >
              {chapter?.title || ""}
            </div>
            <div style={{ fontFamily: "Inter, sans-serif", fontSize: 11, color: "#A88A8F" }}>
              Ch. {currentIdx + 1} of {chapters.length}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isAuthed && !isPreview && (
              <span
                className={lowBal ? "wallet-low flex items-center gap-1" : "flex items-center gap-1"}
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontSize: 12,
                  color: lowBal ? "#D4A843" : "#A88A8F",
                }}
              >
                <Clock size={14} />
                {formatWalletTime(walletSeconds)}
              </span>
            )}
            <button type="button" onClick={toggleBookmark} aria-label="Bookmark">
              {bookmarked ? <BookmarkCheck size={18} color="#6B1020" /> : <Bookmark size={18} color="#A88A8F" />}
            </button>
            <button type="button" onClick={() => setShowTOC(true)} aria-label="Contents">
              <List size={18} color="#A88A8F" />
            </button>
            <button type="button" onClick={() => setShowSettings((s) => !s)} aria-label="Settings">
              <Settings size={18} color="#A88A8F" />
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 px-5 pt-20 pb-36 page-enter">
        <div className="reader-canvas mx-auto" style={{ position: "relative" }}>
          <h2
            className="text-center"
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 28,
              fontWeight: 500,
              color: colors.accent,
              letterSpacing: "-0.01em",
              lineHeight: 1.4,
              marginBottom: 24,
            }}
          >
            {chapter?.title || ""}
          </h2>
          <div className="flex items-center gap-3 mb-10 justify-center">
            <div className="flex-1" style={{ height: 1, background: colors.border }} />
            <span style={{ color: colors.accent, fontSize: 20 }}>❧</span>
            <div className="flex-1" style={{ height: 1, background: colors.border }} />
          </div>

          {accessLocked ? (
            <div
              className="text-center px-4 py-8"
              style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 17,
                color: colors.text,
              }}
            >
              <AlertCircle size={28} color={colors.accent} className="mx-auto mb-4" />
              <div style={{ fontSize: 22, fontFamily: "'Cormorant Garamond', serif", color: colors.accent, marginBottom: 8 }}>
                {lockedReason === "AUTH_REQUIRED"
                  ? "Sign in to continue"
                  : lockedReason === "BLOCKED"
                  ? "Account blocked"
                  : "Reading time ended"}
              </div>
              <p style={{ color: "#7A5C62", fontSize: 15 }}>
                {chapterPayload?.message || "Top up to continue this chapter."}
              </p>
              <div className="mt-6 flex items-center justify-center gap-3">
                {lockedReason === "AUTH_REQUIRED" ? (
                  <button
                    type="button"
                    onClick={() => navigate(`/login?next=/reader/${book.slug}${currentCid ? `?c=${currentCid}` : ""}`)}
                    className="px-5 py-2 rounded-full"
                    style={{ background: "#6B1020", color: "#FAF7F0", fontFamily: "Inter, sans-serif", fontSize: 13 }}
                  >
                    Sign in
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => { setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0); setShowTopUpModal(true); }}
                    className="px-5 py-2 rounded-full"
                    style={{ background: "#6B1020", color: "#FAF7F0", fontFamily: "Inter, sans-serif", fontSize: 13 }}
                  >
                    Top up
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => navigate("/library")}
                  className="px-5 py-2 rounded-full"
                  style={{ background: colors.surface, color: colors.accent, fontFamily: "Inter, sans-serif", fontSize: 13 }}
                >
                  Library
                </button>
              </div>
            </div>
          ) : chapterLoading ? (
            <div className="text-center py-12" style={{ color: "#7A5C62", fontFamily: "'Crimson Pro', Georgia, serif" }}>
              Loading chapter…
            </div>
          ) : (
            <div
              ref={contentRef}
              className="drop-cap reader-content"
              style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize,
                lineHeight: 1.75,
                color: colors.text,
                filter: contentBlurred ? "blur(12px)" : "none",
                transition: "filter 300ms ease",
                userSelect: "none",
                WebkitUserSelect: "none",
              }}
              dangerouslySetInnerHTML={{ __html: processedHtml }}
            />
          )}
        </div>
      </main>

      {/* Bottom toolbar */}
      <div
        className="fixed left-0 right-0 z-40"
        style={{
          bottom: 0,
          background: `${colors.canvas}F5`,
          backdropFilter: "blur(16px)",
          borderTop: `1px solid ${colors.border}`,
          transform: toolbarVisible ? "translateY(0)" : "translateY(100%)",
          transition: "transform 300ms ease",
        }}
      >
        {ttsActive && (
          <div style={{ height: 2, background: colors.border }}>
            <div
              style={{
                width: `${totalWords > 0 ? (Math.max(0, ttsWordIndex) / totalWords) * 100 : 0}%`,
                height: "100%",
                background: "#D4A843",
                transition: "width 200ms",
              }}
            />
          </div>
        )}
        <div className="flex items-center justify-between px-6 py-3 max-w-xl mx-auto">
          <button
            type="button"
            disabled={!prevChapter}
            onClick={() => prevChapter && goToChapter(prevChapter.id)}
            className="flex items-center gap-1"
            style={{
              color: colors.accent,
              fontFamily: "Inter, sans-serif",
              fontSize: 12,
              opacity: prevChapter ? 1 : 0.3,
            }}
          >
            <ChevronLeft size={16} />
            <span className="hidden sm:inline">Prev</span>
          </button>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleVoiceToggle}
              className="flex flex-col items-center gap-1"
              aria-label="Listen"
            >
              <span
                className={ttsActive && !ttsPaused ? "p-3 rounded-full animate-pulse-soft" : "p-3 rounded-full"}
                style={
                  ttsActive && !ttsPaused
                    ? {
                        background: "#6B1020",
                        color: "#FAF7F0",
                        boxShadow: "0 0 0 4px rgba(107,16,32,0.15)",
                        transition: "all 250ms ease",
                        display: "inline-flex",
                      }
                    : {
                        background: colors.surface,
                        color: colors.accent,
                        transition: "all 250ms ease",
                        display: "inline-flex",
                      }
                }
              >
                {ttsActive && !ttsPaused ? <Volume2 size={20} /> : <VolumeX size={20} />}
              </span>
              <span style={{ fontFamily: "Inter, sans-serif", fontSize: 11, color: "#A88A8F" }}>
                {!ttsActive ? "Listen" : ttsPaused ? "Resume" : "Pause"}
              </span>
            </button>
            {ttsActive && (
              <button
                type="button"
                onClick={stopTTS}
                className="px-3 py-1 rounded-full"
                style={{
                  background: colors.surface,
                  color: "#A88A8F",
                  fontFamily: "Inter, sans-serif",
                  fontSize: 11,
                }}
              >
                Stop
              </button>
            )}
          </div>

          <button
            type="button"
            disabled={!nextChapter}
            onClick={() => nextChapter && goToChapter(nextChapter.id)}
            className="flex items-center gap-1"
            style={{
              color: colors.accent,
              fontFamily: "Inter, sans-serif",
              fontSize: 12,
              opacity: nextChapter ? 1 : 0.3,
            }}
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Low-balance warning banner */}
      {showLowBalanceWarning && !showTopUpModal && walletSeconds > 0 && !isPreview && (
        <div
          className="fixed left-0 right-0 z-[45] animate-slide-up"
          style={{
            bottom: 64,
            background: "#E8C97A",
            borderTop: "1px solid #D4A843",
          }}
        >
          <div className="flex items-center justify-between px-4 py-3 max-w-xl mx-auto">
            <div className="flex items-center gap-2">
              <Clock size={16} color="#6B1020" />
              <span style={{ fontFamily: "Inter, sans-serif", fontSize: 13, color: "#6B1020" }}>
                {formatWalletTime(walletSeconds)} of reading time remaining
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => { setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0); setShowTopUpModal(true); }}
                className="px-3 py-1 rounded-full"
                style={{ background: "#6B1020", color: "#FAF7F0", fontFamily: "Inter, sans-serif", fontSize: 12 }}
              >
                Top Up
              </button>
              <button
                type="button"
                onClick={() => setShowLowBalanceWarning(false)}
                style={{ color: "#6B1020", fontFamily: "Inter, sans-serif", fontSize: 16 }}
                aria-label="Dismiss"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top-up modal */}
      {showTopUpModal && (
        <div className="fixed inset-0 z-[60] flex items-end justify-center">
          <div className="absolute inset-0 bg-black/50" style={{ backdropFilter: "blur(4px)" }} />
          <div
            className="relative rounded-t-2xl p-6 w-full max-w-lg animate-slide-up"
            style={{ background: "#FAF7F0", boxShadow: "0 -8px 40px rgba(107,16,32,0.15)" }}
          >
            <div className="text-center" style={{ fontSize: 32 }}>⏸</div>
            <div
              className="text-center mt-3"
              style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 26, color: "#6B1020" }}
            >
              Reading Paused
            </div>
            <p
              className="text-center mt-2"
              style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 16, color: "#7A5C62" }}
            >
              You've used all your reading time.
            </p>
            <p
              className="text-center mt-1 mb-5"
              style={{ fontFamily: "Inter, sans-serif", fontSize: 12, color: "#D4A843" }}
            >
              Your place is saved — top up to continue from where you left off.
            </p>

            <div className="space-y-2">
              {topUpPacks.map((pack, idx) => {
                const sel = idx === selectedPack;
                return (
                  <div
                    key={pack._id}
                    onClick={() => setSelectedPack(idx)}
                    className="rounded-xl p-4 cursor-pointer transition-all"
                    style={{
                      borderWidth: 2,
                      borderStyle: "solid",
                      borderColor: sel ? "#6B1020" : "#E8DDD8",
                      background: sel ? "rgba(107,16,32,0.06)" : "#FFFFFF",
                    }}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 17, color: "#1C0A0E" }}>
                          {pack.minutes} min
                        </div>
                        {pack.label && (
                          <div style={{ fontFamily: "Inter, sans-serif", fontSize: 11, color: "#A88A8F" }}>
                            {pack.label}
                          </div>
                        )}
                      </div>
                      <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 20, color: "#6B1020" }}>
                        ₹{pack.price}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <button
              type="button"
              disabled={topUpProcessing || !topUpPacks[selectedPack]}
              onClick={() => handleTopUp(topUpPacks[selectedPack])}
              className="w-full mt-4 rounded-xl py-3 flex items-center justify-center gap-2"
              style={{
                background: "#6B1020",
                color: "#FAF7F0",
                fontFamily: "Inter, sans-serif",
                fontSize: 15,
                fontWeight: 500,
                opacity: topUpProcessing ? 0.7 : 1,
              }}
            >
              {topUpProcessing && <Loader2 size={16} className="animate-spin" />}
              Complete Payment →
            </button>
            <button
              type="button"
              onClick={() => setShowTopUpModal(false)}
              className="w-full mt-3 text-center"
              style={{ fontFamily: "Inter, sans-serif", fontSize: 12, color: "#A88A8F" }}
            >
              I'll top up later
            </button>
          </div>
        </div>
      )}

      {/* Top-up success overlay */}
      {showTopUpSuccess && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center animate-fade-in"
          style={{ background: "rgba(250,247,240,0.96)", backdropFilter: "blur(8px)" }}
        >
          <div className="flex flex-col items-center gap-4">
            <div
              className="rounded-full flex items-center justify-center"
              style={{ width: 64, height: 64, background: "#6B1020", color: "white", fontSize: 24 }}
            >
              ✓
            </div>
            <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, color: "#6B1020" }}>
              {topUpSuccessMinutes} minutes added
            </div>
            <div style={{ fontFamily: "Inter, sans-serif", fontSize: 13, color: "#A88A8F" }}>
              Resuming your chapter…
            </div>
          </div>
        </div>
      )}

      {/* Settings panel */}
      {showSettings && (
        <div
          className="fixed z-50 rounded-2xl p-5 w-80 animate-slide-up shadow-book"
          style={{
            bottom: 80,
            left: "50%",
            transform: "translateX(-50%)",
            background: colors.surface,
            border: `1px solid ${colors.border}`,
          }}
        >
          <div className="flex justify-between items-center mb-4">
            <span style={{ fontFamily: "Inter, sans-serif", fontSize: 13, fontWeight: 500, color: colors.text }}>
              Reading Settings
            </span>
            <button type="button" onClick={() => setShowSettings(false)} aria-label="Close">
              <X size={16} color="#A88A8F" />
            </button>
          </div>

          <div className="mb-4">
            <div style={{ fontFamily: "Inter, sans-serif", fontSize: 11, color: "#A88A8F", marginBottom: 8 }}>
              Font Size
            </div>
            <div className="flex gap-2">
              {FONT_SIZES.map((f, i) => {
                const sel = prefs.fontSizeIdx === i;
                return (
                  <button
                    key={f.label}
                    type="button"
                    onClick={() => setPrefs((p) => ({ ...p, fontSizeIdx: i }))}
                    className="flex-1 py-2 rounded-lg"
                    style={{
                      background: sel ? "#6B1020" : colors.canvas,
                      color: sel ? "#FAF7F0" : colors.text,
                      border: sel ? "none" : `1px solid ${colors.border}`,
                      fontFamily: "Inter, sans-serif",
                      fontSize: 12,
                      fontWeight: 500,
                    }}
                  >
                    {f.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mb-4">
            <div style={{ fontFamily: "Inter, sans-serif", fontSize: 11, color: "#A88A8F", marginBottom: 8 }}>
              Theme
            </div>
            <div className="flex gap-2">
              {Object.entries(THEMES).map(([key, t]) => {
                const sel = prefs.theme === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setPrefs((p) => ({ ...p, theme: key }))}
                    className="flex-1 py-2 rounded-lg capitalize"
                    style={{
                      background: t.canvas,
                      color: t.text,
                      border: sel ? `2px solid #6B1020` : `1px solid ${colors.border}`,
                      fontFamily: "Inter, sans-serif",
                      fontSize: 11,
                    }}
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div style={{ fontFamily: "Inter, sans-serif", fontSize: 11, color: "#A88A8F", marginBottom: 8 }}>
              Speed: {ttsSpeed}×
            </div>
            <input
              type="range"
              min={0.7}
              max={1.8}
              step={0.1}
              value={ttsSpeed}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                setTtsSpeed(v);
                if (ttsActive) {
                  stopTTS();
                  setTimeout(startTTS, 150);
                }
              }}
              style={{ accentColor: "#6B1020", width: "100%" }}
            />
          </div>
        </div>
      )}

      {/* TOC drawer */}
      {showTOC && (
        <div className="fixed inset-0 z-50 flex">
          <div
            className="absolute inset-0 bg-black/40"
            style={{ backdropFilter: "blur(4px)" }}
            onClick={() => setShowTOC(false)}
          />
          <div
            className="relative ml-auto w-72 h-full overflow-y-auto py-6 px-5 animate-slide-up"
            style={{ background: colors.surface }}
          >
            <div className="flex justify-between items-center mb-6">
              <span style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 20, color: colors.text }}>
                Contents
              </span>
              <button type="button" onClick={() => setShowTOC(false)} aria-label="Close">
                <X size={18} color="#A88A8F" />
              </button>
            </div>
            <div className="space-y-1">
              {chapters.map((ch, index) => {
                const cur = index === currentIdx;
                return (
                  <button
                    key={ch.id}
                    type="button"
                    className="w-full text-left px-3 py-2.5 rounded-lg transition-all"
                    style={{
                      background: cur ? "rgba(107,16,32,0.08)" : "transparent",
                      borderLeft: cur ? "2px solid #6B1020" : "2px solid transparent",
                      color: cur ? "#6B1020" : colors.text,
                      fontFamily: "'Crimson Pro', Georgia, serif",
                      fontSize: 15,
                    }}
                    onClick={() => { setShowTOC(false); goToChapter(ch.id); }}
                  >
                    <span style={{ fontFamily: "Inter, sans-serif", fontSize: 11, color: "#A88A8F", marginRight: 6 }}>
                      {index + 1}.
                    </span>
                    {ch.title}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
