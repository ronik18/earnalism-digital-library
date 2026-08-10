import { Link } from "react-router-dom";
import { BookOpen, X } from "lucide-react";
import { trackFunnelEvent } from "../../lib/funnelAnalytics";

export default function ReaderUpsellPrompt({ book, chapter, onDismiss }) {
  const checkoutPath = "/pricing?pack=1h&source=reader_finish";

  const metadata = {
    book_slug: book?.slug,
    book_title: book?.title,
    chapter_id: chapter?.id,
    chapter_title: chapter?.title,
    pack_id: "1h",
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
        <h3>Ready to continue? <em>The Quiet Hour</em> adds 60 minutes of reading time for ₹89.</h3>
        <Link
          to={checkoutPath}
          className="reader-upsell__cta"
          onClick={() => trackFunnelEvent("reader_upsell_cta_click", metadata)}
        >
          View the ₹89 pass
        </Link>
      </div>
    </aside>
  );
}
