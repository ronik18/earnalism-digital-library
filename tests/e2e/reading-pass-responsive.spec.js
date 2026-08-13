const fs = require('node:fs');
const path = require('node:path');
const { expect, test } = require('playwright/test');

const componentCss = fs.readFileSync(
  path.resolve('frontend/src/components/ReadingPass/ReadingPass.css'),
  'utf8',
);

const viewports = [
  { label: '320', width: 320, height: 700 },
  { label: '360', width: 360, height: 780 },
  { label: '390', width: 390, height: 844 },
  { label: '768', width: 768, height: 1024 },
  { label: '1024', width: 1024, height: 768 },
  { label: '1440', width: 1440, height: 900 },
  { label: 'mobile-landscape', width: 667, height: 375 },
  { label: 'desktop-200-percent-zoom-equivalent', width: 720, height: 450 },
];

function fixture() {
  return `<!doctype html>
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <style>
      * { box-sizing: border-box; }
      html, body { margin: 0; width: 100%; min-height: 100%; overflow-x: clip; }
      button { background: transparent; }
      ${componentCss}
    </style>
    <main style="min-height:1200px;padding:100px 16px 180px"><h1>Reader fixture</h1><p>Protected canonical page.</p></main>
    <aside class="reading-pass-timer" data-status="running" aria-label="Reading Pass status">
      <button class="reading-pass-timer__main"><span class="reading-pass-timer__time">00:05:00</span><span class="reading-pass-timer__state"><strong>Running</strong><small>Reading</small></span></button>
      <button class="reading-pass-timer__topup" aria-label="Add Reading Pass time">+</button>
    </aside>
    <div class="reading-pass-paywall">
      <div class="reading-pass-paywall__backdrop"></div>
      <section class="reading-pass-paywall__dialog" role="dialog" aria-modal="true">
        <button class="reading-pass-paywall__close" aria-label="Close">×</button>
        <span class="reading-pass-paywall__eyebrow">READING PASS</span>
        <h2>The free preview ends here.</h2>
        <p>Sign in and add reading time to continue. Your place is already saved.</p>
        <div class="reading-pass-paywall__balance"><span>Current balance</span><strong>300 seconds</strong></div>
        <div class="reading-pass-paywall__actions"><button class="reading-pass-paywall__primary">Continue reading</button><button>Return to free preview</button></div>
      </section>
    </div>`;
}

for (const viewport of viewports) {
  test(`Reading Pass controls fit ${viewport.label}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.setContent(fixture());
    const result = await page.evaluate(() => {
      const timer = document.querySelector('.reading-pass-timer').getBoundingClientRect();
      const dialog = document.querySelector('.reading-pass-paywall__dialog').getBoundingClientRect();
      const controls = Array.from(document.querySelectorAll('button')).map((node) => node.getBoundingClientRect());
      return {
        viewportWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        timer,
        dialog,
        controls,
      };
    });
    expect(result.scrollWidth).toBeLessThanOrEqual(result.viewportWidth);
    expect(result.timer.left).toBeGreaterThanOrEqual(0);
    expect(result.timer.right).toBeLessThanOrEqual(viewport.width);
    expect(result.timer.bottom).toBeLessThanOrEqual(viewport.height);
    expect(result.dialog.left).toBeGreaterThanOrEqual(0);
    expect(result.dialog.right).toBeLessThanOrEqual(viewport.width);
    expect(result.dialog.top).toBeGreaterThanOrEqual(0);
    expect(result.dialog.bottom).toBeLessThanOrEqual(viewport.height);
    for (const control of result.controls) {
      expect(control.width).toBeGreaterThanOrEqual(44);
      expect(control.height).toBeGreaterThanOrEqual(44);
    }
  });
}
