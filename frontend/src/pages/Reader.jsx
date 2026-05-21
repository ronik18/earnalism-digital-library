import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Volume2, VolumeX, Bookmark, BookmarkCheck, Settings, List, X, Loader2, Clock, AlertCircle, LogIn, CreditCard } from 'lucide-react';
import axios from 'axios';
import { API, TOKEN_KEY, USER_TOKEN_KEY, formatError } from '../lib/api';
import { toast } from 'sonner';
import ReaderUpsellPrompt from '../components/Funnel/ReaderUpsellPrompt';
import SecureReader from '../components/SecureReader';
import { trackFunnelEvent } from '../lib/funnelAnalytics';
import { canShowReaderFinishPrompt, markReaderFinishPromptShown } from '../lib/funnelOffers';
import { useAuth } from '../context/AuthContext';

const THEMES = {
  beige: { canvas: '#FAF7F0', surface: '#F5F0E8', text: '#1C0A0E', accent: '#6B1020', border: '#E8DDD8', label: 'Beige' },
  dark: { canvas: '#141010', surface: '#1E1518', text: '#EDE0D8', accent: '#D4A843', border: '#2E1F22', label: 'Dark' },
  sepia: { canvas: '#EFE4C8', surface: '#E5D8B5', text: '#3B2010', accent: '#8B1A2A', border: '#D5C8A5', label: 'Sepia' },
};

const BENGALI_RE = /[\u0980-\u09FF]/;
const READER_SERIF = "'Crimson Pro', 'Noto Serif Bengali', Georgia, serif";
const READER_DISPLAY = "'Cormorant Garamond', 'Noto Serif Bengali', serif";
const BENGALI_SERIF = "'Noto Serif Bengali', 'Crimson Pro', Georgia, serif";
const UI_FONT = "Inter, 'Noto Sans Bengali', sans-serif";

const FONT_SIZES = [
  { label: 'XS', size: '15px' },
  { label: 'S', size: '17px' },
  { label: 'M', size: '19px' },
  { label: 'L', size: '21px' },
];

const LOW_BALANCE_THRESHOLD = 300;

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function getUserToken() {
  return localStorage.getItem(USER_TOKEN_KEY);
}

function getUserAuthHeaders() {
  return authHeaders(getUserToken());
}

function getAdminAuthHeaders() {
  return authHeaders(localStorage.getItem(TOKEN_KEY));
}

function getChapterAuthHeaders() {
  const token = localStorage.getItem(USER_TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || localStorage.getItem('token');
  return authHeaders(token);
}

function getCurrentReaderPath() {
  return `${window.location.pathname}${window.location.search}`;
}

function apiErrorMessage(err, fallback) {
  return formatError(err.response?.data?.detail) || err.message || fallback;
}

function containsBengaliText(value) {
  return BENGALI_RE.test(value || '');
}

function normalizeVoiceLang(value = '') {
  return String(value || '').toLowerCase().replace('_', '-');
}

function isBengaliVoice(voice) {
  const lang = normalizeVoiceLang(voice?.lang);
  const name = String(voice?.name || '');
  return lang.startsWith('bn') || /bengali|bangla/i.test(name);
}

function selectNarrationVoice(voices = [], prefersBengali = false) {
  const available = Array.from(voices || []).filter(Boolean);
  if (prefersBengali) {
    const bengaliVoice = available.find(isBengaliVoice);
    return { voice: bengaliVoice || null, exactLanguage: Boolean(bengaliVoice) };
  }

  const preferredEnglish = available.find((voice) => /Samantha|Karen|Moira|Daniel/i.test(voice.name))
    || available.find((voice) => normalizeVoiceLang(voice.lang) === 'en-us')
    || available.find((voice) => normalizeVoiceLang(voice.lang).startsWith('en'))
    || available[0]
    || null;

  return { voice: preferredEnglish, exactLanguage: Boolean(preferredEnglish) };
}

function sanitizeReaderHtml(html) {
  if (typeof document === 'undefined') return html || '';
  const template = document.createElement('template');
  template.innerHTML = html || '';
  template.content.querySelectorAll('script,style,iframe,object,embed,form,input,button,meta,link').forEach((node) => node.remove());
  template.content.querySelectorAll('*').forEach((node) => {
    Array.from(node.attributes).forEach((attr) => {
      const name = attr.name.toLowerCase();
      const value = attr.value || '';
      if (name.startsWith('on')) node.removeAttribute(attr.name);
      if ((name === 'href' || name === 'src') && /^\s*javascript:/i.test(value)) node.removeAttribute(attr.name);
    });
    if (node.tagName?.toLowerCase() === 'img' && !node.getAttribute('src')) {
      node.setAttribute('alt', node.getAttribute('alt') || 'Image unavailable');
      node.classList.add('reader-img--error');
    }
  });
  return template.innerHTML;
}

function escapeHtmlText(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function wrapWordsInSpans(html) {
  if (typeof document === 'undefined') return { html: html || '', totalWords: 0 };
  const div = document.createElement('div');
  div.innerHTML = html || '';
  let wordIndex = 0;
  let textOffset = 0;

  function processNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent;
      if (!text) return;
      if (!text.trim()) {
        textOffset += text.length;
        return;
      }

      const wrapper = document.createElement('span');
      let lastIndex = 0;
      let nextHtml = '';
      const re = /\S+/g;
      let match;

      while ((match = re.exec(text)) !== null) {
        const start = textOffset + match.index;
        const end = start + match[0].length;
        nextHtml += escapeHtmlText(text.slice(lastIndex, match.index));
        nextHtml += `<span class="tts-word" data-word="${wordIndex}" data-start="${start}" data-end="${end}">${escapeHtmlText(match[0])}</span>`;
        wordIndex += 1;
        lastIndex = match.index + match[0].length;
      }

      nextHtml += escapeHtmlText(text.slice(lastIndex));
      wrapper.innerHTML = nextHtml;
      textOffset += text.length;

      const parent = node.parentNode;
      while (wrapper.firstChild) parent.insertBefore(wrapper.firstChild, node);
      parent.removeChild(node);
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      const tag = node.tagName?.toUpperCase();
      if (tag === 'SCRIPT' || tag === 'STYLE') return;
      Array.from(node.childNodes).forEach(processNode);
    }
  }

  Array.from(div.childNodes).forEach(processNode);
  return { html: div.innerHTML, totalWords: wordIndex };
}

