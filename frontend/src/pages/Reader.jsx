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
import { DRACULA_CTA_EVENTS, LIVE_APPROVED_SLUG, normalizeChapterDisplayTitle } from '../lib/controlledLaunch';
import { useAuth } from '../context/AuthContext';
import { optimizedImageUrl } from '../lib/images';
import useSEO from '../hooks/useSEO';
import { canExposeAudiobookControls } from '../lib/audioReleaseSafety';

const THEMES = {
  beige: { canvas: '#F5F0E8', surface: '#FDFAF4', text: '#2C1810', accent: '#6B1E2E', border: '#E8D5A3', label: 'Light' },
  sepia: { canvas: '#EDE0C8', surface: '#F5E8D0', text: '#3B2A1A', accent: '#6B1E2E', border: '#D7BD7A', label: 'Sepia' },
  dark: { canvas: '#14090D', surface: '#250B13', text: '#D9C793', accent: '#CDB158', border: 'rgba(205,177,88,0.34)', label: 'Dark' },
};

const BENGALI_RE = /[\u0980-\u09FF]/;
const READER_SERIF = "'Lora', Georgia, serif";
const READER_DISPLAY = "'Playfair Display', 'Noto Serif Bengali', serif";
const BENGALI_SERIF = "'Noto Serif Bengali', 'Lora', Georgia, serif";
const BENGALI_SANS = "'Noto Sans Bengali', Inter, sans-serif";
const UI_FONT = "Inter, 'Noto Sans Bengali', sans-serif";
const AUDIO_ASSET_BASE_URL = (process.env.REACT_APP_AUDIO_ASSET_BASE_URL || '').replace(/\/+$/, '');
const READER_PREFETCH_CACHE_LIMIT = 18;
const readerChapterResponseCache = new Map();
const readerAssetPrefetchCache = new Map();

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
const READING_PULSE_MS = 30000;
const READER_IDLE_MS = 5 * 60 * 1000;

function isReaderVisible() {
  return document.visibilityState === 'visible' && !document.hidden;
}

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
  const token = localStorage.getItem(USER_TOKEN_KEY);
  return authHeaders(token);
}

function getCurrentReaderPath() {
  return `${window.location.pathname}${window.location.search}`;
}

function boundedCacheSet(cache, key, value, limit = READER_PREFETCH_CACHE_LIMIT) {
  if (!key) return;
  if (cache.has(key)) cache.delete(key);
  cache.set(key, value);
  while (cache.size > limit) {
    const oldest = cache.keys().next().value;
    cache.delete(oldest);
  }
}

function readerChapterCacheKey({ bookId, chapterId, version, adminPreview, token }) {
  return [
    bookId || '',
    chapterId || '',
    version || 'unversioned',
    adminPreview ? 'admin' : 'reader',
    token ? token.slice(-18) : 'guest',
  ].join(':');
}

function runWhenIdle(task) {
  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    return window.requestIdleCallback(task, { timeout: 1200 });
  }
  return window.setTimeout(task, 120);
}

function cancelIdleTask(id) {
  if (!id) return;
  if (typeof window !== 'undefined' && 'cancelIdleCallback' in window) {
    window.cancelIdleCallback(id);
  } else {
    window.clearTimeout(id);
  }
}

function resolveAssetUrl(url = '') {
  if (!url) return '';
  if (/^https?:\/\//i.test(url)) return url;
  if (url.startsWith('/')) return AUDIO_ASSET_BASE_URL ? `${AUDIO_ASSET_BASE_URL}${url}` : url;
  return url;
}

function readerNowMs() {
  return typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now();
}

function sendReaderMetric(event, payload = {}) {
  const body = JSON.stringify({
    event,
    route: getCurrentReaderPath(),
    ...payload,
  });
  const url = `${API}/reader/metrics`;
  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      if (navigator.sendBeacon(url, blob)) return;
    }
  } catch {
    // Fall through to fetch.
  }
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getChapterAuthHeaders() },
    body,
    keepalive: true,
  }).catch(() => {});
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

function normalizeAudioWord(value = '') {
  return String(value || '')
    .normalize('NFC')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\u0980-\u09FF]+/gu, '')
    .trim();
}

function highlightWordsFromHtml(html = '', limit = 32) {
  if (typeof document === 'undefined') return [];
  const div = document.createElement('div');
  div.innerHTML = html || '';
  const words = [];
  const tokens = div.textContent?.match(/\S+/g) || [];

  for (const token of tokens) {
    for (const part of highlightTokenParts(token)) {
      if (!part.highlight) continue;
      const normalized = normalizeAudioWord(part.text);
      if (normalized) words.push(normalized);
      if (words.length >= limit) return words;
    }
  }

  return words;
}

function audioWordFromTimestamp(item = {}) {
  return normalizeAudioWord(item.word || item.text || item.value || '');
}

function findTimestampWordOffset(timestamps = [], html = '') {
  const visibleWords = highlightWordsFromHtml(html, 96);
  if (!visibleWords.length || !timestamps.length) return 0;

  const audioWords = timestamps.map(audioWordFromTimestamp);
  const windowSize = Math.min(14, visibleWords.length, audioWords.length);
  const minimumScore = Math.max(4, Math.ceil(windowSize * 0.7));
  const maxVisibleStart = Math.min(80, Math.max(0, visibleWords.length - windowSize));
  const maxAudioStart = Math.min(80, Math.max(0, audioWords.length - windowSize));
  let bestOffset = 0;
  let bestScore = -1;

  for (let visibleStart = 0; visibleStart <= maxVisibleStart; visibleStart += 1) {
    for (let audioStart = 0; audioStart <= maxAudioStart; audioStart += 1) {
      if (audioWords[audioStart] !== visibleWords[visibleStart]) continue;
      let score = 0;
      for (let index = 0; index < windowSize; index += 1) {
        if (audioWords[audioStart + index] && audioWords[audioStart + index] === visibleWords[visibleStart + index]) {
          score += 1;
        }
      }
      if (score > bestScore) {
        bestScore = score;
        bestOffset = audioStart - visibleStart;
      }
      if (score === windowSize) break;
    }
    if (bestScore === windowSize) break;
  }

  return bestScore >= minimumScore ? bestOffset : 0;
}

function audiobookAssetsForBook(book = {}) {
  return book?.audiobook_assets || book?.audiobookAssets || book?.audio_assets || {};
}

function audioAssetUrl(book, lang, slug, suffix) {
  if (!slug) return '';
  const keyBySuffix = {
    '.mp3': 'mp3',
    '_timestamps.json': 'timestamps',
    '_highlight.vtt': 'vtt',
    '_chapters.json': 'chapters',
    '_meta.json': 'meta',
    '_manifest.json': 'manifest',
  };
  const mapped = audiobookAssetsForBook(book)?.[keyBySuffix[suffix]];
  if (mapped) return resolveAssetUrl(mapped);
  const path = `/audio/${lang}/${slug}${suffix}`;
  return AUDIO_ASSET_BASE_URL ? `${AUDIO_ASSET_BASE_URL}${path}` : path;
}

function readerCoverUrl(book = {}, kind = 'front') {
  const src = kind === 'back'
    ? (book?.back_cover_image_url || book?.back_cover_url || '')
    : (book?.cover_image_url || book?.cover_url || '');
  return optimizedImageUrl(src, { width: 1400 });
}

function referencePageKind(html = '') {
  if (/<h[1-6][^>]*>\s*Index\s*<\/h[1-6]>/i.test(html)) return 'index';
  if (/<h[1-6][^>]*>\s*Bibliography\s*<\/h[1-6]>/i.test(html)) return 'reference';
  return '';
}

function audioAssetSlugForBook(book, bookId) {
  const configured = book?.audio_slug || book?.audio_asset_slug || book?.audioAssetSlug;
  if (configured) return configured;
  if (bookId === 'bharat-at-the-crossroads' || /bharat at the crossroads/i.test(book?.title || '')) return 'bharat-at-the-crossroads';
  return book?.slug || bookId || '';
}

