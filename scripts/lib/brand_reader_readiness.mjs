// Uses the Reader's existing DOM contract. No source text, timers, or product
// state are changed; this predicate runs before the capture interval.
export function readerCaptureReadiness() {
  const viewport = document.querySelector('.reader-v2__visual-viewport');
  const content = document.querySelector('[data-testid="reader-reading-text"]');
  const style = content && getComputedStyle(content);
  const rect = content?.getBoundingClientRect();
  return {
    paginationReady: viewport?.getAttribute('data-pagination-ready') === 'true',
    loading: Boolean(document.querySelector('.reader-v2__pagination-opening,.reader-v2__pagination-status,.reader-v2__page-loading,[data-testid="reader-opening"]')),
    visibleContentPresent: Boolean(content && style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0),
  };
}

export async function waitForSettledReader(page, state, context) {
  if (!state.route.startsWith('/reader/')) return { applicable: false };
  try {
    const handle = await page.waitForFunction(`(() => {
      const status = (${readerCaptureReadiness.toString()})();
      return status.paginationReady && !status.loading && status.visibleContentPresent ? status : false;
    })()`, undefined, { timeout: 10000, polling: 'raf' });
    try { return { applicable: true, ...await handle.jsonValue() }; }
    finally { await handle.dispose(); }
  } catch (error) {
    const status = await page.evaluate(readerCaptureReadiness).catch(() => ({ paginationReady: null, loading: null, visibleContentPresent: null }));
    throw new Error(`Reader capture readiness failed: ${JSON.stringify({ stateId: state.id, route: state.route, viewport: context.viewport, ...status })}`, { cause: error });
  }
}