function countWordsInHtml(html) {
  if (typeof document === 'undefined') return (html || '').split(/\s+/).filter(Boolean).length;
  const div = document.createElement('div');
  div.innerHTML = html || '';
  return (div.textContent || '').split(/\s+/).filter(Boolean).length;
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

async function fetchReaderBook(bookId) {
  try {
    return await axios.get(`${API}/books/${bookId}`);
  } catch (err) {
    const adminToken = localStorage.getItem(TOKEN_KEY);
    if (err.response?.status === 404 && adminToken) {
      return axios.get(`${API}/admin/books/${bookId}`, { headers: getAdminAuthHeaders() });
    }
    throw err;
  }
}

export default function Reader() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const bookId = slug;
  const chapterId = new URLSearchParams(window.location.search).get('c');

  const [book, setBook] = useState(null);
  const [chapter, setChapter] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [activeChapterId, setActiveChapterId] = useState(chapterId);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lockedState, setLockedState] = useState(null);

  const [theme, setTheme] = useState('beige');
  const [fontSizeIdx, setFontSizeIdx] = useState(1);
  const [showSettings, setShowSettings] = useState(false);
  const [showTOC, setShowTOC] = useState(false);
  const [toolbarVisible, setToolbarVisible] = useState(true);
  const [bookmarked, setBookmarked] = useState(false);

  const [ttsActive, setTtsActive] = useState(false);
  const [ttsPaused, setTtsPaused] = useState(false);
  const [ttsWordIndex, setTtsWordIndex] = useState(-1);
  const [ttsSpeed, setTtsSpeed] = useState(1);
  const [ttsVoices, setTtsVoices] = useState([]);
  const [processedHtml, setProcessedHtml] = useState('');
  const [totalWords, setTotalWords] = useState(0);

  const [readProgress, setReadProgress] = useState(0);
  const [contentBlurred, setContentBlurred] = useState(false);

  const [walletSeconds, setWalletSeconds] = useState(0);
  const [showLowBalanceWarning, setShowLowBalanceWarning] = useState(false);
  const [showTopUpModal, setShowTopUpModal] = useState(false);
  const [savedScrollPosition, setSavedScrollPosition] = useState(0);
  const [topUpPacks, setTopUpPacks] = useState([]);
  const [selectedPack, setSelectedPack] = useState(1);
  const [topUpProcessing, setTopUpProcessing] = useState(false);
  const [showTopUpSuccess, setShowTopUpSuccess] = useState(false);
  const [topUpSuccessMinutes, setTopUpSuccessMinutes] = useState(0);

  const [sessionId, setSessionId] = useState(null);
  const [meteredSessionActive, setMeteredSessionActive] = useState(false);
  const [showReaderUpsell, setShowReaderUpsell] = useState(false);

  const contentRef = useRef(null);
  const utteranceRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);
  const lastScrollY = useRef(0);
  const wordsRef = useRef([]);
  const pulseIntervalRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const completionReportedRef = useRef('');
  const upsellShownRef = useRef('');
  const ttsWarningShownRef = useRef(false);

  const stopTTS = useCallback(() => {
    synthRef.current?.cancel?.();
    setTtsActive(false);
    setTtsPaused(false);
    setTtsWordIndex(-1);
    wordsRef.current.forEach((word) => word.classList.remove('active'));
  }, []);

  useEffect(() => {
    const synth = synthRef.current;
    if (!synth?.getVoices) return undefined;

    const refreshVoices = () => setTtsVoices(synth.getVoices());
    refreshVoices();
    synth.addEventListener?.('voiceschanged', refreshVoices);
    synth.onvoiceschanged = refreshVoices;

    return () => {
      synth.removeEventListener?.('voiceschanged', refreshVoices);
      if (synth.onvoiceschanged === refreshVoices) synth.onvoiceschanged = null;
    };
  }, []);

  const sendPulse = useCallback(async () => {
    if (!sessionId || !meteredSessionActive) return;
    const headers = getUserAuthHeaders();

    try {
      const response = await axios.post(`${API}/reading/pulse`, { session_id: sessionId }, { headers });
      const { status, wallet_seconds } = response.data;

      switch (status) {
        case 'ok':
          setWalletSeconds(wallet_seconds);
          break;
        case 'low_balance':
          setWalletSeconds(wallet_seconds);
          setShowLowBalanceWarning(true);
          break;
        case 'wallet_empty':
          setWalletSeconds(0);
          clearInterval(pulseIntervalRef.current);
          setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0);
          setShowTopUpModal(true);
          break;
        case 'session_invalid':
          clearInterval(pulseIntervalRef.current);
          alert('Your reading session was opened on another device');
          break;
        default:
          break;
      }
    } catch (err) {
      // Reader heartbeats should not interrupt active reading on transient network errors.
    }
  }, [sessionId, meteredSessionActive]);

  useEffect(() => {
    const id = crypto.randomUUID();
    let protectionInterval;

    setSessionId(id);

    const onContextMenu = (event) => event.preventDefault();
    const onKeyDown = (event) => {
      const blockedCombo = (event.ctrlKey || event.metaKey) && ['s', 'u', 'a', 'p', 'S', 'U', 'A', 'P'].includes(event.key);
      const blockedKey = event.key === 'F12' || event.key === 'PrintScreen';

      if (blockedCombo || blockedKey) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    const onCopy = (event) => {
      event.preventDefault();
      event.clipboardData.setData('text/plain', 'Content is protected © Earnalism');
    };
    const onVisibilityChange = () => {
      setContentBlurred(document.hidden);
    };

    document.addEventListener('contextmenu', onContextMenu);
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('copy', onCopy);
    document.addEventListener('visibilitychange', onVisibilityChange);

    protectionInterval = setInterval(() => {
      const devtoolsOpen = window.outerWidth - window.innerWidth > 160 || window.outerHeight - window.innerHeight > 160;
      setContentBlurred(devtoolsOpen);
    }, 1000);

    return () => {
      document.removeEventListener('contextmenu', onContextMenu);
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('copy', onCopy);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      clearInterval(protectionInterval);
    };
  }, []);

  useEffect(() => {
    if (!bookId || !sessionId) return undefined;

    let cancelled = false;
    let startedSession = false;
    let endSessionHeaders = {};

    async function loadReader() {
      setLoading(true);
      setError(null);
      setLockedState(null);
      setMeteredSessionActive(false);

      try {
        const [bookRes, packsRes] = await Promise.all([
          fetchReaderBook(bookId),
          axios.get(`${API}/payments/packs`),
        ]);
        if (cancelled) return;

        const loadedChapters = [...(bookRes.data?.chapters || [])].sort((a, b) => (a.order || 0) - (b.order || 0));
        const activeChapterId = chapterId || loadedChapters[0]?.id;

        setBook(bookRes.data);
        setChapters(loadedChapters);
        setTopUpPacks(packsRes.data || []);
        setActiveChapterId(activeChapterId || null);

        if (!activeChapterId) {
          setChapter(null);
          setProcessedHtml('');
          setTotalWords(0);
          setLoading(false);
          return;
        }

        if (getUserToken()) {
          try {
            const walletRes = await axios.get(`${API}/users/me/wallet`, { headers: getUserAuthHeaders() });
            if (!cancelled) setWalletSeconds(walletRes.data.wallet_seconds || 0);
          } catch (walletErr) {
            if (walletErr.response?.status === 401) {
              localStorage.removeItem(USER_TOKEN_KEY);
            } else if (walletErr.response?.status !== 403) {
              throw walletErr;
            }
            if (!cancelled) setWalletSeconds(0);
          }
        } else {
          setWalletSeconds(0);
        }

        const chapterRes = await axios.get(
          `${API}/reader/chapter/${encodeURIComponent(bookId)}/${encodeURIComponent(activeChapterId)}`,
          { headers: getChapterAuthHeaders() },
        );
        if (cancelled) return;

        const gate = chapterRes.data || {};
        const loadedChapter = gate.chapter || gate;

        setChapter(loadedChapter);
        if (!chapterId) {
          window.history.replaceState(null, '', `${window.location.pathname}?c=${activeChapterId}`);
        }

        if (gate.locked) {
          setProcessedHtml('');
          setTotalWords(0);
          setLockedState({
            reason: gate.reason || 'LOCKED',
            message: gate.message || 'This chapter is locked.',
            chapter: loadedChapter,
          });
          setLoading(false);
          return;
        }

        const safeHtml = sanitizeReaderHtml(loadedChapter.content);
        // Keep first render light. TTS word spans are injected only if narration starts.
        setProcessedHtml(safeHtml);
        setTotalWords(countWordsInHtml(safeHtml));
        setLockedState(null);

        if (getUserToken() && !gate.is_preview) {
          endSessionHeaders = getUserAuthHeaders();
          await axios.post(`${API}/reading/session/start`, { session_id: sessionId, book_slug: bookId, chapter_id: activeChapterId }, { headers: endSessionHeaders });
          startedSession = true;
          setMeteredSessionActive(true);
        }

        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          const status = err.response?.status;
          if (status === 401) {
            localStorage.removeItem(USER_TOKEN_KEY);
            setLockedState({
              reason: 'AUTH_REQUIRED',
              message: 'Sign in to continue reading this chapter.',
              chapter: null,
            });
            setError(null);
          } else if (status === 402) {
            setLockedState({
              reason: 'INSUFFICIENT_READING_TIME',
              message: 'Your reading time has ended. Add reading time to continue.',
              chapter: null,
            });
            setError(null);
          } else {
            setError(apiErrorMessage(err, 'This chapter could not be opened.'));
          }
          setMeteredSessionActive(false);
          setLoading(false);
        }
      }
    }

    loadReader();

    return () => {
      cancelled = true;
      stopTTS();
      clearInterval(pulseIntervalRef.current);
      if (startedSession) {
        axios.post(`${API}/reading/session/end`, { session_id: sessionId }, { headers: endSessionHeaders }).catch(() => {});
      }
    };
  }, [bookId, chapterId, sessionId, stopTTS]);

  useEffect(() => {
    if (meteredSessionActive && chapter && processedHtml && sessionId) {
      clearInterval(pulseIntervalRef.current);
      pulseIntervalRef.current = setInterval(sendPulse, 30000);
    }

    return () => clearInterval(pulseIntervalRef.current);
  }, [chapter, processedHtml, sessionId, meteredSessionActive, sendPulse]);

  useEffect(() => {
    wordsRef.current = Array.from(contentRef.current?.querySelectorAll('.tts-word') || []);
  }, [processedHtml]);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return undefined;

    let rafId = 0;
    const updateFromScroll = () => {
      rafId = 0;
      const max = el.scrollHeight - el.clientHeight;
      const pct = max > 0 ? (el.scrollTop / max) * 100 : 0;
      setReadProgress(Math.min(100, Math.round(pct)));

      if (el.scrollTop > lastScrollY.current + 10) setToolbarVisible(false);
      if (el.scrollTop < lastScrollY.current - 5) setToolbarVisible(true);
      lastScrollY.current = el.scrollTop;
    };
    const onScroll = () => {
      if (rafId) return;
      rafId = window.requestAnimationFrame(updateFromScroll);
    };

    el.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      el.removeEventListener('scroll', onScroll);
      if (rafId) window.cancelAnimationFrame(rafId);
    };
  }, [loading]);

  useEffect(() => {
    setShowReaderUpsell(false);
  }, [activeChapterId, chapterId]);

  // Funnel prompt appears near the end of short reads only, never mid-paragraph.
  useEffect(() => {
    if (!chapter || lockedState || loading || readProgress < 96) return;
    const currentKey = `${bookId}:${activeChapterId || chapterId || chapter?.id}`;
    if (upsellShownRef.current === currentKey || !canShowReaderFinishPrompt()) return;
    const estimatedMinutes = totalWords > 0 ? Math.ceil(totalWords / 220) : 3;
    if (estimatedMinutes > 10 && !chapter?.is_free_preview) return;

    upsellShownRef.current = currentKey;
    markReaderFinishPromptShown();
    setShowReaderUpsell(true);
    trackFunnelEvent('reader_upsell_shown', {
      book_slug: bookId,
      chapter_id: activeChapterId || chapterId || chapter?.id,
      estimated_minutes: estimatedMinutes,
      pack_id: '1h',
    });
  }, [activeChapterId, bookId, chapter, chapterId, loading, lockedState, readProgress, totalWords]);

  // Completion rewards are best-effort and idempotent; failures must not disturb reading.
  useEffect(() => {
    if (!chapter || lockedState || loading || readProgress < 98 || !getUserToken()) return;
    const currentKey = `${bookId}:${activeChapterId || chapterId || chapter?.id}`;
    if (completionReportedRef.current === currentKey) return;
    completionReportedRef.current = currentKey;

    async function recordCompletion() {
      try {
        const { data } = await axios.post(
          `${API}/users/me/rewards/completion`,
          {
            book_slug: bookId,
            chapter_id: activeChapterId || chapterId || chapter?.id,
            chapter_title: chapter?.title || '',
            progress: readProgress,
          },
          { headers: getUserAuthHeaders() },
        );
        trackFunnelEvent('reader_completion_recorded', {
          book_slug: bookId,
          chapter_id: activeChapterId || chapterId || chapter?.id,
          streak_days: data?.streak_days || 0,
        });

        if (data?.eligible) {
          const claimRes = await axios.post(`${API}/users/me/rewards/claim`, {}, { headers: getUserAuthHeaders() });
          const reward = claimRes.data || {};
          if (reward.claimed_now) {
            setWalletSeconds(reward.wallet_seconds || 0);
            toast.success(`${reward.credit_minutes || 10} minutes credited toward The Reader's Reserve.`);
            trackFunnelEvent('reader_reward_claimed', {
              book_slug: bookId,
              chapter_id: activeChapterId || chapterId || chapter?.id,
              credit_minutes: reward.credit_minutes || 10,
            });
          }
        }
      } catch {
        // Reward logging must never interrupt reading.
      }
    }

    recordCompletion();
  }, [activeChapterId, bookId, chapter, chapterId, loading, lockedState, readProgress]);

  const handleTopUp = async (pack) => {
    if (!pack) return;
    setTopUpProcessing(true);
    const headers = getUserAuthHeaders();

    try {
      const orderRes = await axios.post(`${API}/payments/create-order`, { pack_id: pack._id || pack.id }, { headers });
      const orderData = orderRes.data;
      const options = {
        key: orderData.key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        order_id: orderData.order_id,
        name: 'Earnalism',
        description: `Top up ${pack.minutes} minutes`,
        handler: async (response) => {
          const verifyRes = await axios.post(`${API}/payments/verify`, {
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          }, { headers });
          const { wallet_seconds } = verifyRes.data;

          setWalletSeconds(wallet_seconds);
          setShowTopUpModal(false);
          setTopUpProcessing(false);
          setShowTopUpSuccess(true);
          setTopUpSuccessMinutes(pack.minutes);
          setShowLowBalanceWarning(false);

          setTimeout(() => {
            setShowTopUpSuccess(false);
            if (scrollContainerRef.current) {
              scrollContainerRef.current.scrollTop = savedScrollPosition;
            }
            pulseIntervalRef.current = setInterval(sendPulse, 30000);
          }, 1500);
        },
        modal: {
          ondismiss: () => setTopUpProcessing(false),
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (err) {
      setTopUpProcessing(false);
    }
  };

  const isBengali = useMemo(
    () => containsBengaliText(`${book?.title || ''} ${chapter?.title || ''} ${processedHtml || ''}`),
    [book, chapter, processedHtml],
  );

  const highlightSpokenWord = useCallback((index) => {
    wordsRef.current.forEach((word) => word.classList.remove('active'));
    const current = wordsRef.current[index];
    if (!current) return;

    current.classList.add('active');
    current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTtsWordIndex(index);
  }, []);

  const wordIndexFromCharIndex = useCallback((charIndex) => {
    if (!Number.isFinite(charIndex) || charIndex < 0) return -1;
    const exact = wordsRef.current.findIndex((word) => {
      const start = Number(word.dataset.start);
      const end = Number(word.dataset.end);
      return Number.isFinite(start) && Number.isFinite(end) && start <= charIndex && charIndex < end;
    });
    if (exact >= 0) return exact;
    return wordsRef.current.findIndex((word) => Number(word.dataset.start) >= charIndex);
  }, []);

  const buildUtterance = useCallback(() => {
    if (typeof SpeechSynthesisUtterance === 'undefined') return null;
    const plainText = contentRef.current?.innerText || '';
    if (!plainText.trim()) return null;

    const utter = new SpeechSynthesisUtterance(plainText);
    utter.rate = ttsSpeed;
    utter.pitch = 1;
    utter.lang = isBengali ? 'bn-BD' : 'en-US';

    const voices = ttsVoices.length ? ttsVoices : (synthRef.current?.getVoices?.() || []);
    const preferred = selectNarrationVoice(voices, isBengali);

    if (preferred.voice) utter.voice = preferred.voice;
    if (isBengali && !preferred.exactLanguage && !ttsWarningShownRef.current) {
      ttsWarningShownRef.current = true;
      toast.warning('Bengali narration depends on your browser voice pack. If pronunciation sounds off, add a Bengali voice in system settings.');
    }

    let wordCount = 0;

    utter.onboundary = (event) => {
      if (event.name === 'word') {
        highlightSpokenWord(wordCount);
        wordCount += 1;
        return;
      }

      const index = wordIndexFromCharIndex(event.charIndex);
      if (index >= 0) {
        wordCount = index + 1;
        highlightSpokenWord(index);
      }
    };

    const resetTTS = () => {
      setTtsActive(false);
      setTtsPaused(false);
      setTtsWordIndex(-1);
      wordsRef.current.forEach((word) => word.classList.remove('active'));
    };

    utter.onend = resetTTS;
    utter.onerror = (event) => {
      resetTTS();
      if (event.error && event.error !== 'interrupted' && event.error !== 'canceled') {
        toast.error('Audio reading could not start in this browser.');
      }
    };

    return utter;
  }, [highlightSpokenWord, isBengali, ttsSpeed, ttsVoices, wordIndexFromCharIndex]);

  const startTTS = useCallback(() => {
    const synth = synthRef.current;
    if (!synth?.speak || typeof SpeechSynthesisUtterance === 'undefined') {
      toast.error('Audio reading is not available in this browser.');
      return;
    }

    synth.cancel();
    const speak = () => {
      wordsRef.current = Array.from(contentRef.current?.querySelectorAll('.tts-word') || []);
      const utter = buildUtterance();
      if (!utter) return;

      utteranceRef.current = utter;
      synth.speak(utter);
      setTtsActive(true);
      setTtsPaused(false);
    };

    if (processedHtml && !processedHtml.includes('class="tts-word"')) {
      const wrapped = wrapWordsInSpans(processedHtml);
      setProcessedHtml(wrapped.html);
      setTotalWords(wrapped.totalWords);
      window.requestAnimationFrame(() => window.requestAnimationFrame(speak));
      return;
    }

    speak();
  }, [buildUtterance, processedHtml]);

  const pauseTTS = () => {
    synthRef.current?.pause?.();
    setTtsPaused(true);
  };

  const resumeTTS = () => {
    synthRef.current?.resume?.();
    setTtsPaused(false);
  };

  const handleVoiceToggle = () => {
    if (!ttsActive) startTTS();
    else if (ttsPaused) resumeTTS();
    else pauseTTS();
  };

  const currentIdx = useMemo(
    () => chapters.findIndex((item) => item.id === (activeChapterId || chapterId)),
    [chapters, activeChapterId, chapterId],
  );
  const prevChapter = chapters[currentIdx - 1];
  const nextChapter = chapters[currentIdx + 1];

  const goToChapter = (id) => {
    stopTTS();
    navigate(`/reader/${bookId}?c=${id}`);
  };

  const toggleBookmark = async () => {
    if (!getUserToken()) {
      navigate(`/login?next=${encodeURIComponent(getCurrentReaderPath())}`);
      return;
    }
    const headers = getUserAuthHeaders();
    await axios.post(`${API}/bookmarks`, { bookId, chapterId: activeChapterId || chapterId }, { headers });
    setBookmarked((value) => !value);
  };

  const illustratedContent = useMemo(() => {
    const category = `${book?.category_slug || ''} ${book?.category || ''}`.toLowerCase();
    const illustrationCategory = /fantasy|kid|kids|children|illustrat/.test(category);
    const uploadedImages = chapter?.has_images || /reader-img--(?:photo|illustration)|data-type="(?:photo|illustration)"/.test(processedHtml);
    return Boolean(illustrationCategory || uploadedImages);
  }, [book, chapter, processedHtml]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: THEMES.beige.canvas }}>
        <Loader2 size={32} className="animate-spin" color="#6B1020" />
        <div style={{ fontFamily: READER_SERIF, fontSize: 17, color: '#7A5C62' }}>
          Opening chapter…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 px-6 text-center min-h-screen" style={{ background: THEMES.beige.canvas }}>
        <AlertCircle size={28} color="#6B1020" />
        <div style={{ fontFamily: READER_SERIF, fontSize: 18, color: '#6B1020' }}>
          {error}
        </div>
        <button type="button" onClick={() => navigate(-1)} className="px-6 py-2 rounded-full" style={{ background: '#6B1020', color: '#FAF7F0', fontFamily: 'Inter', fontSize: 14 }}>
          Back
        </button>
      </div>
    );
  }

  if (lockedState) {
    const reason = lockedState.reason;
    const previewChapter = chapters[0];
    const canOpenPreview = previewChapter?.id && previewChapter.id !== activeChapterId;
    const title = lockedState.chapter?.title || chapter?.title || 'Chapter locked';
    const signInUrl = `/login?next=${encodeURIComponent(getCurrentReaderPath())}`;

    return (
      <div className="flex min-h-screen items-center justify-center px-5 py-14 text-center" style={{ background: THEMES.beige.canvas }}>
        <div className="w-full max-w-md rounded-2xl border border-[#E8DDD8] bg-white/70 px-7 py-9 shadow-book">
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: '#F5F0E8', color: '#6B1020' }}>
            {reason === 'INSUFFICIENT_READING_TIME' ? <CreditCard size={22} /> : <LogIn size={22} />}
          </div>
          <div className="italic-eyebrow mb-3">Reading access</div>
          <h1 className="font-serif-light text-3xl text-burgundy leading-tight">{title}</h1>
          <p className="mt-5 text-sm font-light leading-relaxed text-charcoal-soft">
            {lockedState.message || 'This chapter is locked.'}
          </p>

          <div className="mt-8 flex flex-col gap-3">
            {reason === 'AUTH_REQUIRED' && (
              <button type="button" onClick={() => navigate(signInUrl)} className="btn-primary w-full justify-center">
                Sign In
              </button>
            )}
            {reason === 'INSUFFICIENT_READING_TIME' && (
              <button type="button" onClick={() => navigate('/pricing')} className="btn-primary w-full justify-center">
                Add Reading Time
              </button>
            )}
            {reason === 'BLOCKED' && (
              <button type="button" onClick={() => navigate('/contact')} className="btn-primary w-full justify-center">
                Contact Support
              </button>
            )}
            {canOpenPreview && (
              <button type="button" onClick={() => navigate(`/reader/${bookId}?c=${previewChapter.id}`)} className="btn-secondary w-full justify-center">
                Read Free Preview
              </button>
            )}
            <button type="button" onClick={() => navigate(`/book/${bookId}`)} className="text-sm text-charcoal-soft underline decoration-[var(--brand-gold)]/60 underline-offset-4">
              Back to book
            </button>
          </div>
        </div>
      </div>
    );
  }

  const colors = theme === 'beige' && illustratedContent
    ? { ...THEMES.beige, canvas: '#FFFFFF', surface: '#FFFFFF', border: '#E8DDD8', label: 'White' }
    : THEMES[theme];
  const lowBalance = walletSeconds > 0 && walletSeconds <= LOW_BALANCE_THRESHOLD;
  const voiceButtonLabel = !ttsActive
    ? (isBengali ? 'Listen in Bengali' : 'Listen')
    : ttsPaused ? 'Resume narration' : 'Pause narration';

  return (
    <div ref={scrollContainerRef} className="relative flex flex-col min-h-screen overflow-y-auto reader-scroll" style={{ background: colors.canvas, color: colors.text, transition: 'background 400ms ease, color 300ms ease' }}>
      <div className="fixed top-0 left-0 right-0 z-50 h-[2px]" style={{ background: colors.border }}>
        <div style={{ width: `${readProgress}%`, height: '100%', background: '#6B1020', transition: 'width 300ms' }} />
      </div>

      <header className="fixed top-0.5 left-0 right-0 z-40" style={{ background: `${colors.canvas}EE`, backdropFilter: 'blur(12px)', borderBottom: `1px solid ${colors.border}`, transform: toolbarVisible ? 'translateY(0)' : 'translateY(-100%)', transition: 'transform 300ms ease' }}>
        <div className="flex items-center justify-between px-4 py-3">
        <button type="button" onClick={() => navigate(`/book/${bookId}`)} className="flex items-center gap-2 min-w-0" style={{ color: colors.accent, fontFamily: UI_FONT, fontSize: 13 }}>
            <ChevronLeft size={16} />
            <span className="hidden sm:inline">{book?.title}</span>
          </button>

          <div className="flex flex-col items-center text-center min-w-0 px-2">
            <div className="truncate" lang={isBengali ? 'bn' : undefined} style={{ fontFamily: isBengali ? BENGALI_SERIF : READER_SERIF, fontSize: 14, color: colors.text, maxWidth: 220 }}>
              {chapter?.title}
            </div>
            <div style={{ fontFamily: UI_FONT, fontSize: 11, color: '#A88A8F' }}>
              Ch. {Math.max(0, currentIdx) + 1} of {chapters.length}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {walletSeconds > 0 && (
              <div className={lowBalance ? 'wallet-low flex items-center gap-1' : 'flex items-center gap-1'} style={{ fontFamily: UI_FONT, fontSize: 12, color: lowBalance ? '#D4A843' : '#A88A8F' }}>
                <Clock size={14} />
                {formatWalletTime(walletSeconds)}
              </div>
            )}
            <button type="button" onClick={toggleBookmark} aria-label={bookmarked ? 'Remove bookmark' : 'Bookmark chapter'}>
              {bookmarked ? <BookmarkCheck size={18} color="#6B1020" /> : <Bookmark size={18} color="#A88A8F" />}
            </button>
            <button type="button" onClick={() => setShowTOC(true)} aria-label="Open contents">
              <List size={18} color="#A88A8F" />
            </button>
            <button type="button" onClick={() => setShowSettings((value) => !value)} aria-label="Open reading settings">
              <Settings size={18} color="#A88A8F" />
            </button>
          </div>
        </div>
      </header>

      <main key={chapter?.id || chapterId || bookId} className="flex-1 px-5 pt-20 pb-36 page-enter">
        <div className="reader-canvas mx-auto">
          <h2 lang={isBengali ? 'bn' : undefined} style={{ fontFamily: isBengali ? BENGALI_SERIF : READER_DISPLAY, fontSize: 28, fontWeight: 500, textAlign: 'center', color: colors.accent, letterSpacing: '-0.01em', lineHeight: isBengali ? 1.55 : 1.4, marginBottom: 24, overflowWrap: 'break-word' }}>
            {chapter?.title}
          </h2>
          <div className="flex items-center gap-3 mb-10 justify-center">
            <div className="flex-1 h-px" style={{ background: colors.border }} />
            <span style={{ color: colors.accent, fontSize: 20 }}>❧</span>
            <div className="flex-1 h-px" style={{ background: colors.border }} />
          </div>
          <SecureReader
            sessionId={sessionId}
            userName={user && typeof user === 'object' ? user.name : 'Reader'}
            userEmail={user && typeof user === 'object' ? user.email : ''}
            bookSlug={bookId}
            chapterId={activeChapterId || chapterId || chapter?.id}
            title={`${book?.title || 'Earnalism'} · ${chapter?.title || 'Chapter'}`}
            contentRef={contentRef}
            className={isBengali ? 'reader-content reader-content--bengali' : 'drop-cap reader-content'}
            html={processedHtml}
            blurred={contentBlurred}
            lang={isBengali ? 'bn' : 'en'}
            style={{ fontFamily: isBengali ? BENGALI_SERIF : READER_SERIF, fontSize: FONT_SIZES[fontSizeIdx].size, lineHeight: isBengali ? 1.9 : 1.75, color: colors.text, transition: 'filter 300ms ease', userSelect: 'none', WebkitUserSelect: 'none' }}
          />
          {showReaderUpsell && (
            <ReaderUpsellPrompt
              book={book}
              chapter={chapter}
              onDismiss={() => {
                setShowReaderUpsell(false);
                trackFunnelEvent('reader_upsell_dismissed', {
                  book_slug: bookId,
                  chapter_id: activeChapterId || chapterId || chapter?.id,
                });
              }}
            />
          )}
        </div>
      </main>

      <div className="fixed bottom-0 left-0 right-0 z-40" style={{ background: `${colors.canvas}F5`, backdropFilter: 'blur(16px)', borderTop: `1px solid ${colors.border}`, transform: toolbarVisible ? 'translateY(0)' : 'translateY(100%)', transition: 'transform 300ms ease' }}>
        {ttsActive && (
          <div style={{ height: 2, background: colors.border }}>
            <div style={{ width: `${totalWords > 0 ? (ttsWordIndex / totalWords) * 100 : 0}%`, height: '100%', background: '#D4A843', transition: 'width 200ms' }} />
          </div>
        )}

        <div className="flex items-center justify-between px-6 py-3 max-w-xl mx-auto">
          <button type="button" disabled={!prevChapter} onClick={() => prevChapter && goToChapter(prevChapter.id)} className="flex items-center gap-1" style={{ color: colors.accent, fontFamily: 'Inter', fontSize: 12, opacity: prevChapter ? 1 : 0.3 }}>
            <ChevronLeft size={16} />
            <span className="hidden sm:inline">Prev</span>
          </button>

          <button type="button" onClick={handleVoiceToggle} className="flex flex-col items-center gap-1" aria-label={voiceButtonLabel}>
            <span className={ttsActive && !ttsPaused ? 'p-3 rounded-full animate-pulse-soft' : 'p-3 rounded-full'} style={{ background: ttsActive && !ttsPaused ? '#6B1020' : colors.surface, color: ttsActive && !ttsPaused ? '#FAF7F0' : colors.accent, transition: 'all 250ms ease', boxShadow: ttsActive && !ttsPaused ? '0 0 0 4px rgba(107,16,32,0.15)' : 'none', display: 'inline-flex' }}>
              {ttsActive && !ttsPaused ? <Volume2 size={20} /> : <VolumeX size={20} />}
            </span>
            <span style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F' }}>
              {!ttsActive ? 'Listen' : ttsPaused ? 'Resume' : 'Pause'}
            </span>
          </button>

          {ttsActive && (
            <button type="button" onClick={stopTTS} className="px-3 py-1 rounded-full" style={{ background: colors.surface, color: '#A88A8F', fontFamily: 'Inter', fontSize: 11 }}>
              Stop
            </button>
          )}

          <button type="button" disabled={!nextChapter} onClick={() => nextChapter && goToChapter(nextChapter.id)} className="flex items-center gap-1" style={{ color: colors.accent, fontFamily: 'Inter', fontSize: 12, opacity: nextChapter ? 1 : 0.3 }}>
            <span className="hidden sm:inline">Next</span>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {showLowBalanceWarning && !showTopUpModal && walletSeconds > 0 && (
        <div className="fixed left-0 right-0 z-[45] animate-slide-up" style={{ bottom: 64, background: '#E8C97A', borderTop: '1px solid #D4A843' }}>
          <div className="flex items-center justify-between px-4 py-3 max-w-xl mx-auto">
            <div className="flex items-center gap-2">
              <Clock size={16} color="#6B1020" />
              <span style={{ fontFamily: 'Inter', fontSize: 13, color: '#6B1020' }}>
                {formatWalletTime(walletSeconds)} of reading time remaining
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => { setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0); setShowTopUpModal(true); }} className="px-3 py-1 rounded-full" style={{ background: '#6B1020', color: '#FAF7F0', fontFamily: 'Inter', fontSize: 12 }}>
                Top Up
              </button>
              <button type="button" onClick={() => setShowLowBalanceWarning(false)} style={{ color: '#6B1020', fontFamily: 'Inter', fontSize: 16 }}>
                ✕
              </button>
            </div>
          </div>
        </div>
      )}

      {showTopUpModal && (
        <div className="fixed inset-0 z-[60] flex items-end justify-center">
          <div className="absolute inset-0 bg-black/50" style={{ backdropFilter: 'blur(4px)' }} />
          <div className="relative rounded-t-2xl p-6 w-full max-w-lg animate-slide-up" style={{ background: '#FAF7F0', boxShadow: '0 -8px 40px rgba(107,16,32,0.15)' }}>
            <div className="text-center">
              <div style={{ fontSize: 32 }}>⏸</div>
              <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 26, color: '#6B1020', marginTop: 3 }}>
                Reading Paused
              </div>
              <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 16, color: '#7A5C62', marginTop: 2 }}>
                You've used all your reading time.
              </p>
              <p style={{ fontFamily: 'Inter', fontSize: 12, color: '#D4A843', marginTop: 1, marginBottom: 20 }}>
                Your place is saved — top up to continue from where you left off.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {topUpPacks.map((pack, index) => {
                const selected = index === selectedPack;
                const price = pack.price ?? pack.price_inr;
                return (
                  <div key={pack._id || pack.id} onClick={() => setSelectedPack(index)} className="rounded-xl p-4 cursor-pointer transition-all" style={{ borderWidth: 2, borderStyle: 'solid', borderColor: selected ? '#6B1020' : '#E8DDD8', background: selected ? 'rgba(107,16,32,0.06)' : 'white' }}>
                    <div className="flex justify-between items-center gap-3">
                      <div>
                        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 17, color: '#1C0A0E' }}>
                          {pack.minutes} min
                        </div>
                        {pack.label && (
                          <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F' }}>
                            {pack.label}
                          </div>
                        )}
                      </div>
                      <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 20, color: '#6B1020' }}>
                        ₹{price}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <button type="button" onClick={() => handleTopUp(topUpPacks[selectedPack])} disabled={topUpProcessing || !topUpPacks[selectedPack]} className="w-full mt-4 rounded-xl py-3 flex items-center justify-center gap-2" style={{ background: '#6B1020', color: '#FAF7F0', fontFamily: 'Inter', fontSize: 15, fontWeight: 500, opacity: topUpProcessing ? 0.7 : 1 }}>
              {topUpProcessing && <Loader2 className="animate-spin" size={16} />}
              Complete Payment →
            </button>
            <button type="button" onClick={() => setShowTopUpModal(false)} className="w-full mt-3 text-center" style={{ fontFamily: 'Inter', fontSize: 12, color: '#A88A8F' }}>
              I'll top up later
            </button>
          </div>
        </div>
      )}

      {showTopUpSuccess && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center animate-fade-in" style={{ background: 'rgba(250,247,240,0.96)', backdropFilter: 'blur(8px)' }}>
          <div className="flex flex-col items-center gap-4">
            <div className="rounded-full w-16 h-16 bg-[#6B1020] flex items-center justify-center">
              <span style={{ color: 'white', fontSize: 24 }}>✓</span>
            </div>
            <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, color: '#6B1020' }}>
              {topUpSuccessMinutes} minutes added
            </div>
            <div style={{ fontFamily: 'Inter', fontSize: 13, color: '#A88A8F' }}>
              Resuming your chapter…
            </div>
          </div>
        </div>
      )}

      {showSettings && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 rounded-2xl p-5 w-80 shadow-book animate-slide-up" style={{ background: colors.surface, border: `1px solid ${colors.border}` }}>
          <div className="flex justify-between items-center mb-4">
            <span style={{ fontFamily: 'Inter', fontSize: 13, fontWeight: 500, color: colors.text }}>
              Reading Settings
            </span>
            <button type="button" onClick={() => setShowSettings(false)} aria-label="Close reading settings">
              <X size={16} color="#A88A8F" />
            </button>
          </div>

          <div className="mb-4">
            <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F', marginBottom: 8 }}>
              Font Size
            </div>
            <div className="flex gap-2">
              {FONT_SIZES.map((font, index) => {
                const active = fontSizeIdx === index;
                return (
                  <button key={font.label} type="button" onClick={() => setFontSizeIdx(index)} className="flex-1 py-2 rounded-lg" style={{ background: active ? '#6B1020' : colors.canvas, color: active ? '#FAF7F0' : colors.text, border: active ? 'none' : `1px solid ${colors.border}`, fontFamily: 'Inter', fontSize: 12, fontWeight: 500 }}>
                    {font.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mb-4">
            <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F', marginBottom: 8 }}>
              Theme
            </div>
            <div className="flex gap-2">
              {Object.entries(THEMES).map(([key, item]) => {
                const active = theme === key;
                return (
                  <button key={key} type="button" onClick={() => setTheme(key)} className="flex-1 py-2 rounded-lg capitalize" style={{ background: item.canvas, color: item.text, border: active ? '2px solid #6B1020' : `1px solid ${colors.border}`, fontFamily: 'Inter', fontSize: 11 }}>
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F', marginBottom: 8 }}>
              Speed: {ttsSpeed}×
            </div>
            <input type="range" min="0.7" max="1.8" step="0.1" value={ttsSpeed} onChange={(event) => { setTtsSpeed(parseFloat(event.target.value)); if (ttsActive) { stopTTS(); setTimeout(startTTS, 150); } }} style={{ accentColor: '#6B1020', width: '100%' }} />
          </div>
        </div>
      )}

      {showTOC && (
        <div className="fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/40" style={{ backdropFilter: 'blur(4px)' }} onClick={() => setShowTOC(false)} />
          <div className="relative right-0 ml-auto w-72 h-full overflow-y-auto py-6 px-5 animate-slide-up" style={{ background: colors.surface }}>
            <div className="flex justify-between items-center mb-6">
              <span style={{ fontFamily: isBengali ? BENGALI_SERIF : READER_DISPLAY, fontSize: 20, color: colors.text }}>
                Contents
              </span>
              <button type="button" onClick={() => setShowTOC(false)} aria-label="Close contents">
                <X size={18} color="#A88A8F" />
              </button>
            </div>

            <div className="space-y-1">
              {chapters.map((item, index) => {
                const current = index === currentIdx;
                return (
                  <button key={item.id} type="button" onClick={() => { setShowTOC(false); goToChapter(item.id); }} className="w-full text-left px-3 py-2.5 rounded-lg transition-all" lang={containsBengaliText(item.title) ? 'bn' : undefined} style={{ background: current ? 'rgba(107,16,32,0.08)' : 'transparent', borderLeft: current ? '2px solid #6B1020' : '2px solid transparent', color: current ? '#6B1020' : colors.text, fontFamily: containsBengaliText(item.title) ? BENGALI_SERIF : READER_SERIF, fontSize: 15, overflowWrap: 'break-word' }}>
                    <span style={{ fontFamily: UI_FONT, fontSize: 11, color: '#A88A8F', marginRight: 6 }}>
                      {index + 1}.
                    </span>
                    {item.title}
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
