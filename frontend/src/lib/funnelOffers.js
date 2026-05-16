export const EVENING_COUPON_CODE = "EVENING15";
export const EVENING_COUPON_DISCOUNT = 15;
export const EVENING_COUPON_DURATION_MS = 48 * 60 * 60 * 1000;

const EVENING_COUPON_KEY = "earnalism_evening_coupon_expires_at";
const READER_PROMPT_SESSION_KEY = "earnalism_reader_finish_prompt_shown";

export function getOrCreateEveningCoupon(now = Date.now()) {
  if (typeof window === "undefined") {
    return { code: EVENING_COUPON_CODE, expiresAt: now + EVENING_COUPON_DURATION_MS };
  }

  const stored = Number(localStorage.getItem(EVENING_COUPON_KEY) || 0);
  const expiresAt = stored > now ? stored : now + EVENING_COUPON_DURATION_MS;
  localStorage.setItem(EVENING_COUPON_KEY, String(expiresAt));
  return { code: EVENING_COUPON_CODE, expiresAt };
}

export function couponRemainingMs(expiresAt, now = Date.now()) {
  return Math.max(0, Number(expiresAt || 0) - now);
}

export function formatCouponCountdown(ms) {
  const totalMinutes = Math.max(0, Math.ceil(ms / 60000));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, "0")}m`;
  return `${minutes}m`;
}

export function canShowReaderFinishPrompt() {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem(READER_PROMPT_SESSION_KEY) !== "1";
}

export function markReaderFinishPromptShown() {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(READER_PROMPT_SESSION_KEY, "1");
  }
}
