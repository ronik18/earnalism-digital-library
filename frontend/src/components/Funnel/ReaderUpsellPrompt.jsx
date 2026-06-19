import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Clock, X } from "lucide-react";
import { trackFunnelEvent } from "../../lib/funnelAnalytics";
import {
  couponRemainingMs,
  EVENING_COUPON_CODE,
  EVENING_COUPON_DISCOUNT,
  EVENING_COUPON_DURATION_MS,
  formatCouponCountdown,
  getOrCreateEveningCoupon,
} from "../../lib/funnelOffers";

export default function ReaderUpsellPrompt({ book, chapter, onDismiss }) {
  const coupon = useMemo(() => getOrCreateEveningCoupon(), []);
  const [remainingMs, setRemainingMs] = useState(() => couponRemainingMs(coupon.expiresAt));
  const timerPct = Math.max(0, Math.min(100, (remainingMs / EVENING_COUPON_DURATION_MS) * 100));
  const checkoutPath = `/pricing?pack=1h&coupon=${EVENING_COUPON_CODE}&source=reader_finish`;

  useEffect(() => {
    const id = setInterval(() => setRemainingMs(couponRemainingMs(coupon.expiresAt)), 30000);
    return () => clearInterval(id);
  }, [coupon.expiresAt]);

  const metadata = {
    book_slug: book?.slug,
    book_title: book?.title,
    chapter_id: chapter?.id,
    chapter_title: chapter?.title,
    pack_id: "1h",
    coupon: EVENING_COUPON_CODE,
  };

  return (
    <aside className="reader-upsell" aria-label="Continue reading offer">
      <button
        type="button"
        className="reader-upsell__dismiss"
        onClick={onDismiss}
        aria-label="Dismiss reading offer"
      >
        <X size={15} />
      </button>

      <div className="reader-upsell__icon" aria-hidden="true">
        <BookOpen size={18} />
      </div>
      <div className="reader-upsell__body">
        <p className="reader-upsell__eyebrow">After this read</p>
        <h3>Enjoyed this read? Continue with <em>The Quiet Hour</em> at ₹89 — saving {EVENING_COUPON_DISCOUNT}%.</h3>
        <div className="reader-upsell__timer" aria-label={`Coupon expires in ${formatCouponCountdown(remainingMs)}`}>
          <div className="reader-upsell__timer-track">
            <span style={{ width: `${timerPct}%` }} />
          </div>
          <span><Clock size={13} /> {formatCouponCountdown(remainingMs)} left</span>
        </div>
        <Link
          to={checkoutPath}
          className="reader-upsell__cta"
          onClick={() => trackFunnelEvent("reader_upsell_cta_click", metadata)}
        >
          Continue with ₹89
        </Link>
      </div>
    </aside>
  );
}
