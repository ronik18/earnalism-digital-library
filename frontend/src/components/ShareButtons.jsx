import { canonicalShareUrl } from "../lib/socialSharing";
import { toast } from "sonner";
import { Facebook, Link as LinkIcon, MessageCircle, Twitter, Linkedin } from "lucide-react";

/**
 * ShareButtons — premium, minimal row of share actions.
 * Props:
 *  - title: text to accompany the share
 *  - variant: "product" | "article" (controls which networks show)
 *  - testIdPrefix: optional override for data-testid prefix
 */
export default function ShareButtons({ title = "", variant = "product", testIdPrefix = "share", labelled = false }) {
  const url = typeof window !== "undefined" ? canonicalShareUrl(window.location.href) : "";
  const encUrl = encodeURIComponent(url);
  const encText = encodeURIComponent(title);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Link copied");
    } catch {
      toast.error("Could not copy link");
    }
  };

  const btn = "w-11 h-11 inline-flex items-center justify-center rounded-full border border-[var(--brand-border)] text-[var(--brand-charcoal-soft)] hover:text-[var(--brand-burgundy)] hover:border-[var(--brand-gold)] transition-colors";

  return (
    <div className="flex items-center gap-3" data-testid={`${testIdPrefix}-row`}>
      <span className="overline hidden sm:inline mr-1">Share</span>
      <a
        href={`https://wa.me/?text=${encText}%20${encUrl}`}
        target="_blank" rel="noreferrer"
        aria-label="Share on WhatsApp"
        data-testid={`${testIdPrefix}-whatsapp`}
        className={labelled ? `${btn} share-labelled` : btn}
      >
        <MessageCircle size={16} />{labelled && <span>WhatsApp</span>}
      </a>
      <a
        href={`https://www.facebook.com/sharer/sharer.php?u=${encUrl}`}
        target="_blank" rel="noreferrer"
        aria-label="Share on Facebook"
        data-testid={`${testIdPrefix}-facebook`}
        className={labelled ? `${btn} share-labelled` : btn}
      >
        <Facebook size={16} />{labelled && <span>Facebook</span>}
      </a>
      {variant === "article" && (
        <a
          href={`https://x.com/intent/tweet?url=${encUrl}&text=${encText}`}
          target="_blank" rel="noreferrer"
          aria-label="Share on X"
          data-testid={`${testIdPrefix}-twitter`}
          className={labelled ? `${btn} share-labelled` : btn}
        >
          <Twitter size={16} />{labelled && <span>X</span>}
        </a>
      )}
      {variant === "article" && <a href={`https://www.linkedin.com/sharing/share-offsite/?url=${encUrl}`} target="_blank" rel="noreferrer" aria-label="Share on LinkedIn" className={labelled ? `${btn} share-labelled` : btn}><Linkedin size={16} />{labelled && <span>LinkedIn</span>}</a>}
      <button onClick={copy} aria-label="Copy link" data-testid={`${testIdPrefix}-copy`} className={labelled ? `${btn} share-labelled` : btn} type="button">
        <LinkIcon size={16} />{labelled && <span>Copy link</span>}
      </button>
    </div>
  );
}
