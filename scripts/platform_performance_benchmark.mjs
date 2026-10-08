import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { gzipSync, brotliCompressSync } from 'node:zlib';

const require = createRequire(path.resolve('frontend/package.json'));
const { chromium } = require('playwright');
const build = path.resolve(process.env.PERF_BUILD_ROOT || 'frontend/build');
const output = path.resolve(process.argv[2] || '/tmp/earnalism-performance-baseline.json');
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  const candidate = path.resolve(build, '.' + pathname);
  if (!candidate.startsWith(build + path.sep) && candidate !== build) { res.writeHead(403).end(); return; }
  const file = fs.existsSync(candidate) && fs.statSync(candidate).isFile() ? candidate : path.join(build, 'index.html');
  const types = { '.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.json': 'application/json', '.woff2': 'font/woff2', '.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
  res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
  const body = fs.readFileSync(file);
  res.end(path.extname(file) === '.html' && process.env.PERF_ACCOUNT_RESERVATION_BASELINE === '1'
    ? body.toString().replace('<head>', '<head><style>#main-content{min-height:0!important}</style>') : body);
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ headless: true });
const viewport = JSON.parse(process.env.PERF_VIEWPORT || '{"width":1440,"height":900}');
const routes = process.env.PERF_ROUTES ? JSON.parse(process.env.PERF_ROUTES) : ['/', '/library', '/book/a-ghost-story', '/reader/a-ghost-story', '/pricing', '/login', '/account', '/journal'];
const results = [];
const memory = [];
try {
  for (const route of routes) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    // Prevent this isolated audit from sending any requests to production.
    await page.route('**/*', async intercepted => {
      const url = new URL(intercepted.request().url());
      if (url.origin === base && !url.pathname.startsWith('/api/')) return intercepted.continue();
      if (url.pathname.includes('/auth/')) return intercepted.fulfill({ status: 401, json: { detail: 'Anonymous performance fixture' } });
      return intercepted.fulfill({ status: 200, json: [] });
    });
    await page.addInitScript(() => {
      window.__perf = { lcp: null, cls: 0, shifts: [], longTasks: [], interactions: [] };
      for (const [type, handler] of [
        ['largest-contentful-paint', e => { window.__perf.lcp = e.startTime; }],
        ['layout-shift', e => { if (!e.hadRecentInput) { window.__perf.cls += e.value; window.__perf.shifts.push({time: e.startTime, value: e.value, sources: e.sources.map(s => ({node: s.node?.tagName, className: typeof s.node?.className === 'string' ? s.node.className : '', previous: s.previousRect, current: s.currentRect}))}); } }],
        ['longtask', e => window.__perf.longTasks.push(e.duration)],
        ['event', e => { if (e.interactionId) window.__perf.interactions.push(e.duration); }],
      ]) { try { new PerformanceObserver(l => l.getEntries().forEach(handler)).observe({ type, buffered: true, durationThreshold: 16 }); } catch {} }
    });
    const cdp = await context.newCDPSession(page);
    await cdp.send('Performance.enable');
    await cdp.send('Profiler.enable');
    await cdp.send('Profiler.startPreciseCoverage', { callCount: false, detailed: true });
    await cdp.send('Tracing.start', { categories: 'devtools.timeline,blink.user_timing,loading', transferMode: 'ReturnAsStream' });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(base + route, { waitUntil: 'load' });
    await page.waitForTimeout(7000);
    if (process.env.PERF_SCREENSHOTS === '1') await page.screenshot({ path: output.replace(/\.json$/, '') + '-' + results.length + '.png' });
    const data = await page.evaluate(() => {
      const n = performance.getEntriesByType('navigation')[0];
      const resources = performance.getEntriesByType('resource');
      const sum = filter => resources.filter(filter).reduce((v, e) => v + e.decodedBodySize, 0);
      return { ...window.__perf, ttfb_ms: n.responseStart - n.requestStart, fcp_ms: performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? null,
        dom_content_loaded_ms: n.domContentLoadedEventEnd, load_ms: n.loadEventEnd,
        requests: resources.length, resource_bytes: sum(() => true), js_bytes: sum(e => /\.js($|\?)/.test(e.name)), css_bytes: sum(e => /\.css($|\?)/.test(e.name)),
        fonts: resources.filter(e => /\.(woff2?|ttf)($|\?)/.test(e.name)).length,
        font_resources: resources.filter(e => /\.(woff2?|ttf)($|\?)/.test(e.name)).map(e => ({path: new URL(e.name).pathname, bytes: e.decodedBodySize, duration_ms: e.duration})),
        font_faces: [...document.fonts].map(f => ({family: f.family, weight: f.weight, style: f.style, status: f.status})),
        images: [...document.images].map(i => ({src: i.currentSrc ? new URL(i.currentSrc).pathname : '', natural_width: i.naturalWidth, natural_height: i.naturalHeight, rendered_width: i.getBoundingClientRect().width, rendered_height: i.getBoundingClientRect().height, bytes: resources.find(e => e.name === i.currentSrc)?.decodedBodySize ?? null, loading: i.loading, sizes: i.sizes, srcset: i.srcset})),
        decoded_image_memory_bytes: [...document.images].reduce((v, i) => v + i.naturalWidth * i.naturalHeight * 4, 0),
        dom_nodes: document.getElementsByTagName('*').length,
        overflow: document.documentElement.scrollWidth > innerWidth,
        route_chunks: resources.filter(e => /chunk\.js/.test(e.name)).map(e => new URL(e.name).pathname),
      };
    });
    const metrics = (await cdp.send('Performance.getMetrics')).metrics;
    data.script_ms = (metrics.find(m => m.name === 'ScriptDuration')?.value ?? 0) * 1000;
    data.layout_ms = (metrics.find(m => m.name === 'LayoutDuration')?.value ?? 0) * 1000;
    data.heap_bytes = metrics.find(m => m.name === 'JSHeapUsedSize')?.value ?? null;
    const coverage = (await cdp.send('Profiler.takePreciseCoverage')).result;
    data.executed_js_bytes = coverage.reduce((sum, script) => sum + script.functions.flatMap(f => f.ranges).filter(r => r.count > 0).reduce((s, r) => s + r.endOffset - r.startOffset, 0), 0);
    const traceComplete = new Promise(resolve => cdp.once('Tracing.tracingComplete', resolve));
    await cdp.send('Tracing.end');
    const { stream } = await traceComplete;
    let trace = ''; while (true) { const chunk = await cdp.send('IO.read', { handle: stream }); trace += chunk.data; if (chunk.eof) break; }
    await cdp.send('IO.close', { handle: stream });
    const tracePath = output.replace(/\.json$/, '') + '-' + (route.replaceAll('/', '_') || 'home') + '-' + results.length + '.trace.json';
    fs.writeFileSync(tracePath, trace);
    const routeLink = page.locator('a[href="/library"]').first();
    if (route === '/' && await routeLink.count()) {
      await routeLink.focus();
      await page.waitForTimeout(500);
      data.library_intent_chunk_loaded = await page.evaluate(() => performance.getEntriesByType('resource').filter(e => /chunk\.js/.test(e.name)).length);
    }
    results.push({ route, ...data, errors, trace: tracePath });
    await context.close();
  }
  if (process.env.PERF_MEMORY === '1') {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    await page.route('**/*', r => new URL(r.request().url()).origin === base && !new URL(r.request().url()).pathname.startsWith('/api/')
      ? r.continue() : r.fulfill({ status: new URL(r.request().url()).pathname.includes('/auth/') ? 401 : 200, json: [] }));
    await page.goto(base, { waitUntil: 'load' });
    const cdp = await context.newCDPSession(page); await cdp.send('Performance.enable');
    for (let cycle = 0; cycle < 5; cycle++) {
      for (const target of ['/library', '/book/a-ghost-story', '/reader/a-ghost-story', '/library', '/reader/a-ghost-story', '/']) {
        await page.evaluate(url => { history.pushState({}, '', url); dispatchEvent(new PopStateEvent('popstate')); }, target);
        await page.waitForTimeout(250);
      }
      await cdp.send('HeapProfiler.collectGarbage');
      const metrics = (await cdp.send('Performance.getMetrics')).metrics;
      memory.push({ cycle: cycle + 1, retained_heap_bytes: metrics.find(m => m.name === 'JSHeapUsedSize')?.value,
        ...(await cdp.send('Memory.getDOMCounters')) });
    }
    await context.close();
  }
  const bundles = fs.readdirSync(path.join(build, 'static/js')).filter(f => f.endsWith('.js')).map(file => {
    const bytes = fs.readFileSync(path.join(build, 'static/js', file));
    return { file, raw: bytes.length, gzip: gzipSync(bytes).length, brotli: brotliCompressSync(bytes).length };
  }).sort((a,b) => b.raw - a.raw);
  fs.writeFileSync(output, JSON.stringify({ revision: process.env.PERF_REVISION || execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(), captured_at: new Date().toISOString(), environment: 'LOOPBACK_PRODUCTION_BUILD_EMPTY_API_ANONYMOUS', browser: browser.version(), viewport, samples_per_route: 1, production_requests: 0, memory, limitations: ['No authenticated Reader fixture or backend timing; empty API fixtures measure shell costs only.', 'Lab LCP/CLS are not field p75 CWV; no INP without interaction.', 'JS coverage ranges overlap and are diagnostic, not unique unused-byte totals.'], routes: results, bundles }, null, 2) + '\n');
  console.log(output);
} finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
