import { useSettings } from "../context/SettingsContext";

const ALT = "Earnalism logo";
const PUBLIC_URL = process.env.PUBLIC_URL || "";
const DEFAULT_LOGO = `${PUBLIC_URL}/assets/brand/earnalism-logo-transparent-96.webp`;
const DEFAULT_LOGO_SRC_SET = [
  `${PUBLIC_URL}/assets/brand/earnalism-logo-transparent-96.webp 96w`,
  `${PUBLIC_URL}/assets/brand/earnalism-logo-transparent-128.webp 128w`,
].join(", ");
const BRAND_LINE = "Where Learning Becomes Earning";
const VENTURE_LINE = "A Reo Enterprise Venture";

/**
 * BrandMark — renders the brand identity. If admin has uploaded a logo URL via
 * Settings → Brand, it uses that image. Otherwise it uses the bundled mark.
 * The image is capped so an oversized upload cannot blow out the layout.
 *
 * Props:
 *   variant: "header" | "footer" | "auth" | "compact"
 *           — picks the lockup scale and alignment.
 *   className: extra wrapper classes.
 */
export default function BrandMark({ variant = "header", className = "" }) {
  const { brand } = useSettings();
  const logo = brand?.logo_url || DEFAULT_LOGO;
  const useBundledLogo = !brand?.logo_url;

  const wrapperClass = {
    header: "inline-flex items-center gap-2.5 sm:gap-3 text-left",
    footer: "inline-flex items-center gap-3 sm:gap-4 text-left",
    auth: "inline-flex flex-col items-center gap-3 text-center",
    compact: "inline-flex items-center gap-2 text-left",
  }[variant] || "inline-flex items-center gap-3 text-left";

  const imgClass = {
    header: "h-9 w-9 sm:h-11 sm:w-11",
    footer: "h-12 w-12 sm:h-14 sm:w-14",
    auth: "h-14 w-14 sm:h-16 sm:w-16",
    compact: "h-7 w-7",
  }[variant] || "h-10 w-10";

  const textClass = {
    header: "text-[1.12rem] sm:text-[1.42rem]",
    footer: "text-[2rem] sm:text-[2.25rem]",
    auth: "text-[1.55rem] sm:text-[1.85rem]",
    compact: "text-[1.1rem]",
  }[variant] || "text-[1.5rem]";

  const brandLineClass = {
    header: "mt-1 text-[0.55rem] sm:text-[0.62rem]",
    footer: "mt-1.5 text-[0.78rem] sm:text-[0.86rem]",
    auth: "mt-1.5 text-[0.68rem] sm:text-[0.76rem]",
    compact: "mt-0.5 text-[0.48rem]",
  }[variant] || "mt-1 text-[0.68rem]";

  const ventureClass = {
    header: "mt-1 hidden sm:block text-[0.42rem] sm:text-[0.48rem] tracking-[0.18em] text-charcoal-soft/70",
    footer: "mt-1.5 text-[0.55rem] sm:text-[0.62rem] tracking-[0.2em] text-charcoal-soft/75",
    auth: "mt-1 text-[0.5rem] sm:text-[0.56rem] tracking-[0.2em] text-charcoal-soft/70",
    compact: "hidden",
  }[variant] || "mt-1 text-[0.54rem] tracking-[0.18em] text-charcoal-soft/70";

  return (
    <span className={`${wrapperClass} min-w-0 ${className}`} data-testid="brand-mark">
      <img
        src={logo}
        srcSet={useBundledLogo ? DEFAULT_LOGO_SRC_SET : undefined}
        sizes={variant === "footer" || variant === "auth" ? "64px" : "44px"}
        alt={ALT}
        loading={variant === "header" ? "eager" : "lazy"}
        decoding="async"
        className={`${imgClass} shrink-0 object-contain`}
      />
      <span className="min-w-0 flex flex-col">
        <span className={`font-serif-light ${textClass} tracking-tight text-burgundy leading-none whitespace-nowrap`}>Earnalism</span>
        <span className={`font-serif-display italic ${brandLineClass} tracking-[0.02em] text-gold-deep leading-none whitespace-nowrap`} data-testid="brand-line">
          {BRAND_LINE}
        </span>
        <span className={`${ventureClass} uppercase leading-none whitespace-nowrap`} data-testid="brand-venture-line">
          {VENTURE_LINE}
        </span>
      </span>
    </span>
  );
}
