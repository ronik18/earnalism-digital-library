// The map contains source anchors and measured boundaries, never manuscript HTML.
export function authorizedBookPlans(manifest, protectedAccess, makePlan) {
  const rows = manifest?.canonical_pages?.pages || [];
  const plans = []; const seen = new Set();
  for (const row of rows) {
    const index = Number(row.page_number || row.page_index);
    if (seen.has(row.chapter_id) || (!protectedAccess && index > Number(manifest.canonical_pages.preview_policy?.public_limit || 3))) continue;
    const plan = makePlan(manifest, index, protectedAccess);
    if (plan.rows.length && !seen.has(plan.chapterId)) { seen.add(plan.chapterId); plans.push(plan); }
  }
  return plans;
}

export function measuredChapterEntry(window, pages, sourceAnchor) {
  let end = 0;
  const boundaries = pages.map(page => {
    if (page.start !== end || page.end < page.start) throw new Error('Non-contiguous authorized visual map');
    end = page.end;
    return { start: page.start, end: page.end, structures: page.structures, anchor: sourceAnchor(page.anchor ?? page.start) };
  });
  if (end !== window.textLength) throw new Error('Authorized visual map does not cover its source');
  return { key: window.plan.key, chapterId: window.plan.chapterId, boundaries };
}

export function bookPageDomain(plans, entries, currentKey, localIndex) {
  const options = []; let prefixKnown = true; let currentNumber = null;
  let cumulative = 0;
  for (const plan of plans) {
    const entry = entries[plan.key];
    if (!entry) { prefixKnown = false; continue; }
    entry.boundaries.forEach((boundary, index) => {
      const number = prefixKnown ? cumulative + index + 1 : null;
      options.push({ ...boundary, key: `${plan.key}:${index}`, chapterId: plan.chapterId,
        label: number ? `Page ${number}` : `${plan.chapterTitle || "Chapter"} · page ${index + 1}`, number });
      if (plan.key === currentKey && index === localIndex) currentNumber = number;
    });
    if (prefixKnown) cumulative += entry.boundaries.length;
  }
  const complete = plans.length > 0 && plans.every(plan => entries[plan.key]);
  return { options, currentNumber, total: complete ? options.length : null, complete };
}
