#!/usr/bin/env node
/* Strict automated contrast, clipping, and overflow gate for local System UAT. */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const baseUrl = String(process.env.UAT_BASE_URL || '').replace(/\/$/, '');
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) {
  throw new Error('UAT_BASE_URL must be an explicit loopback URL.');
}

const widths = [320, 360, 390, 430, 768, 1024];
const output = path.resolve(process.env.CONTRAST_OUTPUT || 'uat/evidence/system-final/contrast-final/contrast.log');
fs.mkdirSync(path.dirname(output), { recursive: true });
const summary = { tested: 0, passed: 0, failed: 0, missing: 0, na: 0, findings: [] };

const required = [
  { route: '/', selector: '[data-testid="home-reference-primary-cta"]', kind: 'text' },
  { route: '/pricing', selector: '[data-testid="pricing-reference-surface"] h1', kind: 'text' },
  { route: '/pricing', selector: '[data-testid="pricing-reference-wallet-explainer"]', kind: 'text' },
  { route: '/reader/dracula', selector: '.reader-topbar', kind: 'boundary' },
  { route: '/reader/dracula', selector: '.reader-topbar__center strong', kind: 'text' },
  { route: '/reader/dracula', selector: '.reader-topbar__center span', kind: 'text' },
];

function add(status, finding) {
  summary[status] += 1;
  summary.findings.push({ status, ...finding });
}

const browser = await chromium.launch({ headless: true });
try {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: { width, height: width < 600 ? 844 : 900 } });
    const checkedRoutes = new Set();
    for (const item of required) {
      if (!checkedRoutes.has(item.route)) {
        const response = await page.goto(`${baseUrl}${item.route}`, { waitUntil: 'domcontentloaded', timeout: 15_000 });
        await page.waitForTimeout(500);
        if (response?.status() !== 200) add('failed', { width, route: item.route, check: 'route-status', actual: response?.status() });
        checkedRoutes.add(item.route);
      }
      const locator = page.locator(item.selector);
      await locator.first().waitFor({ state: 'attached', timeout: 3_000 }).catch(() => {});
      if (await locator.count() !== 1) {
        add('missing', { width, route: item.route, selector: item.selector, check: 'required-element' });
        continue;
      }
      await locator.scrollIntoViewIfNeeded();
      const measured = await locator.evaluate((element, kind) => {
        const parse = (value) => {
          const nums = String(value).match(/[\d.]+/g)?.map(Number) || [];
          if (nums.length < 3) return null;
          const srgb = String(value).startsWith('color(srgb');
          return [
            srgb ? nums[0] * 255 : nums[0],
            srgb ? nums[1] * 255 : nums[1],
            srgb ? nums[2] * 255 : nums[2],
            nums.length > 3 ? nums[3] : 1,
          ];
        };
        const composite = (foreground, background) => foreground[3] >= 1
          ? foreground.slice(0, 3)
          : foreground.slice(0, 3).map((v, i) => Math.round(v * foreground[3] + background[i] * (1 - foreground[3])));
        const color = parse(getComputedStyle(element).color);
        const nodes = [];
        let node = element;
        while (node) {
          nodes.unshift(node);
          node = node.parentElement;
        }
        let background = [255, 255, 255];
        for (const ancestor of nodes) {
          const parsed = parse(getComputedStyle(ancestor).backgroundColor);
          if (parsed && parsed[3] > 0) {
            background = composite(parsed, background);
          }
        }
        const foreground = color ? composite(color, background) : null;
        const luminance = (rgb) => rgb.map((v) => {
          const s = v / 255;
          return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
        }).reduce((sum, v, index) => sum + v * [0.2126, 0.7152, 0.0722][index], 0);
        const ratio = foreground ? (Math.max(luminance(foreground), luminance(background)) + 0.05) /
          (Math.min(luminance(foreground), luminance(background)) + 0.05) : 0;
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return {
          ratio,
          fontSize: Number.parseFloat(style.fontSize) || 0,
          fontWeight: Number.parseInt(style.fontWeight, 10) || 400,
          rect: { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom },
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          ownScrollWidth: element.scrollWidth,
          ownClientWidth: element.clientWidth,
        };
      }, item.kind);
      summary.tested += 1;
      const large = measured.fontSize >= 24 || (measured.fontSize >= 18.66 && measured.fontWeight >= 700);
      const threshold = item.kind === 'boundary' ? 3 : (large ? 3 : 4.5);
      const clipped = measured.rect.left < -0.5 || measured.rect.right > width + 0.5 || measured.ownScrollWidth > measured.ownClientWidth + 1;
      const overflow = measured.scrollWidth > measured.clientWidth + 1;
      if (measured.ratio < threshold || clipped || overflow) {
        add('failed', { width, route: item.route, selector: item.selector, ratio: Number(measured.ratio.toFixed(2)), threshold, clipped, overflow });
      } else {
        add('passed', { width, route: item.route, selector: item.selector, ratio: Number(measured.ratio.toFixed(2)) });
      }
    }
    // Disabled Dracula audio deliberately has no listening control.  It is a
    // conditional N/A, never a required control or a pass credit.
    await page.goto(`${baseUrl}/reader/dracula`, { waitUntil: 'domcontentloaded', timeout: 15_000 });
    await page.waitForTimeout(500);
    if (await page.getByTestId('generated-audiobook').count() === 0) add('na', { width, route: '/reader/dracula', selector: '[data-testid="generated-audiobook"]', reason: 'controlled audio disabled' });
    else add('failed', { width, route: '/reader/dracula', selector: '[data-testid="generated-audiobook"]', check: 'disabled-audio-control-present' });
    await page.close();
  }
} finally {
  await browser.close();
}

const lines = [
  `tested=${summary.tested}`,
  `passed=${summary.passed}`,
  `failed=${summary.failed}`,
  `missing=${summary.missing}`,
  `n/a=${summary.na}`,
  JSON.stringify(summary.findings, null, 2),
];
fs.writeFileSync(output, `${lines.join('\n')}\n`);
console.log(lines.slice(0, 5).join(' '));
if (summary.failed > 0 || summary.missing > 0) process.exitCode = 1;
