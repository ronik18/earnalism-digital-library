// Fetch code only after navigation intent. This never fetches API/content data.
export function installRoutePrefetch({ document, window, loaders }) {
  const connection = window.navigator?.connection;
  if (connection?.saveData || /(^|-)2g$/.test(connection?.effectiveType || '')) return () => {};
  const loaded = new Set();
  const prefetch = (event) => {
    const anchor = event.target?.closest?.('a[href]');
    if (!anchor) return;
    const url = new URL(anchor.href, window.location.href);
    if (url.origin !== window.location.origin || url.pathname === window.location.pathname) return;
    const key = Object.keys(loaders).find(path => url.pathname === path || url.pathname.startsWith(path + '/'));
    if (!key || loaded.has(key)) return;
    loaded.add(key);
    Promise.resolve().then(loaders[key]).catch(() => loaded.delete(key));
  };
  document.addEventListener('pointerover', prefetch, { passive: true });
  document.addEventListener('focusin', prefetch);
  return () => {
    document.removeEventListener('pointerover', prefetch);
    document.removeEventListener('focusin', prefetch);
  };
}