function normalizeReaderManifestResponse(data = {}) {
  if (!data?.book) return data;
  const book = {
    ...data.book,
    chapters: data.chapters || data.book.chapters || [],
    _readerManifest: {
      version: data.version || '',
      content_generation: data.content_generation,
      access: data.access || {},
      audio: data.audio || {},
      generated_at: data.generated_at || '',
    },
  };
  if (data.audio) {
    book.audiobook_assets = {
      ...(book.audiobook_assets || {}),
      ...(data.audio.assets || {}),
    };
    book.audio_asset_slug = data.audio.asset_slug || book.audio_asset_slug;
    book.audiobook_enabled = data.audio.enabled;
  }
  return book;
}

function chapterVersionFor(chapters = [], chapterId = '') {
  return (chapters || []).find((item) => item.id === chapterId)?.content_version || '';
}

function manifestAudioForBook(book = {}) {
  return book?._readerManifest?.audio || {};
}

function audioManifestUrlForBook(book, lang, slug) {
  const audio = manifestAudioForBook(book);
  const explicit = audio?.assets?.manifest || audiobookAssetsForBook(book)?.manifest;
  if (explicit) return resolveAssetUrl(explicit);
  return audioAssetUrl(book, lang, slug, '_manifest.json');
}

function normalizeAudioTrack(raw = {}, lang = 'en', slug = '') {
  const audioUrl = raw.audio_url || raw.audioUrl || raw.mp3 || raw.src || '';
  const timestampsUrl = raw.timestamps_url || raw.timestampsUrl || raw.timestamps || '';
  const chunks = Array.isArray(raw.chunks || raw.pages || raw.timestamp_chunks)
    ? (raw.chunks || raw.pages || raw.timestamp_chunks).map((chunk) => ({
      startWord: Number(chunk.start_word ?? chunk.startWord ?? chunk.word_start ?? 0) || 0,
      endWord: Number(chunk.end_word ?? chunk.endWord ?? chunk.word_end ?? Number.MAX_SAFE_INTEGER) || Number.MAX_SAFE_INTEGER,
      audioUrl: resolveAssetUrl(chunk.audio_url || chunk.audioUrl || audioUrl),
      timestampsUrl: resolveAssetUrl(chunk.timestamps_url || chunk.timestampsUrl || chunk.timestamps || timestampsUrl),
      version: chunk.version || chunk.hash || raw.version || '',
    })).filter((chunk) => chunk.timestampsUrl || chunk.audioUrl)
    : [];
  return {
    chapterId: raw.chapter_id || raw.chapterId || raw.id || '',
    startWord: Number(raw.start_word ?? raw.startWord ?? 0) || 0,
    endWord: Number(raw.end_word ?? raw.endWord ?? Number.MAX_SAFE_INTEGER) || Number.MAX_SAFE_INTEGER,
    audioUrl: resolveAssetUrl(audioUrl || `/audio/${lang}/${slug}.mp3`),
    timestampsUrl: resolveAssetUrl(timestampsUrl || `/audio/${lang}/${slug}_timestamps.json`),
    version: raw.version || raw.hash || '',
    chunks,
  };
}

function normalizeAudioManifest(raw = {}, lang = 'en', slug = '') {
  const tracks = raw.tracks || raw.chapters || raw.items || [];
  return {
    version: raw.version || raw.hash || '',
    tracks: Array.isArray(tracks) ? tracks.map((track) => normalizeAudioTrack(track, lang, slug)) : [],
  };
}

function selectAudioTrack({ manifest, chapterId, currentWordOffset = 0, legacyAudioUrl, legacyTimestampsUrl }) {
  const tracks = manifest?.tracks || [];
  const track = tracks.find((item) => item.chapterId && item.chapterId === chapterId) || tracks[0];
  if (track) {
    const chunk = (track.chunks || []).find((item) => currentWordOffset >= item.startWord && currentWordOffset <= item.endWord);
    return {
      audioUrl: chunk?.audioUrl || track.audioUrl,
      timestampsUrl: chunk?.timestampsUrl || track.timestampsUrl,
      startWord: chunk?.startWord ?? track.startWord ?? 0,
      endWord: chunk?.endWord ?? track.endWord ?? Number.MAX_SAFE_INTEGER,
      version: chunk?.version || track.version || manifest.version || '',
      chunked: Boolean(chunk || track.chunks?.length),
    };
  }
  return {
    audioUrl: legacyAudioUrl,
    timestampsUrl: legacyTimestampsUrl,
    startWord: 0,
    endWord: Number.MAX_SAFE_INTEGER,
    version: '',
    chunked: false,
  };
}

function hasLegacyGeneratedAudioAsset(book = {}, bookId = '') {
  return bookId === 'bharat-at-the-crossroads'
    || /bharat at the crossroads/i.test(book?.title || '');
}

function isAgenticAiWithPython(book = {}, bookId = '') {
  const identity = `${bookId || ''} ${book?.slug || ''} ${book?.title || ''}`.toLowerCase();
  return identity.includes('agentic-ai-with-python') || /agentic\s+ai\s+with\s+python/i.test(book?.title || '');
}

function isNarrationDisabledForBook(book = {}, bookId = '') {
  if (bookId === LIVE_APPROVED_SLUG || book?.slug === LIVE_APPROVED_SLUG) return true;
  if (isAgenticAiWithPython(book, bookId)) return true;
  if (!canExposeAudiobookControls(book)) return true;
  const assets = audiobookAssetsForBook(book);
  if (book?.audiobook_enabled === false && book?.generate_audiobook === false && !assets?.mp3 && !assets?.timestamps) return true;
  return book?.audiobook_enabled === false
    && book?.generate_audiobook === false
    && (book?.narration_enabled === false || book?.audio_disabled === true);
}

function hasGeneratedAudioEnabled(book = {}, bookId = '') {
  if (isNarrationDisabledForBook(book, bookId)) return false;
  if (!canExposeAudiobookControls(book)) return false;
  const assets = audiobookAssetsForBook(book);
  if (assets?.mp3 && assets?.timestamps) return true;
  if (book?.audio_slug || book?.audio_asset_slug || book?.audioAssetSlug) return true;
  return false;
}

