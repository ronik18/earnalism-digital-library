import { chromium, webkit, firefox } from 'playwright';
import fs from 'node:fs';

const ROOT = process.cwd();
const widths = [320, 360, 390, 430, 768, 1024];
const indexCss = fs.readFileSync(`${ROOT}/frontend/src/index.css`, 'utf8').replace(/@tailwind [^\n]+;?/g, '');
const readerCss = fs.readFileSync(`${ROOT}/frontend/src/pages/ReaderRoute.css`, 'utf8').replace(/@tailwind [^\n]+;?/g, '');
const audioCss = fs.readFileSync(`${ROOT}/frontend/src/components/ReaderAudiobookPanel.css`, 'utf8');

const html = String.raw`<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root { color-scheme: light; }
${indexCss}
${readerCss}
${audioCss}
.test-surface { padding: 20px; }
.reader-topbar { position: static !important; }
.reader-bottom-bar { position: static !important; }
.case { margin: 12px 0; padding: 12px; border: 1px solid var(--brand-border); }
</style>
</head>
<body style="margin:0; background:#f4efe7;">
<div class="test-surface">
  <div class="case">
    <p id="pair-text-gold" class="text-gold">Text Gold Utility sample</p>
    <p id="pair-text-gold-soft" class="text-gold-soft">Text Gold Soft Utility sample</p>
    <p id="pair-text-gold-on-dark" class="text-gold" style="background:#5A1F2B; padding:4px 8px;">Text Gold on brand-burgundy</p>
    <p id="pair-text-gold-soft-on-dark" class="text-gold-soft" style="background:#5A1F2B; padding:4px 8px;">Text Gold Soft on brand-burgundy</p>
  </div>
  <div class="case">
    <button id="reader-topbar-cta" class="reader-audio-button">Start Reading</button>
    <button id="reader-listening-cta" class="reader-listening-room__reading-cta">Play Sample</button>
    <a id="reader-index-link" href="#" class="reader-index-page" style="display:block; margin-top:8px;">Reader index link</a>
  </div>
  <div class="case">
    <div class="reader-progress" id="reader-progress-test" style="position:relative; height:22px;">
      <div class="reader-progress__track" id="reader-progress-track"></div>
      <input class="reader-page-scrubber" id="reader-progress-input" type="range" min="0" max="100" value="35" style="opacity:1; height:18px;" />
    </div>
  </div>
  <div class="case">
    <div class="reader-topbar" style="grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);">
      <button id="reader-topbar-back" class="reader-topbar__back">Back</button>
      <div class="reader-topbar__center" style="min-width:0;">
        <strong id="reader-topbar-title">Reader Header Title</strong>
        <span id="reader-topbar-subtitle">Long subtitle intended to remain single-line on narrow widths</span>
      </div>
      <div id="reader-topbar-actions" class="reader-topbar__actions"><button id="reader-icon-btn" class="reader-icon-button">🔖</button></div>
    </div>
    <div class="reader-bottom-bar" style="position:static;">
      <div class="reader-bottom-bar__controls">
        <button class="reader-nav-button">Previous</button>
        <button id="reader-player-cta" class="reader-player-launch"><span>Open Reader</span><span>↗</span></button>
        <button class="reader-audio-button">Resume</button>
      </div>
    </div>
  </div>
  <div class="case" style="background:var(--reader-surface, #f8f3eb);">
    <a href="#" id="reader-index-item" class="reader-index-page">reader-index-item</a>
    <button id="reader-toc-close" class="reader-toc-close" aria-label="close">×</button>
    <button id="reader-toc-item" class="reader-toc-item" type="button"><span class="reader-toc-item__sequence">1</span><span class="reader-toc-item__copy"><strong>A very long chapter title that should stay within bounds</strong><small>small</small></span></button>
    <button id="reader-settings-reset" class="reader-settings-reset">Reset</button>
    <button id="reader-settings-sheet" class="reader-settings-sheet">Sheet</button>
  </div>
</div>
<script>
window.__pwPayload = {
  contrastTests: [
    { id: 'text-gold-vs-bg', selector: '#pair-text-gold', threshold: 4.5, mode: 'text' },
    { id: 'text-gold-soft-vs-bg', selector: '#pair-text-gold-soft', threshold: 4.5, mode: 'text' },
    { id: 'text-gold-on-dark', selector: '#pair-text-gold-on-dark', threshold: 4.5, mode: 'text' },
    { id: 'text-gold-soft-on-dark', selector: '#pair-text-gold-soft-on-dark', threshold: 4.5, mode: 'text' },
    { id: 'reader-topbar-cta', selector: '#reader-topbar-cta', threshold: 4.5, mode: 'text' },
    { id: 'reader-listening-cta', selector: '#reader-listening-cta', threshold: 4.5, mode: 'text' },
    { id: 'reader-index-link', selector: '#reader-index-link', threshold: 4.5, mode: 'text' },
    { id: 'toc-close-outline', selector: '#reader-toc-close', mode: 'outline', focusSelector: '#reader-toc-close', threshold: 3 },
    { id: 'toc-item-outline', selector: '#reader-toc-item', mode: 'outline', focusSelector: '#reader-toc-item', threshold: 3 },
    { id: 'settings-reset-outline', selector: '#reader-settings-reset', mode: 'outline', focusSelector: '#reader-settings-reset', threshold: 3 },
    { id: 'settings-sheet-outline', selector: '#reader-settings-sheet', mode: 'outline', focusSelector: '#reader-settings-sheet', threshold: 3 },
    { id: 'reader-progress-outline', selector: '#reader-progress-track', mode: 'outline', focusSelector: '#reader-progress-input', threshold: 3 },
  ],
  wrapping: [
    '#reader-topbar-title',
    '#reader-topbar-subtitle',
    '#reader-player-cta',
    '#reader-topbar-actions',
    '#reader-toc-item',
  ],
};
</script>
</body>
</html>`;

