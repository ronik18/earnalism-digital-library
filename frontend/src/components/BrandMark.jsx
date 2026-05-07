import { useSettings } from "../context/SettingsContext";

const ALT = "The Earnalism Digital Library logo";

/**
 * BrandMark — renders the brand identity. If admin has uploaded a logo URL via
 * Settings → Brand, it shows the image. Otherwise it falls back to the existing
 * premium serif text mark. The image height is capped so an oversized upload
 * cannot blow out the layout.
 *
 * Props:
 *   variant: "header" | "footer" | "auth" | "compact"
 *           — picks size + whether the "Digital Library" italic suffix shows.
 *   className: extra wrapper classes.
 */
export default function BrandMark({ variant = "header", className = "" }) {
  const { brand } = useSettings();
  const logo = brand?.logo_url || "";

  // Bounded heights — never let an admin upload distort the page.
  const imgClass = {
    header: "h-7 sm:h-9 w-auto max-w-[200px] object-contain",
    footer: "h-9 sm:h-10 w-auto max-w-[220px] object-contain",
    auth: "h-10 w-auto max-w-[220px] object-contain",
    compact: "h-6 w-auto max-w-[140px] object-contain",
  }[variant] || "h-8 w-auto max-w-[200px] object-contain";

  if (logo) {
    return (
      <span className={`inline-flex items-center ${className}`} data-testid="brand-mark">
        <img src={logo} alt={ALT} loading="lazy" decoding="async" className={imgClass} />
      </span>
    );
  }

  // Fallback: premium text mark (matches the original Header/Footer wording).
  const textSize = {
    header: "text-[1.35rem] sm:text-[1.65rem]",
    footer: "text-[2rem] sm:text-[2.25rem]",
    auth: "text-[1.55rem] sm:text-[1.85rem]",
    compact: "text-[1.1rem]",
  }[variant] || "text-[1.5rem]";
  const showSuffix = variant !== "compact";

  return (
    <span className={`inline-flex items-baseline gap-2 sm:gap-3 ${className}`} data-testid="brand-mark">
      <span className={`font-serif-light ${textSize} tracking-tight text-burgundy leading-none`}>The Earnalism</span>
      {showSuffix && (
        <span className="hidden md:inline italic-accent text-[0.8rem] text-gold-deep leading-none whitespace-nowrap">Digital Library</span>
      )}
    </span>
  );
}
