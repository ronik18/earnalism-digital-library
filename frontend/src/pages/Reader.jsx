import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Play, Pause, Square, Bookmark, BookmarkCheck, Settings, List, X, Loader2, Clock, AlertCircle, LogIn, CreditCard } from 'lucide-react';
import axios from 'axios';
import { API, TOKEN_KEY, USER_TOKEN_KEY, formatError } from '../lib/api';
import { toast } from 'sonner';
import ReaderUpsellPrompt from '../components/Funnel/ReaderUpsellPrompt';
import SecureReader from '../components/SecureReader';
import { trackFunnelEvent } from '../lib/funnelAnalytics';
import { canShowReaderFinishPrompt, markReaderFinishPromptShown } from '../lib/funnelOffers';
import { useAuth } from '../context/AuthContext';

const THEMES = {
  beige: { canvas: '#F5F0E8', surface: '#FDFAF4', text: '#2C1810', accent: '#6B1E2E', border: '#E8D5A3', label: 'Light' },
  sepia: { canvas: '#EDE0C8', surface: '#F5E8D0', text: '#3B2A1A', accent: '#6B1E2E', border: '#D7BD7A', label: 'Sepia' },
  dark: { canvas: '#1A0E12', surface: '#240D14', text: '#E8D5A3', accent: '#C9A84C', border: 'rgba(201,168,76,0.32)', label: 'Dark' },
};

const BENGALI_RE = /[\u0980-\u09FF]/;
const READER_SERIF = "'Lora', Georgia, serif";
const READER_DISPLAY = "'Playfair Display', 'Noto Serif Bengali', serif";
const BENGALI_SERIF = "'Noto Serif Bengali', 'Lora', Georgia, serif";
const BENGALI_SANS = "'Noto Sans Bengali', Inter, sans-serif";
const UI_FONT = "Inter, 'Noto Sans Bengali', sans-serif";

const FONT_SIZES = [
  { label: 'Small', size: '16px' },
  { label: 'Medium', size: '18px' },
  { label: 'Large', size: '20px' },
  { label: 'XL', size: '22px' },
];

