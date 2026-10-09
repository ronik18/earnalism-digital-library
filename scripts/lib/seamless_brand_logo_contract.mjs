import assert from "node:assert/strict";

const CANONICAL_LOGO_PATH = "/assets/brand/earnalism-brand-lockup.png";
const RESPONSIVE_LOGO_PATH = /^\/assets\/performance\/earnalism-brand-lockup-(320|640)\.(avif|webp)$/;
const BRAND_ALT = "The Earnalism — Read. Reflect. Remember.";

const pathname = (value, stateId, field) => {
  assert.ok(value, `${stateId}: logo ${field} is present`);
  return new URL(value, "http://earnalism.local").pathname;
};

/**
 * The canonical PNG remains the declared fallback.  Responsive derivatives are
 * permitted only when they are one of the reviewed local assets and retain the
 * same accessible lockup identity; arbitrary optimized images cannot pass.
 */
export function assertApprovedResponsiveLockup(logo, stateId) {
  assert.ok(logo, `${stateId}: visible brand lockup metadata`);
  assert.equal(pathname(logo.declared_src, stateId, "declared source"), CANONICAL_LOGO_PATH, `${stateId}: canonical logo fallback`);
  const rendered = pathname(logo.current_src, stateId, "rendered source");
  const derivative = rendered.match(RESPONSIVE_LOGO_PATH);
  assert.ok(rendered === CANONICAL_LOGO_PATH || derivative, `${stateId}: canonical logo or approved local responsive derivative only`);
  assert.equal(logo.alt, BRAND_ALT, `${stateId}: canonical logo accessible name`);
  if (derivative) {
    const width = Number(derivative[1]);
    assert.equal(logo.natural_width, width, `${stateId}: derivative width matches its approved filename`);
    assert.equal(logo.natural_height, Math.round(width * 0.3), `${stateId}: derivative preserves approved lockup ratio`);
  } else {
    assert.equal(logo.natural_width, 2400, `${stateId}: canonical width`);
    assert.equal(logo.natural_height, 720, `${stateId}: canonical height`);
  }
}
