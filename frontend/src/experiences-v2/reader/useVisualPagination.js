import { useLayoutEffect, useRef, useState } from 'react';
import { paginateRenderedResponsive } from './visualPagination';

export default function useVisualPagination({ sourceRef, viewportRef, measureRef, revision, typography }) {
  const [result, setResult] = useState({ pages: [], pending: true, error: '', signature: '' });
  const cache = useRef(new Map());
  const geometry = useRef('');
  useLayoutEffect(() => {
    let cancelled = false; let timer; let generation = 0;
    const viewport = viewportRef.current; const source = sourceRef.current; const measure = measureRef.current;
    if (!viewport || !source || !measure) return undefined;
    const calculate = async () => {
      const version = ++generation;
      const superseded = () => cancelled || version !== generation;
      if (superseded()) return;
      setResult(previous => ({ ...previous, pending: true }));
      // Hidden measurement text may not itself trigger web-font loading.
      const stylesheets = [...document.querySelectorAll('link[rel="stylesheet"]')].filter(link => !link.sheet);
      if (stylesheets.length) await Promise.all(stylesheets.map(link => new Promise(resolve => {
        link.addEventListener('load', resolve, { once: true });
        link.addEventListener('error', resolve, { once: true });
      })));
      if (document.fonts) {
        const font = getComputedStyle(source);
        try {
          await document.fonts.load(`${font.fontWeight} ${font.fontSize} ${font.fontFamily}`);
          await document.fonts.ready;
        } catch {
          if (!superseded()) setResult({ pages: [], pending: false, error: 'Reader typography could not be prepared. Reload this page to retry.', signature: '' });
          return;
        }
      }
      const images = [...source.querySelectorAll('img')];
      if (images.length) await Promise.all(images.map(async image => {
        image.loading = 'eager';
        if (typeof image.decode === 'function') await image.decode().catch(() => undefined);
      }));
      if (superseded()) return;
      const measureLayout = async () => {
        if (superseded()) return;
        const width = viewport.clientWidth; const height = viewport.clientHeight;
        // A hidden/non-rendered route cannot supply a meaningful layout yet.
        if (!width || !height) return;
        geometry.current = `${width}:${height}`;
        const style = getComputedStyle(source);
        const signature = [revision, width, height, style.fontFamily, style.fontSize, style.lineHeight, style.fontWeight, source.innerHTML].join('|');
        try {
          measure.style.width = `${width}px`;
          viewport.style.setProperty('--reader-visual-height', `${height}px`);
          measure.style.setProperty('--reader-visual-height', `${height}px`);
          measure.style.fontFamily = style.fontFamily;
          measure.style.fontSize = style.fontSize;
          measure.style.lineHeight = style.lineHeight;
          measure.style.fontWeight = style.fontWeight;
          const started = performance.now();
          const cached = cache.current.get(signature);
          const calculation = cached?.pages || paginateRenderedResponsive(source, measure, height, { cancelled: superseded });
          const pages = typeof calculation?.then === 'function' ? await calculation : calculation;
          if (superseded()) return;
          if (!cached) {
            cache.current.set(signature, { pages, durationMs: performance.now() - started });
            while (cache.current.size > 4) cache.current.delete(cache.current.keys().next().value);
          }
          setResult({ pages, pending: false, error: '', signature, durationMs: cache.current.get(signature).durationMs, cached: Boolean(cached), height, width });
        } catch (error) {
          if (superseded()) return;
          setResult({ pages: [], pending: false, error: 'This content cannot be safely paginated in this layout.', errorReason: error.message, signature });
        } finally { if (!superseded()) measure.replaceChildren(); }
      };
      measureLayout();
    };
    const schedule = () => {
      generation++;
      clearTimeout(timer);
      // Hide incompatible fragments immediately; do not display clipped content.
      setResult(previous => ({ ...previous, pending: true }));
      timer = setTimeout(calculate, 80);
    };
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(() => { if (geometry.current !== `${viewport.clientWidth}:${viewport.clientHeight}`) schedule(); }) : null;
    observer?.observe(viewport);
    window.addEventListener('resize', schedule);
    window.visualViewport?.addEventListener('resize', schedule);
    const fontsChanged = () => { cache.current.clear(); schedule(); };
    document.fonts?.addEventListener('loadingdone', fontsChanged);
    void calculate();
    return () => {
      cancelled = true; clearTimeout(timer); observer?.disconnect();
      window.removeEventListener('resize', schedule);
      window.visualViewport?.removeEventListener('resize', schedule);
      document.fonts?.removeEventListener('loadingdone', fontsChanged);
    };
  }, [sourceRef, viewportRef, measureRef, revision, typography]);
  return result;
}