const LINE_SPACING_OPTIONS = [
  { label: 'Comfortable', value: 'comfortable', english: 1.75, bengali: 1.9 },
  { label: 'Relaxed', value: 'relaxed', english: 1.9, bengali: 2.05 },
  { label: 'Airy', value: 'airy', english: 2.05, bengali: 2.2 },
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

function normalizeInlineText(value = '') {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function textEquals(value, candidates = []) {
  const normalized = normalizeInlineText(value);
  return candidates.some((candidate) => normalizeInlineText(candidate) === normalized);
}

function looksLikePublicationYear(value = '') {
  return /(?:\d{4}|[০-৯]{4})/.test(value) && normalizeInlineText(value).length <= 48;
}

function firstParagraphText(html = '') {
  if (typeof document === 'undefined') return '';
  const template = document.createElement('template');
  template.innerHTML = html || '';
  const first = template.content.querySelector('p, h1, h2, h3, div');
  return normalizeInlineText(first?.textContent || '');
}

function extractReaderFrontMatter(html = '', book = {}, chapter = {}) {
  if (typeof document === 'undefined') {
    return {
      html,
      author: book?.author || '',
      collection: book?.collection || '',
      year: book?.original_publication_year || '',
      storyTitle: book?.title || chapter?.title || '',
    };
  }

  const template = document.createElement('template');
  template.innerHTML = html || '';
  const author = book?.author || '';
  const title = book?.title || chapter?.title || '';
  const subtitle = book?.subtitle || '';
  let collection = book?.collection || book?.series || '';
  let year = book?.original_publication_year || book?.publication_year || '';
  let storyTitle = title;

  const leadingNodes = Array.from(template.content.childNodes)
    .filter((node) => node.nodeType === Node.ELEMENT_NODE || normalizeInlineText(node.textContent));

  for (const node of leadingNodes.slice(0, 8)) {
    const text = normalizeInlineText(node.textContent || '');
    if (!text) {
      node.remove();
      continue;
    }

    const shouldRemoveAuthor = author && textEquals(text, [author]);
    const shouldRemoveTitle = title && textEquals(text, [title, chapter?.title]);
    const shouldRemoveSubtitle = subtitle && textEquals(text, [subtitle]);
    const shouldRemoveYear = looksLikePublicationYear(text);
    const shouldUseAsCollection = !collection
      && text.length <= 42
      && !shouldRemoveAuthor
      && !shouldRemoveTitle
      && !shouldRemoveYear
      && containsBengaliText(text);

    if (shouldRemoveAuthor) {
      node.remove();
      continue;
    }
    if (shouldUseAsCollection) {
      collection = text;
      node.remove();
      continue;
    }
    if (shouldRemoveYear) {
      year = year || text;
      node.remove();
      continue;
    }
    if (shouldRemoveTitle || shouldRemoveSubtitle) {
      storyTitle = title || text;
      node.remove();
      continue;
    }
    break;
  }

  return {
    html: template.innerHTML,
    author,
    collection,
    year,
    storyTitle: storyTitle || firstParagraphText(html) || 'Chapter',
    subtitle: subtitle && !textEquals(subtitle, [collection]) ? subtitle : '',
  };
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

function wrapWordsInSpans(html, startWordIndex = 0) {
  if (typeof document === 'undefined') return { html: html || '', totalWords: 0 };
  const div = document.createElement('div');
  div.innerHTML = html || '';
  let wordIndex = startWordIndex;
  let wrappedWords = 0;
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
        nextHtml += escapeHtmlText(text.slice(lastIndex, match.index));
        for (const part of highlightTokenParts(match[0])) {
          const start = textOffset + match.index + part.index;
          const end = start + part.text.length;
          if (part.highlight) {
            nextHtml += `<span class="tts-word" data-word="${wordIndex}" data-start="${start}" data-end="${end}">${escapeHtmlText(part.text)}</span>`;
            wordIndex += 1;
            wrappedWords += 1;
          } else {
            nextHtml += escapeHtmlText(part.text);
          }
        }
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
  return { html: div.innerHTML, totalWords: wrappedWords };
}

function textSegments(text = '') {
  const source = String(text || '');
  if (!source.trim()) return [];
  const segments = [];
  const re = /[^।.!?;:]+[।.!?;:]?|[^।.!?;:]+$/g;
  let match;
  while ((match = re.exec(source)) !== null) {
    const raw = match[0].trim();
    if (!raw) continue;
    const start = match.index + match[0].indexOf(raw);
    const end = start + raw.length;
    const words = raw.split(/\s+/).filter(Boolean);
    if (words.length > 42) {
      let cursor = start;
      for (let index = 0; index < words.length; index += 32) {
        const part = words.slice(index, index + 32).join(' ');
        const partStart = source.indexOf(words[index], cursor);
        const partEnd = partStart >= 0 ? partStart + part.length : end;
        segments.push({ text: part, start: partStart >= 0 ? partStart : start, end: partEnd, pauseMs: 180 });
        cursor = partEnd;
      }
    } else {
      const punct = raw.slice(-1);
      const pauseMs = /[।.!?]/.test(punct) ? 520 : /[,;:]/.test(punct) ? 280 : 180;
      segments.push({ text: raw, start, end, pauseMs });
    }
  }
  const trimmed = source.trim();
  return segments.length ? segments : [{ text: trimmed, start: source.indexOf(trimmed), end: source.indexOf(trimmed) + trimmed.length, pauseMs: 240 }];
}

function countWordsInHtml(html) {
  if (typeof document === 'undefined') return countHighlightUnitsInText(html || '');
  const div = document.createElement('div');
  div.innerHTML = html || '';
  return countHighlightUnitsInText(div.textContent || '');
}

function isHighlightableToken(token = '') {
  return /[\p{L}\p{N}\u0980-\u09FF]/u.test(token);
}

function highlightTokenParts(token = '') {
  if (/^\d{1,3}(?:,\d{3})+(?:[^\p{L}\p{N}\u0980-\u09FF]*)$/u.test(token)) {
    const parts = [];
    const re = /\d+|\D+/g;
    let match;
    while ((match = re.exec(token)) !== null) {
      parts.push({
        text: match[0],
        index: match.index,
        highlight: /\d/.test(match[0]),
      });
    }
    return parts;
  }
  return [{ text: token, index: 0, highlight: isHighlightableToken(token) }];
}

function countHighlightUnitsInText(text = '') {
  return (text.match(/\S+/g) || []).reduce((count, token) => {
    return count + highlightTokenParts(token).filter((part) => part.highlight).length;
  }, 0);
}

function readerCoverUrl(book = {}, kind = 'front') {
  return kind === 'back'
    ? (book?.back_cover_image_url || book?.back_cover_url || '')
    : (book?.cover_image_url || book?.cover_url || '');
}

function referencePageKind(html = '') {
  if (/<h[1-6][^>]*>\s*Index\s*<\/h[1-6]>/i.test(html)) return 'index';
  if (/<h[1-6][^>]*>\s*Bibliography\s*<\/h[1-6]>/i.test(html)) return 'reference';
  return '';
}

function audioAssetSlugForBook(book, bookId) {
  const configured = book?.audio_slug || book?.audio_asset_slug || book?.audioAssetSlug;
  if (configured) return configured;
  if (bookId === 'book-d19e96859f' || book?.title === 'গিন্নি') return 'ginni';
  if (bookId === 'bharat-at-the-crossroads' || /bharat at the crossroads/i.test(book?.title || '')) return 'bharat-at-the-crossroads';
  return book?.slug || bookId || '';
}

function rightsForBook(book = {}, userName = 'Reader') {
  const title = book?.title || '';
  if (/bharat at the crossroads/i.test(title) || book?.slug === 'bharat-at-the-crossroads') {
    return {
      licenseMetadata: 'Bharat at the Crossroads - Original Earnalism Digital Edition',
      licenseNotice: 'Bharat at the Crossroads is an original work authored by Ronik Basak. Copyright 2026 Reo Enterprise. This reading copy is licensed for lawful personal reading only; redistribution, scraping, recording, or reproduction is prohibited without prior written permission.',
      watermarkText: `Bharat at the Crossroads - Reo Enterprise - Licensed for ${userName || 'Reader'}`,
      footerText: `Licensed reading copy for ${userName || 'Reader'} - Copyright 2026 Reo Enterprise. Author: Ronik Basak. Redistribution prohibited.`,
    };
  }
  return {};
}

function timestampIndexAt(timestamps = [], nowMs = 0) {
  if (!timestamps.length) return -1;
  let lo = 0;
  let hi = timestamps.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if ((timestamps[mid]?.start_ms || 0) <= nowMs) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

function splitParagraphNode(node) {
  const text = (node.textContent || '').trim();
  if (!text || text.length < 600) return [node];
  const chunks = [];
  let buffer = [];
  textSegments(text).forEach((segment) => {
    buffer.push(segment.text);
    if (buffer.join(' ').length >= 520) {
      chunks.push(buffer.join(' '));
      buffer = [];
    }
  });
  if (buffer.length) chunks.push(buffer.join(' '));
  return chunks.map((chunk) => {
    const next = document.createElement(node.nodeName.toLowerCase());
    next.textContent = chunk;
    return next;
  });
}

function measurePageHeight() {
  if (typeof window === 'undefined') return 760;
  return Math.max(440, Math.min(780, window.innerHeight - 245));
}

function paginateReaderHtml(html, { isBengali = false, fontSize = '17px' } = {}) {
  if (typeof document === 'undefined' || !html) return [];
  const template = document.createElement('template');
  template.innerHTML = html;

  const measure = document.createElement('div');
  measure.className = `reader-content ${isBengali ? 'reader-content--bengali' : ''}`;
  measure.style.cssText = [
    'position:absolute',
    'left:-10000px',
    'top:0',
    'visibility:hidden',
    `width:${Math.max(300, Math.min(window.innerWidth - 72, 680))}px`,
    `font-size:${fontSize}`,
    `font-family:${isBengali ? BENGALI_SERIF : READER_SERIF}`,
    `line-height:${isBengali ? 1.9 : 1.75}`,
    'box-sizing:border-box',
    'padding:0',
  ].join(';');
  document.body.appendChild(measure);

  const limit = measurePageHeight();
  const pages = [];
  let pageNodes = [];

  const commitPage = () => {
    if (!pageNodes.length) return;
    pages.push({ html: pageNodes.map((node) => node.outerHTML || node.textContent || '').join('') });
    pageNodes = [];
    measure.innerHTML = '';
  };

  const sourceNodes = Array.from(template.content.childNodes)
    .flatMap((node) => (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'P' ? splitParagraphNode(node) : [node]))
    .filter((node) => (node.textContent || '').trim() || node.nodeType === Node.ELEMENT_NODE);

  sourceNodes.forEach((node) => {
    const candidate = node.cloneNode(true);
    measure.appendChild(candidate);
    if (measure.scrollHeight > limit && pageNodes.length) {
      measure.removeChild(candidate);
      commitPage();
      measure.appendChild(candidate);
    }
    pageNodes.push(candidate.cloneNode(true));
  });

  commitPage();
  document.body.removeChild(measure);
  return pages.length ? pages : [{ html }];
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
  const [fontSizeIdx, setFontSizeIdx] = useState(2);
  const [lineSpacingMode, setLineSpacingMode] = useState('relaxed');
  const [fontFamilyMode, setFontFamilyMode] = useState('sans');
  const [showSettings, setShowSettings] = useState(false);
  const [showTOC, setShowTOC] = useState(false);
  const [toolbarVisible, setToolbarVisible] = useState(true);
  const [bookmarked, setBookmarked] = useState(false);

  const [ttsActive, setTtsActive] = useState(false);
  const [ttsPaused, setTtsPaused] = useState(false);
  const [ttsWordIndex, setTtsWordIndex] = useState(-1);
  const [ttsSpeed, setTtsSpeed] = useState(0.85);
  const [ttsVoices, setTtsVoices] = useState([]);
  const [generatedAudioAvailable, setGeneratedAudioAvailable] = useState(false);
  const [generatedAudioActive, setGeneratedAudioActive] = useState(false);
  const [processedHtml, setProcessedHtml] = useState('');
  const [ttsHtml, setTtsHtml] = useState('');
  const [totalWords, setTotalWords] = useState(0);
  const [paginatedPages, setPaginatedPages] = useState([]);
  const [currentPage, setCurrentPage] = useState(0);

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
  const generatedAudioRef = useRef(null);
  const generatedTimestampsRef = useRef([]);
  const generatedPageEndRef = useRef(null);
  const generatedHighlightTimerRef = useRef(null);
  const utteranceRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);
  const lastScrollY = useRef(0);
  const wordsRef = useRef([]);
  const ttsFallbackTimerRef = useRef(null);
  const ttsSegmentTimerRef = useRef(null);
  const pulseIntervalRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const completionReportedRef = useRef('');
  const upsellShownRef = useRef('');
  const ttsWarningShownRef = useRef(false);

  const stopTTS = useCallback(() => {
    synthRef.current?.cancel?.();
    const audio = generatedAudioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    generatedPageEndRef.current = null;
    clearInterval(generatedHighlightTimerRef.current);
    clearTimeout(ttsFallbackTimerRef.current);
    clearTimeout(ttsSegmentTimerRef.current);
    setTtsActive(false);
    setTtsPaused(false);
    setGeneratedAudioActive(false);
    setTtsWordIndex(-1);
    setTtsHtml('');
    wordsRef.current.forEach((word) => word.classList.remove('active', 'tts-word--fallback'));
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
        setTtsHtml('');
        setCurrentPage(0);
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

  const isBengali = useMemo(
    () => containsBengaliText(`${book?.title || ''} ${chapter?.title || ''} ${processedHtml || ''}`),
    [book, chapter, processedHtml],
  );
  const readerFrontMatter = useMemo(
    () => extractReaderFrontMatter(processedHtml, book, chapter),
    [book, chapter, processedHtml],
  );
  const readerHtml = readerFrontMatter.html || processedHtml;
  const lineSpacing = LINE_SPACING_OPTIONS.find((item) => item.value === lineSpacingMode) || LINE_SPACING_OPTIONS[0];
  const readerFontFamily = fontFamilyMode === 'sans'
    ? (isBengali ? BENGALI_SANS : UI_FONT)
    : (isBengali ? BENGALI_SERIF : READER_SERIF);
  const readerDisplayTitle = book?.title || readerFrontMatter.storyTitle || chapter?.title || 'Chapter';

  useEffect(() => {
    if (meteredSessionActive && chapter && processedHtml && sessionId) {
      clearInterval(pulseIntervalRef.current);
      pulseIntervalRef.current = setInterval(sendPulse, 30000);
    }

    return () => clearInterval(pulseIntervalRef.current);
  }, [chapter, processedHtml, sessionId, meteredSessionActive, sendPulse]);

  useEffect(() => {
    if (!readerHtml) {
      setPaginatedPages([]);
      setCurrentPage(0);
      return undefined;
    }

    let cancelled = false;
    let resizeTimer = 0;
    const runPagination = () => {
      const contentPages = paginateReaderHtml(readerHtml, {
        isBengali,
        fontSize: FONT_SIZES[fontSizeIdx].size,
      });
      let referenceKind = '';
      const readerPages = contentPages.map((page, index) => {
        const detectedReferenceKind = referencePageKind(page.html || '');
        if (!referenceKind && detectedReferenceKind) referenceKind = detectedReferenceKind;
        if (referenceKind === 'reference' && detectedReferenceKind === 'index') referenceKind = 'index';
        return {
          ...page,
          type: referenceKind || 'content',
          contentIndex: referenceKind ? null : index,
        };
      });
      const frontCover = readerCoverUrl(book, 'front');
      const backCover = readerCoverUrl(book, 'back');
      const nextPages = [
        ...(frontCover ? [{ type: 'front-cover', imageUrl: frontCover, html: '' }] : []),
        ...readerPages,
        ...(backCover ? [{ type: 'back-cover', imageUrl: backCover, html: '' }] : []),
      ];
      if (cancelled) return;
      setPaginatedPages(nextPages);
      setCurrentPage((page) => Math.min(page, Math.max(0, nextPages.length - 1)));
    };
    const onResize = () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(runPagination, 120);
    };

    window.setTimeout(runPagination, 60);
    window.addEventListener('resize', onResize);
    return () => {
      cancelled = true;
      window.clearTimeout(resizeTimer);
      window.removeEventListener('resize', onResize);
    };
  }, [book, fontSizeIdx, isBengali, readerHtml]);

  const currentPageData = paginatedPages.length ? paginatedPages[currentPage] : { type: 'content', html: readerHtml, contentIndex: 0 };
  const isContentPage = !paginatedPages.length || currentPageData?.type === 'content';
  const isIndexPage = currentPageData?.type === 'index';
  const isReferencePage = currentPageData?.type === 'reference' || isIndexPage;
  const currentPageHtml = (isContentPage || isReferencePage) ? (currentPageData?.html || readerHtml) : '';
  const displayedHtml = ttsHtml || currentPageHtml;
  const pageWordOffsets = useMemo(() => {
    let cursor = 0;
    return paginatedPages.map((page) => {
      const start = cursor;
      if (page.type === 'content') cursor += countWordsInHtml(page.html || '');
      return start;
    });
  }, [paginatedPages]);
  const currentPageWordOffset = paginatedPages.length ? (pageWordOffsets[currentPage] || 0) : 0;
  const effectiveReadProgress = paginatedPages.length > 1
    ? Math.round(((currentPage + 1) / paginatedPages.length) * 100)
    : readProgress;
  const generatedAudioSlug = useMemo(
    () => audioAssetSlugForBook(book, bookId),
    [book, bookId],
  );
  const generatedAudioLang = isBengali ? 'ben' : 'en';

  useEffect(() => {
    let cancelled = false;
    generatedTimestampsRef.current = [];
    setGeneratedAudioAvailable(false);
    setGeneratedAudioActive(false);
    if (!generatedAudioSlug || !processedHtml || lockedState) return undefined;

    fetch(`/audio/${generatedAudioLang}/${generatedAudioSlug}_timestamps.json`, { cache: 'force-cache' })
      .then((response) => {
        if (!response.ok) throw new Error('Generated audio timestamps unavailable');
        return response.json();
      })
      .then((timestamps) => {
        if (cancelled) return;
        if (Array.isArray(timestamps) && timestamps.length > 0) {
          generatedTimestampsRef.current = timestamps;
          setGeneratedAudioAvailable(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          generatedTimestampsRef.current = [];
          setGeneratedAudioAvailable(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [generatedAudioLang, generatedAudioSlug, lockedState, processedHtml]);

  useEffect(() => {
    setTtsHtml('');
    setTotalWords(countWordsInHtml(currentPageHtml));
  }, [currentPageHtml]);

  useEffect(() => {
    wordsRef.current = Array.from(contentRef.current?.querySelectorAll('.tts-word') || []);
  }, [displayedHtml]);

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
    if (!chapter || lockedState || loading || effectiveReadProgress < 96) return;
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
  }, [activeChapterId, bookId, chapter, chapterId, effectiveReadProgress, loading, lockedState, totalWords]);

  // Completion rewards are best-effort and idempotent; failures must not disturb reading.
  useEffect(() => {
    if (!chapter || lockedState || loading || effectiveReadProgress < 98 || !getUserToken()) return;
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
            progress: effectiveReadProgress,
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
  }, [activeChapterId, bookId, chapter, chapterId, effectiveReadProgress, loading, lockedState]);

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

  const highlightSpokenWord = useCallback((index) => {
    wordsRef.current.forEach((word) => word.classList.remove('active', 'tts-word--fallback'));
    const current = wordsRef.current[index];
    if (!current) return;

    current.classList.add('active');
    current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTtsWordIndex(index);
  }, []);

  const highlightGeneratedWord = useCallback((globalIndex) => {
    if (!wordsRef.current.length && contentRef.current) {
      wordsRef.current = Array.from(contentRef.current.querySelectorAll('.tts-word') || []);
    }
    wordsRef.current.forEach((word) => word.classList.remove('active', 'tts-word--fallback'));
    let current = wordsRef.current.find((word) => Number(word.dataset.word) === globalIndex);
    if (!current && contentRef.current) {
      wordsRef.current = Array.from(contentRef.current.querySelectorAll('.tts-word') || []);
      current = wordsRef.current.find((word) => Number(word.dataset.word) === globalIndex);
    }
    if (!current) return;

    current.classList.add('active');
    current.scrollIntoView({ behavior: 'smooth', block: 'center' });
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

  const fallbackHighlightSegment = useCallback((segment) => {
    clearTimeout(ttsFallbackTimerRef.current);
    const inRange = wordsRef.current.filter((word) => {
      const start = Number(word.dataset.start);
      const end = Number(word.dataset.end);
      return Number.isFinite(start) && Number.isFinite(end) && start >= segment.start && end <= segment.end;
    });
    if (!inRange.length) return;
    let index = 0;
    const stepMs = Math.max(isBengali ? 520 : 380, (isBengali ? 690 : 520) / Math.max(0.65, ttsSpeed));
    const tick = () => {
      inRange.forEach((word) => word.classList.remove('active', 'tts-word--fallback'));
      const current = inRange[index];
      if (current) {
        current.classList.add('active', 'tts-word--fallback');
        current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTtsWordIndex(Number(current.dataset.word) || 0);
      }
      index += 1;
      if (index < inRange.length) {
        ttsFallbackTimerRef.current = window.setTimeout(tick, stepMs);
      }
    };
    tick();
  }, [isBengali, ttsSpeed]);

  const buildUtterance = useCallback((segment, onDone) => {
    if (typeof SpeechSynthesisUtterance === 'undefined') return null;
    const spokenText = String(segment?.text || '').trim();
    if (!spokenText) return null;

    const utter = new SpeechSynthesisUtterance(spokenText);
    utter.rate = isBengali ? Math.min(ttsSpeed, 0.88) : ttsSpeed;
    utter.pitch = isBengali ? 0.96 : 1;
    utter.volume = 1;
    utter.lang = isBengali ? 'bn-BD' : 'en-US';

    const voices = ttsVoices.length ? ttsVoices : (synthRef.current?.getVoices?.() || []);
    const preferred = selectNarrationVoice(voices, isBengali);

    if (preferred.voice) utter.voice = preferred.voice;
    if (isBengali && !preferred.exactLanguage && !ttsWarningShownRef.current) {
      ttsWarningShownRef.current = true;
      toast.warning('Bengali narration depends on your browser voice pack. If pronunciation sounds off, add a Bengali voice in system settings.');
    }

    let boundarySeen = false;
    ttsFallbackTimerRef.current = window.setTimeout(() => {
      if (!boundarySeen) fallbackHighlightSegment(segment);
    }, 850);

    utter.onboundary = (event) => {
      boundarySeen = true;
      clearTimeout(ttsFallbackTimerRef.current);
      if (event.name === 'word') {
        const index = wordIndexFromCharIndex(segment.start + (event.charIndex || 0));
        if (index >= 0) highlightSpokenWord(index);
        return;
      }

      const index = wordIndexFromCharIndex(segment.start + event.charIndex);
      if (index >= 0) {
        highlightSpokenWord(index);
      }
    };

    const resetTTS = () => {
      clearTimeout(ttsFallbackTimerRef.current);
      setTtsActive(false);
      setTtsPaused(false);
      setTtsWordIndex(-1);
      wordsRef.current.forEach((word) => word.classList.remove('active', 'tts-word--fallback'));
    };

    utter.onend = () => {
      clearTimeout(ttsFallbackTimerRef.current);
      onDone?.();
    };
    utter.onerror = (event) => {
      resetTTS();
      if (event.error && event.error !== 'interrupted' && event.error !== 'canceled') {
        toast.error('Audio reading could not start in this browser.');
      }
    };

    return utter;
  }, [fallbackHighlightSegment, highlightSpokenWord, isBengali, ttsSpeed, ttsVoices, wordIndexFromCharIndex]);

  const speakSegments = useCallback((segments, index = 0) => {
    const synth = synthRef.current;
    if (!segments[index]) {
      setTtsActive(false);
      setTtsPaused(false);
      setTtsWordIndex(-1);
      wordsRef.current.forEach((word) => word.classList.remove('active', 'tts-word--fallback'));
      return;
    }

    const segment = segments[index];
    const onDone = () => {
      ttsSegmentTimerRef.current = window.setTimeout(() => speakSegments(segments, index + 1), segment.pauseMs || 220);
    };
    const utter = buildUtterance(segment, onDone);
    if (!utter) return;
    utteranceRef.current = utter;
    synth.speak(utter);
    setTtsActive(true);
    setTtsPaused(false);
  }, [buildUtterance]);

  const startGeneratedAudio = useCallback(() => {
    const audio = generatedAudioRef.current;
    const timestamps = generatedTimestampsRef.current || [];
    const pageHtml = currentPageHtml || readerHtml;
    if (!isContentPage || !audio || !generatedAudioAvailable || !timestamps.length || !pageHtml) return false;

    synthRef.current?.cancel?.();
    const wrapped = wrapWordsInSpans(pageHtml, currentPageWordOffset);
    const firstWord = currentPageWordOffset;
    const lastWord = currentPageWordOffset + Math.max(0, wrapped.totalWords - 1);
    const firstTimestamp = timestamps[firstWord];
    if (!firstTimestamp) return false;

    generatedPageEndRef.current = lastWord;
    const tickGeneratedHighlight = () => {
      const audioIndex = timestampIndexAt(timestamps, Math.floor(audio.currentTime * 1000));
      const pageEnd = generatedPageEndRef.current;
      if (Number.isFinite(pageEnd) && audioIndex > pageEnd) {
        audio.pause();
        generatedPageEndRef.current = null;
        clearInterval(generatedHighlightTimerRef.current);
        setGeneratedAudioActive(false);
        setTtsActive(false);
        setTtsPaused(false);
        return false;
      }
      if (audioIndex >= currentPageWordOffset) {
        highlightGeneratedWord(audioIndex);
        return true;
      }
      return false;
    };
    setTtsHtml(wrapped.html);
    setTotalWords(wrapped.totalWords);
    setGeneratedAudioActive(true);
    setTtsActive(true);
    setTtsPaused(false);

    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        wordsRef.current = Array.from(contentRef.current?.querySelectorAll('.tts-word') || []);
        audio.currentTime = Math.max(0, (firstTimestamp.start_ms || 0) / 1000);
        clearInterval(generatedHighlightTimerRef.current);
        tickGeneratedHighlight();
        generatedHighlightTimerRef.current = window.setInterval(tickGeneratedHighlight, 140);
        audio.play().catch(() => {
          clearInterval(generatedHighlightTimerRef.current);
          setGeneratedAudioActive(false);
          setTtsActive(false);
          setTtsPaused(false);
          toast.error('Generated audiobook could not start in this browser.');
        });
      });
    });
    return true;
  }, [currentPageHtml, currentPageWordOffset, generatedAudioAvailable, highlightGeneratedWord, isContentPage, readerHtml]);

  const startTTS = useCallback(() => {
    if (!isContentPage) {
      toast.info('Audio is available on reading pages only.');
      return;
    }
    if (startGeneratedAudio()) return;

    const synth = synthRef.current;
    if (!synth?.speak || typeof SpeechSynthesisUtterance === 'undefined') {
      toast.error('Audio reading is not available in this browser.');
      return;
    }

    synth.cancel();
    const speak = () => {
      wordsRef.current = Array.from(contentRef.current?.querySelectorAll('.tts-word') || []);
      // Use textContent because TTS word offsets are generated from text nodes.
      // innerText inserts layout newlines, which breaks Bengali boundary matching.
      const plainText = contentRef.current?.textContent || '';
      const segments = textSegments(plainText);
      speakSegments(segments, 0);
    };

    const pageHtml = currentPageHtml || readerHtml;
    if (pageHtml && !pageHtml.includes('class="tts-word"')) {
      const wrapped = wrapWordsInSpans(pageHtml);
      setTtsHtml(wrapped.html);
      setTotalWords(wrapped.totalWords);
      window.requestAnimationFrame(() => window.requestAnimationFrame(speak));
      return;
    }

    speak();
  }, [currentPageHtml, isContentPage, readerHtml, speakSegments, startGeneratedAudio]);

  const pauseTTS = () => {
    clearTimeout(ttsFallbackTimerRef.current);
    clearInterval(generatedHighlightTimerRef.current);
    if (generatedAudioActive) {
      generatedAudioRef.current?.pause?.();
    } else {
      synthRef.current?.pause?.();
    }
    setTtsPaused(true);
  };

  const resumeTTS = () => {
    if (generatedAudioActive) {
      generatedAudioRef.current?.play?.().catch(() => toast.error('Generated audiobook could not resume.'));
    } else {
      synthRef.current?.resume?.();
    }
    setTtsPaused(false);
  };

  const syncGeneratedAudioHighlight = useCallback(() => {
    const audio = generatedAudioRef.current;
    const timestamps = generatedTimestampsRef.current || [];
    if (!audio || !timestamps.length) return false;

    const index = timestampIndexAt(timestamps, Math.floor(audio.currentTime * 1000));
    const pageEnd = generatedPageEndRef.current;
    if (Number.isFinite(pageEnd) && index > pageEnd) {
      audio.pause();
      generatedPageEndRef.current = null;
      setGeneratedAudioActive(false);
      setTtsActive(false);
      setTtsPaused(false);
      return false;
    }
    if (index >= currentPageWordOffset) {
      highlightGeneratedWord(index);
      return true;
    }
    return false;
  }, [currentPageWordOffset, highlightGeneratedWord]);

  const handleGeneratedAudioTimeUpdate = useCallback(() => {
    if (ttsPaused) return;
    syncGeneratedAudioHighlight();
  }, [syncGeneratedAudioHighlight, ttsPaused]);

  const handleGeneratedAudioEnded = useCallback(() => {
    generatedPageEndRef.current = null;
    clearInterval(generatedHighlightTimerRef.current);
    setGeneratedAudioActive(false);
    setTtsActive(false);
    setTtsPaused(false);
    setTtsWordIndex(-1);
  }, []);

  useEffect(() => {
    if (!ttsActive || ttsPaused) return undefined;
    let timerId = 0;
    const tick = () => {
      syncGeneratedAudioHighlight();
      timerId = window.setTimeout(tick, 140);
    };
    tick();
    return () => window.clearTimeout(timerId);
  }, [syncGeneratedAudioHighlight, ttsActive, ttsPaused]);

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
  const hasPages = paginatedPages.length > 1;
  const canPrev = hasPages ? currentPage > 0 : Boolean(prevChapter);
  const canNext = hasPages ? currentPage < paginatedPages.length - 1 : Boolean(nextChapter);
  const readerUserName = user && typeof user === 'object' ? user.name : 'Reader';
  const readerUserEmail = user && typeof user === 'object' ? user.email : '';
  const rightsCopy = rightsForBook(book, readerUserName);

  const goToChapter = (id) => {
    stopTTS();
    navigate(`/reader/${bookId}?c=${id}`);
  };

  const goPrev = () => {
    stopTTS();
    if (hasPages && currentPage > 0) {
      setCurrentPage((page) => Math.max(0, page - 1));
      scrollContainerRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }
    if (prevChapter) goToChapter(prevChapter.id);
  };

  const goNext = () => {
    stopTTS();
    if (hasPages && currentPage < paginatedPages.length - 1) {
      setCurrentPage((page) => Math.min(paginatedPages.length - 1, page + 1));
      scrollContainerRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }
    if (nextChapter) goToChapter(nextChapter.id);
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

  const colors = THEMES[theme];
  const lowBalance = walletSeconds > 0 && walletSeconds <= LOW_BALANCE_THRESHOLD;
  const voiceButtonLabel = !ttsActive
    ? (isBengali ? 'Listen in Bengali' : 'Listen')
    : ttsPaused ? 'Resume narration' : 'Pause narration';
  const showBookHeader = isContentPage && currentIdx <= 0 && currentPageData?.contentIndex === 0;
  const showStoryHeader = isContentPage && (!hasPages || currentPageData?.contentIndex === 0);
  const currentPageLabel = currentPageData?.type === 'front-cover'
    ? 'Front cover'
      : currentPageData?.type === 'back-cover'
        ? 'Back cover'
      : currentPageData?.type === 'index'
        ? 'Index'
        : currentPageData?.type === 'reference'
          ? 'Reference'
        : 'Generated reader pages';
  const audioDisabledForPage = !isContentPage;
  const readingMinutesLeft = hasPages
    ? Math.max(1, Math.ceil((paginatedPages.filter((page, index) => index >= currentPage && page.type === 'content').length || 1) / 2))
    : totalWords > 0
      ? Math.max(1, Math.ceil(((100 - effectiveReadProgress) / 100) * (totalWords / 220)))
      : null;
  const contentLineHeight = isBengali ? lineSpacing.bengali : lineSpacing.english;
  const readerThemeClass = `premium-reader premium-reader--${theme}`;
  const contentClassName = [
    'reader-content',
    isBengali ? 'reader-content--bengali' : 'reader-content--english',
    'reader-content--dropcap',
    fontFamilyMode === 'sans' ? 'reader-content--sans' : 'reader-content--serif',
  ].join(' ');

  return (
    <div
      ref={scrollContainerRef}
      className={readerThemeClass}
      data-reader-language={isBengali ? 'bn' : 'en'}
      style={{
        '--reader-font-size': FONT_SIZES[fontSizeIdx].size,
        '--reader-line-height': contentLineHeight,
        '--reader-body-font': readerFontFamily,
        '--reader-heading-font': isBengali ? BENGALI_SERIF : READER_DISPLAY,
        '--reader-canvas': colors.canvas,
        '--reader-surface': colors.surface,
        '--reader-ink': colors.text,
        '--reader-accent': colors.accent,
        '--reader-border': colors.border,
      }}
    >
      {generatedAudioSlug && (
        <audio
          ref={generatedAudioRef}
          src={generatedAudioAvailable ? `/audio/${generatedAudioLang}/${generatedAudioSlug}.mp3` : undefined}
          preload="metadata"
          onTimeUpdate={handleGeneratedAudioTimeUpdate}
          onEnded={handleGeneratedAudioEnded}
          style={{ display: 'none' }}
          data-testid="generated-audiobook"
        />
      )}

      <header className={`reader-topbar ${toolbarVisible ? 'reader-topbar--visible' : 'reader-topbar--hidden'}`}>
        <button type="button" onClick={() => navigate(`/book/${bookId}`)} className="reader-topbar__back" aria-label="Back to book">
          <ChevronLeft size={18} />
          <span>{readerDisplayTitle}</span>
        </button>

        <div className="reader-topbar__center">
          <strong>{hasPages ? `Page ${currentPage + 1} of ${paginatedPages.length}` : `Ch. ${Math.max(0, currentIdx) + 1} of ${chapters.length}`}</strong>
          <span>{chapter?.title && chapter.title !== 'Full Text' ? chapter.title : 'Reading edition'}</span>
        </div>

        <div className="reader-topbar__actions">
          {walletSeconds > 0 && (
            <div className={lowBalance ? 'reader-wallet reader-wallet--low' : 'reader-wallet'}>
              <Clock size={14} />
              {formatWalletTime(walletSeconds)}
            </div>
          )}
          <button type="button" onClick={toggleBookmark} className="reader-icon-button" aria-label={bookmarked ? 'Remove bookmark' : 'Bookmark chapter'}>
            {bookmarked ? <BookmarkCheck size={19} /> : <Bookmark size={19} />}
          </button>
          <button type="button" onClick={() => setShowTOC(true)} className="reader-icon-button" aria-label="Open contents">
            <List size={19} />
          </button>
          <button type="button" onClick={() => setShowSettings((value) => !value)} className="reader-icon-button" aria-label="Open reading settings">
            <Settings size={19} />
          </button>
        </div>
      </header>

      <main key={chapter?.id || chapterId || bookId} className="reader-main">
        <div className="reader-gutter reader-gutter--left" aria-hidden="true" />
        <article key={`${activeChapterId || chapterId || chapter?.id || bookId}:${currentPage}`} className="reader-canvas page-enter">
          <section className={bookmarked ? 'reader-page-shell reader-page-shell--bookmarked' : 'reader-page-shell'}>
            {showBookHeader && (
              <header className="reader-book-header">
                {readerFrontMatter.author && <div className="reader-book-header__author">{readerFrontMatter.author}</div>}
                {(readerFrontMatter.collection || readerFrontMatter.year) && (
                  <div className="reader-book-header__meta">
                    {readerFrontMatter.collection && <span>{readerFrontMatter.collection}</span>}
                    {readerFrontMatter.collection && readerFrontMatter.year && <span aria-hidden="true">—</span>}
                    {readerFrontMatter.year && <span>{readerFrontMatter.year}</span>}
                  </div>
                )}
                <div className="reader-ornament" aria-hidden="true">
                  <svg viewBox="0 0 180 22" role="img" focusable="false">
                    <path d="M6 11h56" />
                    <path d="M118 11h56" />
                    <path d="M90 3c9 8 9 8 0 16-9-8-9-8 0-16Z" />
                    <path d="M78 11c5-6 10-6 12 0-5 6-10 6-12 0Z" />
                    <path d="M102 11c-5-6-10-6-12 0 5 6 10 6 12 0Z" />
                  </svg>
                </div>
              </header>
            )}

            {showStoryHeader && (
              <header className="reader-story-header">
                <h1 lang={isBengali ? 'bn' : undefined}>{readerDisplayTitle}</h1>
                {readerFrontMatter.subtitle && <p>{readerFrontMatter.subtitle}</p>}
              </header>
            )}

            {hasPages && (
              <>
                <div className="reader-page-meta">{currentPageLabel} · {currentPage + 1} / {paginatedPages.length}</div>
                <nav className="reader-page-index" aria-label="Generated reader page index">
                  {paginatedPages.map((_, index) => (
                    <button
                      key={index}
                      type="button"
                      aria-current={index === currentPage ? 'page' : undefined}
                      onClick={() => {
                        stopTTS();
                        setCurrentPage(index);
                        scrollContainerRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
                      }}
                    >
                      {index + 1}
                    </button>
                  ))}
                </nav>
              </>
            )}

            {isContentPage || isReferencePage ? (
              <SecureReader
                sessionId={sessionId}
                userName={readerUserName}
                userEmail={readerUserEmail}
                bookSlug={bookId}
                chapterId={activeChapterId || chapterId || chapter?.id}
                title={`${book?.title || 'Earnalism'} · ${chapter?.title || 'Chapter'}${hasPages ? ` · page ${currentPage + 1}` : ''}`}
                contentRef={contentRef}
                className={contentClassName}
                html={displayedHtml}
                blurred={contentBlurred}
                lang={isBengali ? 'bn' : 'en'}
                licenseNotice={rightsCopy.licenseNotice}
                licenseMetadata={rightsCopy.licenseMetadata}
                watermarkText={rightsCopy.watermarkText}
                footerText={rightsCopy.footerText}
                style={{
                  fontFamily: readerFontFamily,
                  fontSize: FONT_SIZES[fontSizeIdx].size,
                  lineHeight: contentLineHeight,
                  color: colors.text,
                  transition: 'filter 300ms ease',
                  userSelect: 'none',
                  WebkitUserSelect: 'none',
                }}
              />
            ) : (
              <SecureReader
                sessionId={sessionId}
                userName={readerUserName}
                userEmail={readerUserEmail}
                bookSlug={bookId}
                chapterId={activeChapterId || chapterId || chapter?.id}
                title={`${book?.title || 'Earnalism'} · ${currentPageLabel}`}
                className="reader-cover-page"
                blurred={contentBlurred}
                licenseNotice={rightsCopy.licenseNotice}
                licenseMetadata={rightsCopy.licenseMetadata}
                watermarkText={rightsCopy.watermarkText}
                footerText={rightsCopy.footerText}
              >
                <figure>
                  <img src={currentPageData.imageUrl} alt={`${book?.title || 'Book'} ${currentPageLabel.toLowerCase()}`} />
                  <figcaption>{currentPageLabel}</figcaption>
                </figure>
              </SecureReader>
            )}
          </section>

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
        </article>
        <div className="reader-gutter reader-gutter--right" aria-hidden="true" />
      </main>

      <footer className={`reader-bottom-bar ${toolbarVisible ? 'reader-bottom-bar--visible' : 'reader-bottom-bar--hidden'}`}>
        <div className="reader-progress" aria-label={`Reading progress ${effectiveReadProgress}%`}>
          {readingMinutesLeft && <span className="reader-progress__time">~{readingMinutesLeft} min left</span>}
          <div className="reader-progress__track">
            <div className="reader-progress__fill" style={{ width: `${effectiveReadProgress}%` }}>
              <span className="reader-progress__thumb" />
            </div>
          </div>
        </div>

        <div className="reader-bottom-bar__controls">
          <button type="button" disabled={!canPrev} onClick={goPrev} className="reader-nav-button reader-nav-button--ghost">
            <ChevronLeft size={17} />
            <span>{hasPages ? 'Prev Page' : 'Prev'}</span>
          </button>

          <div className="reader-audio-control">
            <button type="button" onClick={handleVoiceToggle} disabled={audioDisabledForPage} className="reader-audio-button" aria-label={voiceButtonLabel}>
              {ttsActive && !ttsPaused ? (
                <>
                  <Pause size={17} />
                  <span>Pause</span>
                  <span className="reader-waveform" aria-hidden="true"><i /><i /><i /></span>
                </>
              ) : ttsActive && ttsPaused ? (
                <>
                  <Play size={17} />
                  <span>Resume</span>
                </>
              ) : (
                <>
                  <Play size={17} />
                  <span>Play</span>
                </>
              )}
            </button>
            {ttsActive && (
              <button type="button" onClick={stopTTS} className="reader-stop-button" aria-label="Stop narration">
                <Square size={12} />
                <span>Stop</span>
              </button>
            )}
            <span className="reader-audio-control__hint">
              {audioDisabledForPage
                ? 'Audio starts on reading pages'
                : generatedAudioAvailable
                ? (ttsActive && !ttsPaused ? 'Synced audiobook' : 'Synced audio ready')
                : (ttsActive && !ttsPaused ? 'Narrating' : 'Resume anytime')}
            </span>
          </div>

          <button type="button" disabled={!canNext} onClick={goNext} className="reader-nav-button reader-nav-button--ghost">
            <span>{hasPages ? 'Next Page' : 'Next'}</span>
            <ChevronRight size={17} />
          </button>
        </div>
      </footer>

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
        <div className="reader-settings-sheet" role="dialog" aria-modal="false" aria-label="Reading settings">
          <div className="reader-settings-sheet__handle" aria-hidden="true" />
          <div className="reader-settings-sheet__header">
            <span>Reading Settings</span>
            <button type="button" onClick={() => setShowSettings(false)} className="reader-icon-button" aria-label="Close reading settings">
              <X size={16} />
            </button>
          </div>

          <div className="reader-setting-group">
            <span className="reader-setting-label">Font size</span>
            <div className="reader-segmented-control">
              {FONT_SIZES.map((font, index) => (
                <button key={font.label} type="button" onClick={() => setFontSizeIdx(index)} aria-pressed={fontSizeIdx === index}>
                  {font.label}
                </button>
              ))}
            </div>
          </div>

          <div className="reader-setting-group">
            <span className="reader-setting-label">Line spacing</span>
            <div className="reader-segmented-control">
              {LINE_SPACING_OPTIONS.map((item) => (
                <button key={item.value} type="button" onClick={() => setLineSpacingMode(item.value)} aria-pressed={lineSpacingMode === item.value}>
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div className="reader-setting-group">
            <span className="reader-setting-label">Theme</span>
            <div className="reader-segmented-control reader-segmented-control--theme">
              {Object.entries(THEMES).map(([key, item]) => (
                <button key={key} type="button" onClick={() => setTheme(key)} aria-pressed={theme === key}>
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div className="reader-setting-group">
            <span className="reader-setting-label">Font</span>
            <div className="reader-segmented-control">
              <button type="button" onClick={() => setFontFamilyMode('serif')} aria-pressed={fontFamilyMode === 'serif'}>Serif</button>
              <button type="button" onClick={() => setFontFamilyMode('sans')} aria-pressed={fontFamilyMode === 'sans'}>Sans</button>
            </div>
          </div>

          <div className="reader-setting-group">
            <span className="reader-setting-label">Narration speed: {ttsSpeed}×</span>
            <input
              className="reader-range"
              type="range"
              min="0.7"
              max="1.8"
              step="0.1"
              value={ttsSpeed}
              onChange={(event) => {
                setTtsSpeed(parseFloat(event.target.value));
                if (ttsActive) {
                  stopTTS();
                  setTimeout(startTTS, 150);
                }
              }}
            />
          </div>
        </div>
      )}

      {showTOC && (
        <div className="fixed inset-0 z-[80] flex">
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
