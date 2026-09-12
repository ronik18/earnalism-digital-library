// Presentation accepts only the offer shape owned by the checkout API.
export function presentReadingPass(pack) {
  if (!pack || typeof pack.id !== "string" || !pack.id.trim()) return null;
  const { minutes, price_inr: price, validity_days: days } = pack;
  if (!Number.isFinite(minutes) || minutes <= 0 || !Number.isFinite(price) || price < 0 || !Number.isInteger(days) || days <= 0) return null;
  return { ...pack, minutes, price_inr: price, validity_days: days, unitPrice: (price / minutes).toFixed(2) };
}

export function availableReadingPasses(packs) {
  const ids = new Set();
  return (Array.isArray(packs) ? packs : []).map(presentReadingPass).filter((pack) => {
    if (!pack || ids.has(pack.id)) return false;
    ids.add(pack.id);
    return true;
  });
}
