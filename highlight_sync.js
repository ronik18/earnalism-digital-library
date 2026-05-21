/*
 * Earnalism audiobook word-highlight sync.
 *
 * Drop this file into the reader bundle or serve it as a standalone script.
 * It loads {slug}_timestamps.json, wraps reader text nodes in word spans, and
 * highlights the active word using O(log n) timestamp lookup on audio updates.
 */

(function attachEarnalismHighlightSync(globalScope) {
  "use strict";

  const DEFAULT_BODY_SELECTOR = ".chapter-body";
  const DEFAULT_AUDIO_SELECTOR = "#earnalism-audio";

  async function loadTimestamps(slug, lang) {
    const response = await fetch(`/audio/${lang}/${slug}_timestamps.json`, {
      credentials: "same-origin",
      cache: "force-cache"
    });
    if (!response.ok) {
      throw new Error(`Timestamps not found for ${slug}`);
    }
    return response.json();
  }

  function collectTextNodes(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.textContent || !node.textContent.trim()) {
          return NodeFilter.FILTER_REJECT;
        }
        const parent = node.parentElement;
        if (!parent) {
          return NodeFilter.FILTER_REJECT;
        }
        if (parent.closest(".word-token, script, style, noscript, audio, video")) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    });

    const nodes = [];
    let node;
    while ((node = walker.nextNode())) {
      nodes.push(node);
    }
    return nodes;
  }

  function splitTokens(text, lang) {
    // Bengali and English both split on whitespace here. Bengali conjuncts,
    // ZWJ (U+200D), and ZWNJ (U+200C) remain inside tokens because the regex
    // does not split within a grapheme-like word.
    if (lang === "ben") {
      return text.split(/(\s+)/);
    }
    return text.split(/(\s+)/);
  }

  function tokenizeReadingSurface(lang, options = {}) {
    const body = document.querySelector(options.bodySelector || DEFAULT_BODY_SELECTOR);
    if (!body) {
      throw new Error("Reader body not found");
    }

    const existing = body.querySelectorAll(".word-token");
    if (existing.length > 0) {
      return Array.from(existing);
    }

    const wordSpans = [];
    const textNodes = collectTextNodes(body);

    textNodes.forEach((node) => {
      const tokens = splitTokens(node.textContent, lang);
      const fragment = document.createDocumentFragment();

      tokens.forEach((token) => {
        if (/^\s+$/.test(token)) {
          fragment.appendChild(document.createTextNode(token));
        } else if (token.length > 0) {
          const span = document.createElement("span");
          span.className = "word-token";
          span.dataset.index = String(wordSpans.length);
          span.textContent = token;
          wordSpans.push(span);
          fragment.appendChild(span);
        }
      });

      node.parentNode.replaceChild(fragment, node);
    });

    return wordSpans;
  }

  function binarySearchWord(timestamps, nowMs) {
    let lo = 0;
    let hi = timestamps.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (timestamps[mid].start_ms <= nowMs) {
        lo = mid;
      } else {
        hi = mid - 1;
      }
    }
    return lo;
  }

  function startHighlightSync(audioElement, timestamps, wordSpans) {
    if (!audioElement || !timestamps.length || !wordSpans.length) {
      return;
    }

    let currentIndex = -1;
    let lastSpan = null;

    function setActiveIndex(index) {
      if (index === currentIndex) {
        return;
      }

      if (lastSpan) {
        lastSpan.classList.remove("word-active");
        lastSpan.classList.add("word-read");
      }

      const nextSpan = wordSpans[index];
      if (nextSpan) {
        nextSpan.classList.add("word-active");
        nextSpan.scrollIntoView({
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
          block: "center",
          inline: "nearest"
        });
        lastSpan = nextSpan;
      }

      currentIndex = index;
    }

    audioElement.addEventListener("timeupdate", () => {
      const nowMs = Math.floor(audioElement.currentTime * 1000);
      setActiveIndex(binarySearchWord(timestamps, nowMs));
    });

    audioElement.addEventListener("seeked", () => {
      wordSpans.forEach((span) => {
        span.classList.remove("word-active", "word-read");
      });
      currentIndex = -1;
      lastSpan = null;
      const nowMs = Math.floor(audioElement.currentTime * 1000);
      setActiveIndex(binarySearchWord(timestamps, nowMs));
    });

    audioElement.addEventListener("ended", () => {
      if (lastSpan) {
        lastSpan.classList.remove("word-active");
        lastSpan.classList.add("word-read");
      }
    });
  }

  function installHighlightStyles() {
    if (document.getElementById("earnalism-highlight-sync-styles")) {
      return;
    }
    const style = document.createElement("style");
    style.id = "earnalism-highlight-sync-styles";
    style.textContent = `
      .word-token {
        display: inline;
        border-radius: 2px;
        transition: background 0.15s ease, color 0.3s ease;
      }
      .word-active {
        background: var(--earnalism-gold-light, #E8D5A3);
        color: var(--earnalism-ink, #2C1810);
      }
      .word-read {
        color: var(--earnalism-muted, #8B7355);
      }
      @media (prefers-reduced-motion: reduce) {
        .word-token {
          transition: none;
        }
      }
    `;
    document.head.appendChild(style);
  }

  async function initReader(slug, lang, options = {}) {
    try {
      installHighlightStyles();
      const audio = document.querySelector(options.audioSelector || DEFAULT_AUDIO_SELECTOR);
      if (!audio) {
        throw new Error("Audio element not found");
      }

      const start = async () => {
        const timestamps = options.timestamps || await loadTimestamps(slug, lang);
        if (!Array.isArray(timestamps) || timestamps.length === 0) {
          console.warn(`No timestamps for ${slug}; highlighting disabled`);
          return;
        }
        const wordSpans = tokenizeReadingSurface(lang, options);
        startHighlightSync(audio, timestamps, wordSpans);
      };

      if (document.fonts && document.fonts.ready) {
        await document.fonts.ready;
      }
      await start();
    } catch (error) {
      console.error("Highlight sync init failed:", error);
    }
  }

  const api = {
    loadTimestamps,
    tokenizeReadingSurface,
    binarySearchWord,
    startHighlightSync,
    installHighlightStyles,
    initReader
  };

  globalScope.EarnalismHighlightSync = api;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