function rightsForBook(book = {}, userName = 'Reader') {
  const title = book?.title || '';
  if (/bharat at the crossroads/i.test(title) || book?.slug === 'bharat-at-the-crossroads') {
    return {
      licenseMetadata: 'Bharat at the Crossroads - Original Earnalism Digital Edition',
      licenseNotice: 'Bharat at the Crossroads is an original work authored by Ronik Basak. Copyright 2026 Reo Enterprise. This reading copy is licensed for lawful personal reading only; redistribution, scraping, recording, or reproduction is prohibited without prior written permission.',
      watermarkText: `Bharat at the Crossroads - Reo Enterprise - Licensed for ${userName || 'Reader'}`,
      footerText: `© 2026 Reo Enterprise · Licensed copy · Redistribution prohibited`,
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

function timestampWordIndex(item = {}, fallbackIndex = 0) {
  const raw = item.word_index ?? item.wordIndex ?? item.index ?? item.global_word_index;
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallbackIndex;
}

function timestampArrayIndexForWord(timestamps = [], wordIndex = 0) {
  if (!timestamps.length) return -1;
  let lo = 0;
  let hi = timestamps.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (timestampWordIndex(timestamps[mid], mid) < wordIndex) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

function normalizeGeneratedTimestamps(raw, html = '', baseWord = 0) {
  const source = Array.isArray(raw) ? raw : (raw?.words || raw?.timestamps || raw?.items || []);
  if (!Array.isArray(source) || !source.length) return { words: [], offset: 0 };
  const offset = findTimestampWordOffset(source, html);
  const words = source.map((item, index) => ({
    ...item,
    _word_index: baseWord + index - offset,
  }));
  return { words, offset };
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

async function fetchReaderBook(bookId, requestedAdminPreview = false) {
  const encodedBookId = encodeURIComponent(bookId);
  const adminToken = localStorage.getItem(TOKEN_KEY);
  const manifestHeaders = requestedAdminPreview && adminToken ? getAdminAuthHeaders() : getChapterAuthHeaders();
  try {
    const manifestUrl = `${API}/reader/book/${encodedBookId}/manifest${requestedAdminPreview && adminToken ? '?preview=admin' : ''}`;
    const response = await axios.get(manifestUrl, { headers: manifestHeaders });
    response.adminPreview = Boolean(response.data?.access?.admin_preview);
    response.readerManifest = response.data;
    response.data = normalizeReaderManifestResponse(response.data);
    return response;
  } catch (err) {
    if (![401, 403, 404].includes(err.response?.status)) throw err;
    if (requestedAdminPreview && !adminToken) throw err;
  }

  if (requestedAdminPreview && adminToken) {
    const response = await axios.get(`${API}/admin/books/${encodedBookId}`, { headers: getAdminAuthHeaders() });
    response.adminPreview = true;
    return response;
  }

  try {
    const response = await axios.get(`${API}/books/${encodedBookId}`);
    response.adminPreview = false;
    return response;
  } catch (err) {
    throw err;
  }
}

function readerSearchParams({ chapterId, adminPreview } = {}) {
  const params = new URLSearchParams();
  if (chapterId) params.set('c', chapterId);
  if (adminPreview) params.set('preview', 'admin');
  const query = params.toString();
  return query ? `?${query}` : '';
}

async function fetchReaderChapter({ bookId, chapterId, adminPreview = false, version = '', useCache = true }) {
  const token = adminPreview ? localStorage.getItem(TOKEN_KEY) : localStorage.getItem(USER_TOKEN_KEY);
  const cacheKey = readerChapterCacheKey({ bookId, chapterId, version, adminPreview, token });
  if (useCache && readerChapterResponseCache.has(cacheKey)) {
    return readerChapterResponseCache.get(cacheKey);
  }
  const params = new URLSearchParams();
  if (version) params.set('v', version);
  if (adminPreview) params.set('preview', 'admin');
  const query = params.toString();
  const url = `${API}/reader/chapter/${encodeURIComponent(bookId)}/${encodeURIComponent(chapterId)}${query ? `?${query}` : ''}`;
  const promise = axios.get(url, { headers: adminPreview ? getAdminAuthHeaders() : getChapterAuthHeaders() })
    .then((response) => response.data);
  boundedCacheSet(readerChapterResponseCache, cacheKey, promise);
  try {
    const data = await promise;
    boundedCacheSet(readerChapterResponseCache, cacheKey, Promise.resolve(data));
    return data;
  } catch (err) {
    readerChapterResponseCache.delete(cacheKey);
    throw err;
  }
}

function prefetchAsset(url) {
  if (!url || readerAssetPrefetchCache.has(url)) return;
  const promise = fetch(url, { cache: 'force-cache', mode: /^https?:\/\//i.test(url) ? 'cors' : 'same-origin' })
    .then((response) => (response.ok ? response : Promise.reject(new Error('asset prefetch failed'))))
    .catch(() => null);
  boundedCacheSet(readerAssetPrefetchCache, url, promise, 32);
}

function ReaderChapterIndex({ chapters = [], currentChapterId = '', bookId = '', adminPreview = false, onChapterSelect }) {
  const sortedChapters = [...chapters].sort((a, b) => (a.order || 0) - (b.order || 0));

  return (
    <nav className="reader-index-page" aria-label="Book chapter index">
      <div className="reader-index-page__eyebrow">Contents</div>
      <h2>Jump to a chapter</h2>
      <ol>
        {sortedChapters.map((item, index) => {
          const isCurrent = item.id === currentChapterId;
          const href = `/reader/${bookId}${readerSearchParams({ chapterId: item.id, adminPreview })}`;
          return (
            <li key={item.id || item.title}>
              <a
                href={href}
                aria-current={isCurrent ? 'page' : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  onChapterSelect?.(item.id);
                }}
              >
                <span>{String(index + 1).padStart(2, '0')}</span>
                <strong>{normalizeChapterDisplayTitle(item.title)}</strong>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
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
  const [adminPreview, setAdminPreview] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [lockedState, setLockedState] = useState(null);

  const [theme, setTheme] = useState('dark');
  const [fontSizeIdx, setFontSizeIdx] = useState(0);
  const [lineSpacingMode, setLineSpacingMode] = useState('comfortable');
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
  const [generatedAudioManifest, setGeneratedAudioManifest] = useState(null);
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
  const generatedAudioWordOffsetRef = useRef(0);
  const generatedPageEndRef = useRef(null);
  const utteranceRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);
  const lastScrollY = useRef(0);
  const wordsRef = useRef([]);
  const wordMapRef = useRef(new Map());
  const activeWordRef = useRef(null);
  const highlightedWordIndexRef = useRef(-1);
  const generatedHighlightRafRef = useRef(0);
  const ttsFallbackTimerRef = useRef(null);
  const ttsSegmentTimerRef = useRef(null);
  const pulseIntervalRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const completionReportedRef = useRef('');
  const draculaChapterOneCompleteRef = useRef('');
  const readerStartedRef = useRef(false);
  const upsellShownRef = useRef('');
  const ttsWarningShownRef = useRef(false);
  const lastReaderActivityRef = useRef(Date.now());
  const readerMetricsRef = useRef({ loadStartedAt: 0, timings: {} });
  const audioIntentStartedAtRef = useRef(0);

  useSEO({
    title: notFound
      ? 'Reader not found - The Earnalism Digital Library'
      : book?.title ? `${book.title} - Reader - The Earnalism Digital Library` : 'Reader - The Earnalism Digital Library',
    description: notFound
      ? 'This Earnalism reader page is no longer available.'
      : 'A secure Earnalism reading room.',
    robots: 'noindex, nofollow',
  });

  const cacheReaderWords = useCallback(() => {
    const words = Array.from(contentRef.current?.querySelectorAll('.tts-word') || []);
    const wordMap = new Map();
    words.forEach((word) => {
      const index = Number(word.dataset.word);
      if (Number.isFinite(index)) wordMap.set(index, word);
    });
    wordsRef.current = words;
    wordMapRef.current = wordMap;
    activeWordRef.current = null;
    highlightedWordIndexRef.current = -1;
  }, []);

  const stopTTS = useCallback(() => {
    synthRef.current?.cancel?.();
    const audio = generatedAudioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    generatedPageEndRef.current = null;
    clearTimeout(ttsFallbackTimerRef.current);
    clearTimeout(ttsSegmentTimerRef.current);
    setTtsActive(false);
    setTtsPaused(false);
    setGeneratedAudioActive(false);
    setTtsWordIndex(-1);
    setTtsHtml('');
    activeWordRef.current?.classList.remove('active', 'tts-word--fallback');
    activeWordRef.current = null;
    highlightedWordIndexRef.current = -1;
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

  useEffect(() => () => {
    if (generatedHighlightRafRef.current) {
      window.cancelAnimationFrame(generatedHighlightRafRef.current);
      generatedHighlightRafRef.current = 0;
    }
  }, []);

  const sendPulse = useCallback(async () => {
    if (!sessionId || !meteredSessionActive) return;
    const headers = getUserAuthHeaders();
    const visible = isReaderVisible();
    const idle = Date.now() - lastReaderActivityRef.current > READER_IDLE_MS;

    try {
      const response = await axios.post(`${API}/reading/pulse`, { session_id: sessionId, visible, idle }, { headers });
      const { status, wallet_seconds } = response.data;

      switch (status) {
        case 'ok':
          setWalletSeconds(wallet_seconds);
          break;
        case 'low_balance':
          setWalletSeconds(wallet_seconds);
          setShowLowBalanceWarning(true);
          trackFunnelEvent('reader_low_balance_state', {
            book_slug: bookId,
            chapter_id: activeChapterId || chapterId || chapter?.id || '',
            wallet_seconds,
            source: 'reader_pulse',
          });
          break;
        case 'paused':
          setWalletSeconds(wallet_seconds);
          break;
        case 'wallet_empty':
          setWalletSeconds(0);
          clearInterval(pulseIntervalRef.current);
          setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0);
          setShowTopUpModal(true);
          trackFunnelEvent('reader_locked_state', {
            book_slug: bookId,
            chapter_id: activeChapterId || chapterId || chapter?.id || '',
            reason: 'wallet_empty',
            source: 'reader_pulse',
          });
          break;
        case 'session_invalid':
          clearInterval(pulseIntervalRef.current);
          setMeteredSessionActive(false);
          toast.info('Reading moved to another device. This device has stopped billing.');
          break;
        default:
          break;
      }
    } catch (err) {
      // Reader heartbeats should not interrupt active reading on transient network errors.
    }
  }, [activeChapterId, bookId, chapter, chapterId, sessionId, meteredSessionActive]);

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
    const markActive = () => {
      lastReaderActivityRef.current = Date.now();
    };
    const markVisibleActive = () => {
      if (isReaderVisible()) markActive();
    };
    const activityEvents = ['pointerdown', 'pointermove', 'keydown', 'wheel', 'touchstart', 'scroll'];

    markActive();
    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, markActive, { passive: true });
    });
    document.addEventListener('visibilitychange', markVisibleActive);
    window.addEventListener('focus', markActive);

    return () => {
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, markActive);
      });
      document.removeEventListener('visibilitychange', markVisibleActive);
      window.removeEventListener('focus', markActive);
    };
  }, []);

  useEffect(() => {
    if (!bookId || !sessionId) return undefined;

    let cancelled = false;
    let startedSession = false;
    let endSessionHeaders = {};
    const requestedAdminPreview = new URLSearchParams(window.location.search).get('preview') === 'admin';

    async function loadReader() {
      const loadStartedAt = readerNowMs();
      const timings = {};
      readerMetricsRef.current = { loadStartedAt, timings };
      setLoading(true);
      setError(null);
      setNotFound(false);
      setLockedState(null);
      setMeteredSessionActive(false);

      try {
        const manifestStartedAt = readerNowMs();
        const [bookRes, packsRes] = await Promise.all([
          fetchReaderBook(bookId, requestedAdminPreview),
          axios.get(`${API}/payments/packs`),
        ]);
        timings.manifest_ms = Math.round(readerNowMs() - manifestStartedAt);
        if (cancelled) return;

        const isAdminPreview = requestedAdminPreview || Boolean(bookRes.adminPreview);
        const manifestAccess = bookRes.data?._readerManifest?.access || bookRes.readerManifest?.access || {};
        const loadedChapters = [...(bookRes.data?.chapters || [])].sort((a, b) => (a.order || 0) - (b.order || 0));
        const activeChapterId = chapterId || loadedChapters[0]?.id;

        setBook(bookRes.data);
        setChapters(loadedChapters);
        setAdminPreview(isAdminPreview);
        setTopUpPacks(packsRes.data || []);
        setActiveChapterId(activeChapterId || null);

        if (!activeChapterId) {
          setChapter(null);
          setProcessedHtml('');
          setTotalWords(0);
          setLoading(false);
          return;
        }

        if (!isAdminPreview && getUserToken()) {
          if (typeof manifestAccess.wallet_seconds === 'number') {
            setWalletSeconds(manifestAccess.wallet_seconds || 0);
          } else {
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
          }
        } else {
          setWalletSeconds(0);
        }

        const chapterStartedAt = readerNowMs();
        const gate = await fetchReaderChapter({
          bookId,
          chapterId: activeChapterId,
          adminPreview: isAdminPreview,
          version: chapterVersionFor(loadedChapters, activeChapterId),
        });
        timings.chapter_ms = Math.round(readerNowMs() - chapterStartedAt);
        if (cancelled) return;

        const loadedChapter = gate.chapter || gate;

        setChapter(loadedChapter);
        if (!chapterId) {
          window.history.replaceState(window.history.state, '', `${window.location.pathname}${readerSearchParams({ chapterId: activeChapterId, adminPreview: isAdminPreview })}`);
        }

        if (gate.locked) {
          setProcessedHtml('');
          setTotalWords(0);
          setLockedState({
            reason: gate.reason || 'LOCKED',
            message: gate.message || 'This chapter is locked.',
            chapter: loadedChapter,
          });
          trackFunnelEvent('reader_locked_state', {
            book_slug: bookId,
            chapter_id: activeChapterId,
            reason: gate.reason || 'LOCKED',
            source: 'chapter_gate',
          });
          timings.total_load_ms = Math.round(readerNowMs() - loadStartedAt);
          sendReaderMetric('reader_chapter_open', {
            session_id: sessionId,
            book_slug: bookId,
            chapter_id: activeChapterId,
            timings,
            metrics: { locked: 1 },
            tags: {
              reason: gate.reason || 'LOCKED',
              admin_preview: isAdminPreview ? '1' : '0',
              manifest_version: bookRes.data?._readerManifest?.version || '',
              chapter_version: chapterVersionFor(loadedChapters, activeChapterId),
            },
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
        if (bookId === LIVE_APPROVED_SLUG && !readerStartedRef.current) {
          readerStartedRef.current = true;
          trackFunnelEvent(DRACULA_CTA_EVENTS.readerStart, {
            book: LIVE_APPROVED_SLUG,
            book_slug: LIVE_APPROVED_SLUG,
            chapter_id: activeChapterId,
            is_preview: Boolean(gate.is_preview),
          });
        }
        timings.render_prepare_ms = Math.round(readerNowMs() - chapterStartedAt - timings.chapter_ms);

        if (!isAdminPreview && getUserToken() && !gate.is_preview) {
          endSessionHeaders = getUserAuthHeaders();
          await axios.post(`${API}/reading/session/start`, { session_id: sessionId, book_slug: bookId, chapter_id: activeChapterId }, { headers: endSessionHeaders });
          startedSession = true;
          setMeteredSessionActive(true);
        }

        timings.total_load_ms = Math.round(readerNowMs() - loadStartedAt);
        sendReaderMetric('reader_chapter_open', {
          session_id: sessionId,
          book_slug: bookId,
          chapter_id: activeChapterId,
          timings,
          metrics: {
            locked: 0,
            word_count: countWordsInHtml(safeHtml),
            chapter_count: loadedChapters.length,
          },
          tags: {
            admin_preview: isAdminPreview ? '1' : '0',
            manifest_version: bookRes.data?._readerManifest?.version || '',
            chapter_version: chapterVersionFor(loadedChapters, activeChapterId),
          },
        });
        trackFunnelEvent('reading_started', {
          book_slug: bookId,
          chapter_id: activeChapterId,
          is_preview: Boolean(gate.is_preview),
        });
        trackFunnelEvent('reader_opened', {
          book_slug: bookId,
          chapter_id: activeChapterId,
          is_preview: Boolean(gate.is_preview),
          source: 'reader_load',
        });
        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          const status = err.response?.status;
          const errorUrl = err.config?.url || '';
          const missingReaderResource = status === 404 && (
            errorUrl.includes('/books/')
            || errorUrl.includes('/admin/books/')
            || errorUrl.includes('/reader/chapter/')
            || errorUrl.includes('/reader/book/')
          );
          if (status === 401) {
            localStorage.removeItem(USER_TOKEN_KEY);
            setLockedState({
              reason: 'AUTH_REQUIRED',
              message: 'Sign in to continue reading this chapter.',
              chapter: null,
            });
            trackFunnelEvent('reader_locked_state', {
              book_slug: bookId,
              chapter_id: chapterId || '',
              reason: 'AUTH_REQUIRED',
              source: 'reader_error',
            });
            setError(null);
          } else if (status === 402) {
            setLockedState({
              reason: 'INSUFFICIENT_READING_TIME',
              message: 'Your reading time has ended. Add reading time to continue.',
              chapter: null,
            });
            trackFunnelEvent('reader_locked_state', {
              book_slug: bookId,
              chapter_id: chapterId || '',
              reason: 'INSUFFICIENT_READING_TIME',
              source: 'reader_error',
            });
            setError(null);
          } else if (missingReaderResource) {
            setBook(null);
            setChapter(null);
            setChapters([]);
            setProcessedHtml('');
            setTtsHtml('');
            setTotalWords(0);
            setLockedState(null);
            setNotFound(true);
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
    if (!(meteredSessionActive && chapter && processedHtml && sessionId)) {
      clearInterval(pulseIntervalRef.current);
      return undefined;
    }

    const startPulseTimer = () => {
      clearInterval(pulseIntervalRef.current);
      if (isReaderVisible()) {
        pulseIntervalRef.current = setInterval(sendPulse, READING_PULSE_MS);
      }
    };
    const handleReaderVisibility = () => {
      if (isReaderVisible()) {
        lastReaderActivityRef.current = Date.now();
        void sendPulse();
        startPulseTimer();
      } else {
        clearInterval(pulseIntervalRef.current);
        void sendPulse();
      }
    };

    startPulseTimer();
    document.addEventListener('visibilitychange', handleReaderVisibility);
    window.addEventListener('focus', handleReaderVisibility);
    window.addEventListener('blur', handleReaderVisibility);

    return () => {
      clearInterval(pulseIntervalRef.current);
      document.removeEventListener('visibilitychange', handleReaderVisibility);
      window.removeEventListener('focus', handleReaderVisibility);
      window.removeEventListener('blur', handleReaderVisibility);
    };
  }, [chapter, processedHtml, sessionId, meteredSessionActive, sendPulse]);

  const currentIdx = useMemo(
    () => chapters.findIndex((item) => item.id === (activeChapterId || chapterId)),
    [chapters, activeChapterId, chapterId],
  );

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
      const isFirstChapter = currentIdx <= 0;
      const isLastChapter = currentIdx < 0 || currentIdx >= chapters.length - 1;
      const includeFrontMatter = chapters.length <= 1 || isFirstChapter;
      const includeBackMatter = chapters.length <= 1 || isLastChapter;
      const nextPages = [
        ...(includeFrontMatter && frontCover ? [{ type: 'front-cover', imageUrl: frontCover, html: '' }] : []),
        ...(includeFrontMatter && chapters.length > 1 ? [{ type: 'chapter-index', html: '' }] : []),
        ...readerPages,
        ...(includeBackMatter && backCover ? [{ type: 'back-cover', imageUrl: backCover, html: '' }] : []),
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
  }, [book, chapters.length, currentIdx, fontSizeIdx, isBengali, readerHtml]);

  const currentPageData = paginatedPages.length ? paginatedPages[currentPage] : { type: 'content', html: readerHtml, contentIndex: 0 };
  const isContentPage = !paginatedPages.length || currentPageData?.type === 'content';
  const isChapterIndexPage = currentPageData?.type === 'chapter-index';
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
    () => (hasGeneratedAudioEnabled(book, bookId) ? audioAssetSlugForBook(book, bookId) : ''),
    [book, bookId],
  );
  const generatedAudioLang = isBengali ? 'ben' : 'en';
  const legacyGeneratedAudioUrl = audioAssetUrl(book, generatedAudioLang, generatedAudioSlug, '.mp3');
  const legacyGeneratedTimestampsUrl = audioAssetUrl(book, generatedAudioLang, generatedAudioSlug, '_timestamps.json');
  const generatedAudioManifestUrl = generatedAudioSlug ? audioManifestUrlForBook(book, generatedAudioLang, generatedAudioSlug) : '';
  const selectedGeneratedAudioTrack = useMemo(
    () => selectAudioTrack({
      manifest: generatedAudioManifest,
      chapterId: activeChapterId || chapterId || chapter?.id,
      currentWordOffset: currentPageWordOffset,
      legacyAudioUrl: legacyGeneratedAudioUrl,
      legacyTimestampsUrl: legacyGeneratedTimestampsUrl,
    }),
    [activeChapterId, chapter, chapterId, currentPageWordOffset, generatedAudioManifest, legacyGeneratedAudioUrl, legacyGeneratedTimestampsUrl],
  );
  const generatedAudioUrl = selectedGeneratedAudioTrack.audioUrl;
  const generatedTimestampsUrl = selectedGeneratedAudioTrack.timestampsUrl;

  useEffect(() => {
    let cancelled = false;
    setGeneratedAudioManifest(null);
    if (!generatedAudioManifestUrl || !generatedAudioSlug || lockedState) return undefined;
    fetch(generatedAudioManifestUrl, { cache: 'force-cache' })
      .then((response) => {
        if (!response.ok) throw new Error('Audio manifest unavailable');
        return response.json();
      })
      .then((raw) => {
        if (!cancelled) {
          setGeneratedAudioManifest(normalizeAudioManifest(raw, generatedAudioLang, generatedAudioSlug));
        }
      })
      .catch(() => {
        if (!cancelled) setGeneratedAudioManifest(null);
      });
    return () => {
      cancelled = true;
    };
  }, [generatedAudioLang, generatedAudioManifestUrl, generatedAudioSlug, lockedState]);

  useEffect(() => {
    let cancelled = false;
    generatedTimestampsRef.current = [];
    generatedAudioWordOffsetRef.current = 0;
    setGeneratedAudioAvailable(false);
    setGeneratedAudioActive(false);
    if (!generatedTimestampsUrl || !readerHtml || lockedState) return undefined;

    fetch(generatedTimestampsUrl, { cache: 'force-cache' })
      .then((response) => {
        if (!response.ok) throw new Error('Generated audio timestamps unavailable');
        return response.json();
      })
      .then((timestamps) => {
        if (cancelled) return;
        const normalized = normalizeGeneratedTimestamps(timestamps, readerHtml, selectedGeneratedAudioTrack.startWord || 0);
        if (normalized.words.length > 0) {
          generatedTimestampsRef.current = normalized.words;
          generatedAudioWordOffsetRef.current = normalized.offset;
          setGeneratedAudioAvailable(true);
          sendReaderMetric('reader_audio_timestamps_loaded', {
            session_id: sessionId,
            book_slug: bookId,
            chapter_id: activeChapterId || chapterId || chapter?.id,
            metrics: {
              timestamp_count: normalized.words.length,
              chunked: selectedGeneratedAudioTrack.chunked ? 1 : 0,
            },
            tags: {
              audio_version: selectedGeneratedAudioTrack.version || '',
            },
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          generatedTimestampsRef.current = [];
          generatedAudioWordOffsetRef.current = 0;
          setGeneratedAudioAvailable(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeChapterId, bookId, chapter, chapterId, generatedTimestampsUrl, lockedState, readerHtml, selectedGeneratedAudioTrack, sessionId]);

  useEffect(() => {
    const audio = generatedAudioRef.current;
    if (!audio || !generatedAudioAvailable || !generatedAudioUrl || lockedState) return;
    audio.preload = 'metadata';
    audio.load();
  }, [generatedAudioAvailable, generatedAudioUrl, lockedState]);

  useEffect(() => {
    setTtsHtml('');
    setTotalWords(countWordsInHtml(currentPageHtml));
    activeWordRef.current?.classList.remove('active', 'tts-word--fallback');
    activeWordRef.current = null;
    highlightedWordIndexRef.current = -1;
  }, [currentPageHtml]);

  useEffect(() => {
    cacheReaderWords();
  }, [cacheReaderWords, displayedHtml]);

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

  useEffect(() => {
    if (bookId !== LIVE_APPROVED_SLUG || !chapter || lockedState || loading || effectiveReadProgress < 98 || currentIdx !== 0) return;
    const currentKey = `${bookId}:${activeChapterId || chapterId || chapter?.id}`;
    if (draculaChapterOneCompleteRef.current === currentKey) return;
    draculaChapterOneCompleteRef.current = currentKey;
    trackFunnelEvent(DRACULA_CTA_EVENTS.chapterOneComplete, {
      book: LIVE_APPROVED_SLUG,
      book_slug: LIVE_APPROVED_SLUG,
      chapter_id: activeChapterId || chapterId || chapter?.id,
    });
  }, [activeChapterId, bookId, chapter, chapterId, currentIdx, effectiveReadProgress, loading, lockedState]);

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
        if (bookId === 'dracula' && (chapter?.order === 0 || /chapter i\b/i.test(chapter?.title || ''))) {
          trackFunnelEvent('chapter_1_completed', {
            book_slug: bookId,
            chapter_id: activeChapterId || chapterId || chapter?.id,
            source: 'reader',
          });
        }

        if (data?.eligible) {
          const claimRes = await axios.post(`${API}/users/me/rewards/claim`, {}, { headers: getUserAuthHeaders() });
          const reward = claimRes.data || {};
          if (reward.claimed_now) {
            setWalletSeconds(reward.wallet_seconds || 0);
            toast.success(`${reward.credit_minutes || 10} minutes credited toward The Reader’s Reserve.`);
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
            lastReaderActivityRef.current = Date.now();
            clearInterval(pulseIntervalRef.current);
            if (isReaderVisible()) {
              pulseIntervalRef.current = setInterval(sendPulse, READING_PULSE_MS);
            }
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
    if (highlightedWordIndexRef.current === index) return;
    const current = wordsRef.current[index];
    if (!current) return;

    activeWordRef.current?.classList.remove('active', 'tts-word--fallback');
    current.classList.add('active');
    current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    activeWordRef.current = current;
    highlightedWordIndexRef.current = index;
    setTtsWordIndex(index);
  }, []);

  const highlightGeneratedWord = useCallback((globalIndex) => {
    if (highlightedWordIndexRef.current === globalIndex) return;
    let current = wordMapRef.current.get(globalIndex);
    if ((!current || !current.isConnected) && contentRef.current) {
      cacheReaderWords();
      current = wordMapRef.current.get(globalIndex);
    }
    if (!current) return;

    activeWordRef.current?.classList.remove('active', 'tts-word--fallback');
    current.classList.add('active');
    current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    activeWordRef.current = current;
    highlightedWordIndexRef.current = globalIndex;
    setTtsWordIndex(globalIndex);
  }, [cacheReaderWords]);

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

  const primeGeneratedAudio = useCallback(() => {
    const audio = generatedAudioRef.current;
    if (!audio || !generatedAudioAvailable || !generatedAudioUrl) return;
    if (!audioIntentStartedAtRef.current) audioIntentStartedAtRef.current = readerNowMs();
    audio.preload = 'auto';
    if (audio.readyState === 0) audio.load();
  }, [generatedAudioAvailable, generatedAudioUrl]);

  const startGeneratedAudio = useCallback(() => {
    const audio = generatedAudioRef.current;
    const timestamps = generatedTimestampsRef.current || [];
    const pageHtml = currentPageHtml || readerHtml;
    if (!isContentPage || !audio || !generatedAudioAvailable || !timestamps.length || !pageHtml) return false;

    audioIntentStartedAtRef.current = readerNowMs();
    primeGeneratedAudio();
    synthRef.current?.cancel?.();
    const wrapped = wrapWordsInSpans(pageHtml, currentPageWordOffset);
    const firstWord = currentPageWordOffset;
    const lastWord = currentPageWordOffset + Math.max(0, wrapped.totalWords - 1);
    const firstAudioWord = Math.max(0, timestampArrayIndexForWord(timestamps, firstWord));
    const firstTimestamp = timestamps[firstAudioWord];
    if (!firstTimestamp) return false;

    generatedPageEndRef.current = Math.max(0, lastWord);
    const tickGeneratedHighlight = () => {
      const audioIndex = timestampIndexAt(timestamps, Math.floor(audio.currentTime * 1000));
      const wordIndex = audioIndex >= 0 ? timestampWordIndex(timestamps[audioIndex], audioIndex) : -1;
      const pageEnd = generatedPageEndRef.current;
      if (Number.isFinite(pageEnd) && wordIndex > pageEnd) {
        audio.pause();
        generatedPageEndRef.current = null;
        setGeneratedAudioActive(false);
        setTtsActive(false);
        setTtsPaused(false);
        return false;
      }
      if (wordIndex >= currentPageWordOffset) {
        highlightGeneratedWord(wordIndex);
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
        tickGeneratedHighlight();
        audio.play().catch(() => {
          setGeneratedAudioActive(false);
          setTtsActive(false);
          setTtsPaused(false);
          toast.error('Generated audiobook could not start in this browser.');
        });
      });
    });
    return true;
  }, [currentPageHtml, currentPageWordOffset, generatedAudioAvailable, highlightGeneratedWord, isContentPage, primeGeneratedAudio, readerHtml]);

  const handleGeneratedAudioMetadata = useCallback(() => {
    if (!audioIntentStartedAtRef.current) return;
    sendReaderMetric('reader_audio_metadata_loaded', {
      session_id: sessionId,
      book_slug: bookId,
      chapter_id: activeChapterId || chapterId || chapter?.id,
      timings: {
        audio_metadata_ms: Math.round(readerNowMs() - audioIntentStartedAtRef.current),
      },
      metrics: {
        chunked: selectedGeneratedAudioTrack.chunked ? 1 : 0,
      },
      tags: {
        audio_version: selectedGeneratedAudioTrack.version || '',
      },
    });
    audioIntentStartedAtRef.current = 0;
  }, [activeChapterId, bookId, chapter, chapterId, selectedGeneratedAudioTrack, sessionId]);

  const startTTS = useCallback(() => {
    if (!isContentPage) {
      toast.info('Audio is available on reading pages only.');
      return;
    }
    if (isNarrationDisabledForBook(book, bookId)) {
      toast.info('Audiobook controls stay hidden until the release gate approves this title.');
      return;
    }
    if (startGeneratedAudio()) return;

    toast.info('Approved audiobook audio is not available for this reader page yet.');
  }, [book, bookId, isContentPage, startGeneratedAudio]);

  const pauseTTS = () => {
    clearTimeout(ttsFallbackTimerRef.current);
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
    const wordIndex = index >= 0 ? timestampWordIndex(timestamps[index], index) : -1;
    const pageEnd = generatedPageEndRef.current;
    if (Number.isFinite(pageEnd) && wordIndex > pageEnd) {
      audio.pause();
      generatedPageEndRef.current = null;
      setGeneratedAudioActive(false);
      setTtsActive(false);
      setTtsPaused(false);
      return false;
    }
    if (wordIndex >= currentPageWordOffset) {
      highlightGeneratedWord(wordIndex);
      return true;
    }
    return false;
  }, [currentPageWordOffset, highlightGeneratedWord]);

  const handleGeneratedAudioTimeUpdate = useCallback(() => {
    if (ttsPaused) return;
    if (generatedHighlightRafRef.current) return;
    generatedHighlightRafRef.current = window.requestAnimationFrame(() => {
      generatedHighlightRafRef.current = 0;
      syncGeneratedAudioHighlight();
    });
  }, [syncGeneratedAudioHighlight, ttsPaused]);

  const handleGeneratedAudioEnded = useCallback(() => {
    if (generatedHighlightRafRef.current) {
      window.cancelAnimationFrame(generatedHighlightRafRef.current);
      generatedHighlightRafRef.current = 0;
    }
    generatedPageEndRef.current = null;
    activeWordRef.current?.classList.remove('active', 'tts-word--fallback');
    activeWordRef.current = null;
    highlightedWordIndexRef.current = -1;
    setGeneratedAudioActive(false);
    setTtsActive(false);
    setTtsPaused(false);
    setTtsWordIndex(-1);
  }, []);

  useEffect(() => {
    if (!generatedAudioActive || ttsPaused) return undefined;
    let timerId = 0;
    const tick = () => {
      syncGeneratedAudioHighlight();
      timerId = window.setTimeout(tick, 140);
    };
    tick();
    return () => window.clearTimeout(timerId);
  }, [generatedAudioActive, syncGeneratedAudioHighlight, ttsPaused]);

  const handleVoiceToggle = () => {
    if (!ttsActive) startTTS();
    else if (ttsPaused) resumeTTS();
    else pauseTTS();
  };

  const prevChapter = chapters[currentIdx - 1];
  const nextChapter = chapters[currentIdx + 1];
  const hasPages = paginatedPages.length > 1;
  const canPrev = hasPages ? currentPage > 0 || Boolean(prevChapter) : Boolean(prevChapter);
  const canNext = hasPages ? currentPage < paginatedPages.length - 1 || Boolean(nextChapter) : Boolean(nextChapter);
  const readerUserName = user && typeof user === 'object' ? user.name : 'Reader';
  const readerUserEmail = user && typeof user === 'object' ? user.email : '';
  const rightsCopy = rightsForBook(book, readerUserName);
  const narrationDisabledForBook = isNarrationDisabledForBook(book, bookId);

  useEffect(() => {
    if (!book || lockedState || loading || !nextChapter?.id) return undefined;
    const idleId = runWhenIdle(() => {
      const nextVersion = chapterVersionFor(chapters, nextChapter.id);
      const canPrefetchPaid = adminPreview || nextChapter.is_preview || walletSeconds > 0;
      if (canPrefetchPaid) {
        fetchReaderChapter({
          bookId,
          chapterId: nextChapter.id,
          adminPreview,
          version: nextVersion,
        }).catch(() => {});
      }

      if (!narrationDisabledForBook && generatedAudioSlug) {
        if (generatedAudioManifestUrl) prefetchAsset(generatedAudioManifestUrl);
        const nextTrack = selectAudioTrack({
          manifest: generatedAudioManifest,
          chapterId: nextChapter.id,
          currentWordOffset: 0,
          legacyAudioUrl: legacyGeneratedAudioUrl,
          legacyTimestampsUrl: legacyGeneratedTimestampsUrl,
        });
        // Keep MP3 loading under the audio element so metadata/range requests do not become full-file prefetches.
        prefetchAsset(nextTrack.timestampsUrl);
      }
    });
    return () => cancelIdleTask(idleId);
  }, [
    adminPreview,
    book,
    bookId,
    chapters,
    generatedAudioManifest,
    generatedAudioManifestUrl,
    generatedAudioSlug,
    legacyGeneratedAudioUrl,
    legacyGeneratedTimestampsUrl,
    loading,
    lockedState,
    narrationDisabledForBook,
    nextChapter,
    walletSeconds,
  ]);

  const goToChapter = useCallback((id) => {
    stopTTS();
    navigate(`/reader/${bookId}${readerSearchParams({ chapterId: id, adminPreview })}`);
  }, [adminPreview, bookId, navigate, stopTTS]);

  const goPrev = useCallback(() => {
    stopTTS();
    if (hasPages && currentPage > 0) {
      setCurrentPage((page) => Math.max(0, page - 1));
      scrollContainerRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }
    if (prevChapter) goToChapter(prevChapter.id);
  }, [currentPage, goToChapter, hasPages, prevChapter, stopTTS]);

  const goNext = useCallback(() => {
    stopTTS();
    if (hasPages && currentPage < paginatedPages.length - 1) {
      setCurrentPage((page) => Math.min(paginatedPages.length - 1, page + 1));
      scrollContainerRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }
    if (nextChapter) goToChapter(nextChapter.id);
  }, [currentPage, goToChapter, hasPages, nextChapter, paginatedPages.length, stopTTS]);

  const goToPage = useCallback((index, options = {}) => {
    const nextPage = Math.min(Math.max(Number(index) || 0, 0), Math.max(paginatedPages.length - 1, 0));
    if (nextPage === currentPage) return;
    stopTTS();
    setCurrentPage(nextPage);
    scrollContainerRef.current?.scrollTo?.({ top: 0, behavior: options.behavior || 'smooth' });
  }, [currentPage, paginatedPages.length, stopTTS]);

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
      <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: THEMES.beige.canvas }} role="status" aria-live="polite">
        <Loader2 size={32} className="animate-spin" color="#6B1020" />
        <div style={{ fontFamily: READER_SERIF, fontSize: 17, color: '#7A5C62' }}>
          Opening chapter…
        </div>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex min-h-screen items-center justify-center px-5 py-14 text-center" style={{ background: THEMES.beige.canvas }} data-testid="reader-not-found">
        <div className="w-full max-w-md rounded-2xl border border-[#E8DDD8] bg-white/70 px-7 py-9 shadow-book">
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: '#F5F0E8', color: '#6B1020' }}>
            <AlertCircle size={22} />
          </div>
          <div className="italic-eyebrow mb-3">Unavailable reader</div>
          <h1 className="font-serif-light text-3xl text-burgundy leading-tight">Reader not found</h1>
          <p className="mt-5 text-sm font-light leading-relaxed text-charcoal-soft">
            This reading room is not available from the production reader API right now. The library remains available, and no unapproved audio or fallback narration is exposed.
          </p>
          <div className="mt-8 flex flex-col gap-3">
            <button type="button" onClick={() => navigate('/library')} className="btn-primary w-full justify-center">
              Back to Library
            </button>
            <button type="button" onClick={() => navigate('/')} className="text-sm text-charcoal-soft underline decoration-[var(--brand-gold)]/60 underline-offset-4">
              Go home
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 px-6 text-center min-h-screen" style={{ background: THEMES.beige.canvas }} data-testid="reader-error" role="alert">
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
      <div className="flex min-h-screen items-center justify-center px-5 py-14 text-center" style={{ background: THEMES.beige.canvas }} data-testid="reader-locked">
        <div className="w-full max-w-md rounded-2xl border border-[#E8DDD8] bg-white/70 px-7 py-9 shadow-book" role="status" aria-live="polite" data-testid="reader-locked-state">
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: '#F5F0E8', color: '#6B1020' }}>
            {reason === 'INSUFFICIENT_READING_TIME' ? <CreditCard size={22} /> : <LogIn size={22} />}
          </div>
          <div className="italic-eyebrow mb-3">Reading access</div>
          <h1 className="font-serif-light text-3xl text-burgundy leading-tight">{title}</h1>
          <p className="mt-5 text-sm font-light leading-relaxed text-charcoal-soft">
            {lockedState.message || 'This chapter is locked.'}
          </p>
          <p className="mt-3 text-xs font-light leading-relaxed text-charcoal-soft/80" data-testid="reader-locked-wallet-note">
            Chapter 1 remains free. Later Dracula chapters ask for sign-in and reading time from your wallet.
          </p>

          <div className="mt-8 flex flex-col gap-3">
            {reason === 'AUTH_REQUIRED' && (
              <button
                type="button"
                onClick={() => {
                  trackFunnelEvent('return_resume_reading_click', {
                    book_slug: bookId,
                    chapter_id: activeChapterId || chapterId || '',
                    source: 'reader_locked_sign_in',
                  });
                  navigate(signInUrl);
                }}
                className="btn-primary w-full justify-center"
              >
                Sign In
              </button>
            )}
            {reason === 'INSUFFICIENT_READING_TIME' && (
              <button
                type="button"
                onClick={() => {
                  trackFunnelEvent('return_resume_reading_click', {
                    book_slug: bookId,
                    chapter_id: activeChapterId || chapterId || '',
                    source: 'reader_locked_pricing',
                  });
                  navigate('/pricing');
                }}
                className="btn-primary w-full justify-center"
              >
                Add Reading Time
              </button>
            )}
            {reason === 'BLOCKED' && (
              <button type="button" onClick={() => navigate('/contact')} className="btn-primary w-full justify-center">
                Contact Support
              </button>
            )}
            {canOpenPreview && (
              <button
                type="button"
                onClick={() => {
                  trackFunnelEvent('return_resume_reading_click', {
                    book_slug: bookId,
                    chapter_id: previewChapter.id,
                    source: 'reader_locked_free_preview',
                  });
                  navigate(`/reader/${bookId}?c=${previewChapter.id}`);
                }}
                className="btn-secondary w-full justify-center"
              >
                Read Free Preview
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                trackFunnelEvent('return_resume_reading_click', {
                  book_slug: bookId,
                  chapter_id: activeChapterId || chapterId || '',
                  source: 'reader_locked_back_to_book',
                });
                navigate(`/book/${bookId}`);
              }}
              className="text-sm text-charcoal-soft underline decoration-[var(--brand-gold)]/60 underline-offset-4"
            >
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
      : currentPageData?.type === 'chapter-index'
        ? 'Contents'
      : currentPageData?.type === 'index'
        ? 'Index'
        : currentPageData?.type === 'reference'
          ? 'Reference'
        : 'Generated reader pages';
  const audioDisabledForPage = narrationDisabledForBook || !isContentPage;
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
  const progressRatio = Math.min(1, Math.max(0, effectiveReadProgress / 100));
  const chapterPositionLabel = chapters.length > 1 && currentIdx >= 0
    ? `Ch. ${currentIdx + 1} of ${chapters.length}`
    : '';
  const topbarPositionLabel = hasPages
    ? [chapterPositionLabel, `Page ${currentPage + 1} of ${paginatedPages.length}`].filter(Boolean).join(' · ')
    : (chapterPositionLabel || `Ch. ${Math.max(0, currentIdx) + 1} of ${chapters.length}`);

  return (
    <div
      ref={scrollContainerRef}
      className={readerThemeClass}
      data-testid="reader-page"
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
          src={generatedAudioAvailable ? generatedAudioUrl : undefined}
          preload={generatedAudioAvailable ? 'metadata' : 'none'}
          onLoadedMetadata={handleGeneratedAudioMetadata}
          onTimeUpdate={handleGeneratedAudioTimeUpdate}
          onEnded={handleGeneratedAudioEnded}
          style={{ display: 'none' }}
          data-testid="generated-audiobook"
        />
      )}

      <header className={`reader-topbar ${toolbarVisible ? 'reader-topbar--visible' : 'reader-topbar--hidden'}`}>
        <button type="button" onClick={() => navigate(adminPreview ? '/admin' : `/book/${bookId}`)} className="reader-topbar__back" aria-label={adminPreview ? 'Back to admin' : 'Back to book'}>
          <ChevronLeft size={18} />
          <span>{adminPreview ? 'Back to Admin' : readerDisplayTitle}</span>
        </button>

        <div className="reader-topbar__center">
          <strong>{topbarPositionLabel}</strong>
          <span>{chapter?.title && chapter.title !== 'Full Text' ? normalizeChapterDisplayTitle(chapter.title) : 'Reading edition'}</span>
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
            ) : isChapterIndexPage ? (
              <SecureReader
                sessionId={sessionId}
                userName={readerUserName}
                userEmail={readerUserEmail}
                bookSlug={bookId}
                chapterId={activeChapterId || chapterId || chapter?.id}
                title={`${book?.title || 'Earnalism'} · Contents`}
                blurred={contentBlurred}
                licenseNotice={rightsCopy.licenseNotice}
                licenseMetadata={rightsCopy.licenseMetadata}
                watermarkText={rightsCopy.watermarkText}
                footerText={rightsCopy.footerText}
              >
                <ReaderChapterIndex
                  chapters={chapters}
                  currentChapterId={activeChapterId || chapterId || chapter?.id}
                  bookId={bookId}
                  adminPreview={adminPreview}
                  onChapterSelect={goToChapter}
                />
              </SecureReader>
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
                  <img
                    src={currentPageData.imageUrl}
                    alt={`${book?.title || 'Book'} ${currentPageLabel.toLowerCase()}`}
                    decoding="async"
                    fetchPriority="high"
                  />
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
            <div className="reader-progress__fill" style={{ '--reader-progress-scale': progressRatio, '--reader-progress-percent': `${effectiveReadProgress}%` }}>
              <span className="reader-progress__thumb" />
            </div>
          </div>
          {hasPages && (
            <input
              type="range"
              className="reader-page-scrubber"
              min="1"
              max={paginatedPages.length}
              value={currentPage + 1}
              onChange={(event) => goToPage(Number(event.target.value) - 1, { behavior: 'auto' })}
              aria-label={`Jump to reader page, currently page ${currentPage + 1} of ${paginatedPages.length}`}
            />
          )}
        </div>

        <div className="reader-bottom-bar__controls">
          <button type="button" disabled={!canPrev} onClick={goPrev} className="reader-nav-button reader-nav-button--ghost">
            <ChevronLeft size={17} />
            <span>{hasPages ? 'Prev Page' : 'Prev'}</span>
          </button>

          {narrationDisabledForBook ? (
            <div className="reader-audio-disabled" aria-label="Audio disabled for this book">
              Audio hidden until approved
            </div>
          ) : (
            <div className="reader-audio-control">
              <button
                type="button"
                onClick={handleVoiceToggle}
                onMouseEnter={primeGeneratedAudio}
                onFocus={primeGeneratedAudio}
                onTouchStart={primeGeneratedAudio}
                disabled={audioDisabledForPage}
                className="reader-audio-button"
                aria-label={voiceButtonLabel}
              >
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
          )}

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
                Add Time
              </button>
              <button type="button" onClick={() => setShowLowBalanceWarning(false)} style={{ color: '#6B1020', fontFamily: 'Inter', fontSize: 16 }}>
                ✕
              </button>
            </div>
          </div>
        </div>
      )}

      {showTopUpModal && (
        <div className="fixed inset-0 z-[60] flex items-end justify-center" role="dialog" aria-modal="true" aria-labelledby="reading-time-dialog-title" aria-describedby="reading-time-dialog-description" data-testid="reading-time-dialog">
          <div className="absolute inset-0 bg-black/50" style={{ backdropFilter: 'blur(4px)' }} />
          <div className="relative rounded-t-2xl p-6 w-full max-w-lg animate-slide-up" style={{ background: '#FAF7F0', boxShadow: '0 -8px 40px rgba(107,16,32,0.15)' }}>
            <div className="text-center">
              <div style={{ fontSize: 32 }}>⏸</div>
              <div id="reading-time-dialog-title" style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 26, color: '#6B1020', marginTop: 3 }}>
                Reading Paused
              </div>
              <p id="reading-time-dialog-description" style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 16, color: '#7A5C62', marginTop: 2 }}>
                You've used all your reading time.
              </p>
              <p style={{ fontFamily: 'Inter', fontSize: 12, color: '#D4A843', marginTop: 1, marginBottom: 20 }}>
                Your place is saved. Add reading time to continue from where you left off.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {topUpPacks.map((pack, index) => {
                const selected = index === selectedPack;
                const price = pack.price ?? pack.price_inr;
                return (
                  <button
                    key={pack._id || pack.id}
                    type="button"
                    onClick={() => setSelectedPack(index)}
                    aria-pressed={selected}
                    aria-label={`Select ${pack.label || `${pack.minutes} minute`} reading-time pack for ₹${price}`}
                    className="rounded-xl p-4 cursor-pointer transition-all text-left"
                    style={{ borderWidth: 2, borderStyle: 'solid', borderColor: selected ? '#6B1020' : '#E8DDD8', background: selected ? 'rgba(107,16,32,0.06)' : 'white' }}
                  >
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
                  </button>
                );
              })}
            </div>

            <button type="button" onClick={() => handleTopUp(topUpPacks[selectedPack])} disabled={topUpProcessing || !topUpPacks[selectedPack]} className="w-full mt-4 rounded-xl py-3 flex items-center justify-center gap-2" style={{ background: '#6B1020', color: '#FAF7F0', fontFamily: 'Inter', fontSize: 15, fontWeight: 500, opacity: topUpProcessing ? 0.7 : 1 }}>
              {topUpProcessing && <Loader2 className="animate-spin" size={16} />}
              Add reading time
            </button>
            <button type="button" onClick={() => setShowTopUpModal(false)} className="w-full mt-3 text-center" style={{ fontFamily: 'Inter', fontSize: 12, color: '#A88A8F' }}>
              I'll return later
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

          {!narrationDisabledForBook && (
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
          )}
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