const launchBrowser = async () => {
  const attempts = [
    { name: 'chromium', engine: chromium },
    { name: 'webkit', engine: webkit },
    { name: 'firefox', engine: firefox },
  ];
  for (const attempt of attempts) {
    try {
      const launchArgs = {
        headless: true,
        args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
      };
      const browser = await attempt.engine.launch(launchArgs);
      return { browser, name: attempt.name };
    } catch (error) {
      console.warn(`contrast-check: ${attempt.name} launch failed, trying next engine`, error.message);
    }
  }
  throw new Error('No Playwright browser could be launched in this environment.');
};

const { browser, name: activeBrowser } = await launchBrowser();
console.log(`contrast-check: running with ${activeBrowser}`);
const page = await browser.newPage({ width: 1280, height: 2200 });

const report = [];
for (const width of widths) {
  await page.setViewportSize({ width, height: 2200 });
  await page.setContent(html, { waitUntil: 'domcontentloaded' });

  const result = await page.evaluate(async () => {
    const colorParse = (value) => {
      if (!value || value === 'transparent') return null;
      if (!value.startsWith('rgb')) return null;
      const values = value.replace(/rgba?\(|\)/g, '').split(',').map((v) => Number(v.trim())).filter((v) => Number.isFinite(v));
      if (values.length < 3) return null;
      return [values[0], values[1], values[2], values.length === 4 ? values[3] : 1];
    };

    const blend = (fg, bg) => {
      const alpha = fg[3];
      const inv = 1 - alpha;
      return [fg[0] * alpha + bg[0] * inv, fg[1] * alpha + bg[1] * inv, fg[2] * alpha + bg[2] * inv, 1];
    };

    const luminance = (rgb) => {
      const channels = rgb.slice(0, 3).map((channel) => {
        const s = channel / 255;
        return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    };

    const contrastRatio = (a, b) => {
      const L1 = luminance(a);
      const L2 = luminance(b);
      const light = Math.max(L1, L2);
      const dark = Math.min(L1, L2);
      return (light + 0.05) / (dark + 0.05);
    };

    const nearestOpaqueBg = (node) => {
      let current = node;
      while (current) {
        const bg = colorParse(getComputedStyle(current).backgroundColor);
        if (bg) {
          if (bg[3] >= 0.999) return bg;
          const parent = current.parentElement;
          const parentBg = parent ? nearestOpaqueBg(parent) : [255, 255, 255, 1];
          return blend(bg, parentBg);
        }
        current = current.parentElement;
      }
      return [255, 255, 255, 1];
    };

    const tests = [];
    for (const test of window.__pwPayload.contrastTests) {
      const target = document.querySelector(test.focusSelector);
      const element = test.mode === 'text' ? document.querySelector(test.selector) : target;
      if (!target || !element) {
        tests.push({ id: test.id, pass: false, failReason: 'missing-element' });
        continue;
      }

      if (test.mode === 'text') {
        const textColor = colorParse(getComputedStyle(element).color);
        const bg = nearestOpaqueBg(element);
        if (!textColor) {
          tests.push({ id: test.id, pass: false, failReason: 'missing-text-color' });
          continue;
        }
        const effectiveText = textColor[3] < 1 ? blend(textColor, bg) : textColor;
        const ratio = contrastRatio(effectiveText, bg);
        tests.push({
          id: test.id,
          selector: test.selector,
          ratio,
          threshold: test.threshold,
          pass: ratio >= test.threshold,
          color: `rgb(${textColor.slice(0, 3).join(',')})`,
          background: `rgb(${bg.slice(0, 3).join(',')})`,
        });
        continue;
      }

      target.focus({ preventScroll: true });
      const outline = colorParse(getComputedStyle(target).outlineColor);
      if (!outline) {
        tests.push({ id: test.id, pass: false, failReason: 'no-outline', selector: test.selector });
        continue;
      }
      const bg = nearestOpaqueBg(target);
      const effectiveOutline = outline[3] < 1 ? blend(outline, bg) : outline;
      const ratio = contrastRatio(effectiveOutline, bg);
      tests.push({
        id: test.id,
        selector: test.selector,
        ratio,
        threshold: test.threshold,
        pass: ratio >= test.threshold,
        color: `rgb(${outline.slice(0, 3).join(',')})`,
        background: `rgb(${bg.slice(0, 3).join(',')})`,
      });
    }

    const wrapping = window.__pwPayload.wrapping.map((selector) => {
      const el = document.querySelector(selector);
      if (!el) return { selector, pass: false, reason: 'missing-element' };
      const clipped = Math.round(el.scrollWidth) > Math.round(el.clientWidth);
      return {
        selector,
        pass: !clipped,
        scrollWidth: Math.round(el.scrollWidth),
        clientWidth: Math.round(el.clientWidth),
        whiteSpace: getComputedStyle(el).whiteSpace,
        overflowX: getComputedStyle(el).overflowX,
      };
    });

    return { tests, wrapping };
  });

  report.push({ width, ...result });
}

await browser.close();
console.log('@@@ CONTRAST REPORT START');
console.log(JSON.stringify({ report }, null, 2));
