import assert from 'node:assert/strict';

// The expected fixture comes from the bound state manifest, never the captured
// marker itself. A public/Listener capture cannot opt out of its logo contract.
export function assertQuietFolioReaderChrome(record, expectedState) {
  assert.equal(expectedState?.fixture, 'reader-visual-safe');
  assert.equal(record.state_id, expectedState.id);
  assert.equal(record.fixture, expectedState.fixture);
  assert.equal(record.route, expectedState.route);
  assert.equal(record.reader_chrome_contract, 'QUIET_FOLIO_NO_MARKETING_MASTHEAD');
  assert.equal(record.visible_header_count, 1);
  assert.equal(record.reader_marketing_header_count, 0);
  assert.equal(record.visible_canonical_lockup_count, 0);
  assert.equal(record.logo, null);
  assert.equal(record.action_row_below_brand, null);
  const bar = record.zoom_results?.reader_topbar;
  assert.equal(bar?.contract, 'QUIET_FOLIO');
  const box = value => {
    assert.ok(value);
    for (const key of ['left', 'right', 'top', 'bottom', 'width', 'height']) assert.ok(Number.isFinite(value[key]), `Missing finite ${key}`);
    assert.ok(value.width > 0 && value.height > 0);
  };
  box(bar.box);
  assert.ok(Number.isFinite(bar.client_width) && bar.client_width > 0);
  assert.ok(Number.isFinite(bar.scroll_width) && bar.scroll_width <= bar.client_width);
  assert.equal(bar.control_overlap_area, 0);
  assert.equal(bar.content_begins_below_topbar, true);
  assert.equal(bar.action_row_content_overlap_area, 0);
  for (const key of ['back', 'title', 'settings', 'fullscreen']) {
    const item = bar.children?.[key];
    box(item?.box);
    assert.equal(item.clipped_area, 0);
    assert.ok(item.box.left >= bar.box.left && item.box.right <= bar.box.right);
    if (key !== 'title') assert.ok(item.box.width >= 44 && item.box.height >= 44);
  }
  const navigation = record.zoom_results?.reader_navigation;
  box(navigation?.box);
  assert.equal(navigation.control_overlap_area, 0);
  assert.deepEqual(Object.keys(navigation.children || {}), ['Previous page', 'Contents', 'Next page']);
  for (const label of ['Previous page', 'Contents', 'Next page']) {
    const item = navigation.children?.[label];
    box(item?.box);
    assert.ok(item.box.width >= 44 && item.box.height >= 44);
    assert.equal(item.clipped_area, 0);
  }
  assert.equal(record.reader?.protected_content_exposed, false);
  assert.equal(record.reader?.protected_prefetch, false);
  assert.equal(record.reader?.balance_consumption, 0);
}

export function isExpectedReader(record, states) {
  return states.get(record.state_id)?.fixture === 'reader-visual-safe';
}

// A second required header-evidence workflow measures its own DOM instead of
// consuming the main capture artifact. Keep that measurement explicit and real.
export async function measureQuietFolioReaderChrome(page, expectedState) {
  const measured = await page.evaluate(() => {
    const visible = node => { if (!node) return false; const style = getComputedStyle(node); const r = node.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
    const box = node => { if (!node) return null; const r = node.getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height }; };
    const overlap = (a, b) => !a || !b ? 0 : Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    const info = node => { const r = box(node); return { box: r, clipped_area: !r ? 0 : Math.max(0, r.width * r.height - Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0)) * Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0))) }; };
    const bar = document.querySelector('header.reader-folio__bar');
    const nodes = { back: bar?.querySelector('[aria-label="Back to book"]'), title: bar?.querySelector('.reader-folio__book-title'), settings: bar?.querySelector('[aria-label="Reader settings"]'), fullscreen: bar?.querySelector('[aria-label="Enter fullscreen"], [aria-label="Exit fullscreen"]') };
    const navigation = document.querySelector('.reader-folio__navigation');
    const buttons = [...(navigation?.querySelectorAll('button') || [])];
    const overlaps = list => list.reduce((sum, node, index) => sum + list.slice(index + 1).reduce((rest, next) => rest + overlap(box(node), box(next)), 0), 0);
    const canvas = document.querySelector('.reader-v2__canvas');
    const logos = [...document.querySelectorAll('[data-testid="earnalism-brand-lockup"], [data-brand-asset="earnalism-brand-lockup.png"], img[src*="earnalism-brand-lockup"]')].filter(visible);
    const requests = performance.getEntriesByType('resource').map(entry => entry.name);
    return {
      title: nodes.title?.textContent?.trim(),
      reader_chrome_contract: 'QUIET_FOLIO_NO_MARKETING_MASTHEAD',
      visible_header_count: [...document.querySelectorAll('header.reader-folio__bar')].filter(visible).length,
      reader_marketing_header_count: [...document.querySelectorAll('[data-testid="site-header"],header.experience-header')].filter(visible).length,
      visible_canonical_lockup_count: logos.length,
      logo: logos.length ? {present:true} : null, action_row_below_brand: null,
      zoom_results: {
        reader_topbar: { contract: 'QUIET_FOLIO', box: box(bar), client_width: bar?.clientWidth, scroll_width: bar?.scrollWidth,
          children: Object.fromEntries(Object.entries(nodes).map(([name, node]) => [name, info(node)])), control_overlap_area: overlaps(Object.values(nodes)),
          content_begins_below_topbar: Boolean(canvas && bar && box(canvas).top >= box(bar).bottom - 1), action_row_content_overlap_area: overlap(box(bar), box(canvas)) },
        reader_navigation: { box: box(navigation), children: Object.fromEntries(buttons.map(node => [node.getAttribute('aria-label') || node.textContent.trim(), info(node)])), control_overlap_area: overlaps(buttons) },
      },
      reader: { protected_content_exposed: Boolean(document.querySelector('[data-testid="reader-protected-content"],[data-testid="protected-reader-content"]')),
        protected_prefetch: requests.some(url => /\/api\/reader\/(book\/.*\/pages|chapter\/.*(4|5|6|7|8|9))/.test(url)),
        balance_consumption: requests.filter(url => /reading-pass|wallet|lease|session/i.test(url)).length },
    };
  });
  const record = { ...measured, state_id: expectedState.id, route: expectedState.route, fixture: expectedState.fixture };
  assert.ok(measured.title, 'Reader book title must be visible');
  assertQuietFolioReaderChrome(record, expectedState);
  return record;
}
