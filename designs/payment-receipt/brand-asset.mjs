/** Exact production header lockup. Never redraw, recolour or typeset a substitute. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

export const BRAND_ORIGIN = 'https://theearnalism.com/assets/brand/earnalism-brand-lockup.png';
export const BRAND_SHA256 = '951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919';
const bytes = readFileSync(new URL('./assets/earnalism-brand-lockup.png', import.meta.url));
if (createHash('sha256').update(bytes).digest('hex') !== BRAND_SHA256) {
  throw new Error('Brand asset differs from the verified production header lockup. Review provenance before using a replacement.');
}
export const BRAND_DATA_URI = 'data:image/png;base64,' + bytes.toString('base64');
