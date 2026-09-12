// Presentation accepts only the offer shape owned by the checkout API. PackOut
// deliberately has no expiry field: an absent validity_days value means that
// this public response makes no expiry claim, not that it is malformed.
export function presentReadingPass(pack) {
  if (!pack || typeof pack.id !== "string" || !pack.id.trim()) return null;
  const { minutes, price_inr: price, amount_paise: amount, label, note, validity_days: days } = pack;
  if (typeof label !== "string" || !label.trim() || typeof note !== "string"
    || !Number.isInteger(minutes) || minutes <= 0
    || !Number.isInteger(price) || price < 0
    || !Number.isInteger(amount) || amount < 0) return null;
  if (days !== undefined && days !== null && (!Number.isInteger(days) || days <= 0)) return null;
  return { ...pack, minutes, price_inr: price, amount_paise: amount, validity_days: days ?? null, unitPrice: (price / minutes).toFixed(2) };
}

export function availableReadingPasses(packs) {
  const ids = new Set();
  return (Array.isArray(packs) ? packs : []).map(presentReadingPass).filter((pack) => {
    if (!pack || ids.has(pack.id)) return false;
    ids.add(pack.id);
    return true;
  });
}
