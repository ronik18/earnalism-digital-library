import { useSettings } from "../context/SettingsContext";

const ALT = "Earnalism logo";
const DEFAULT_LOGO = `${process.env.PUBLIC_URL || ""}/assets/brand/earnalism-logo-transparent.png`;

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

  return (
    <span className={`${wrapperClass} min-w-0 ${className}`} data-testid="brand-mark">
      <img
        src={logo}
        alt={ALT}
        loading={variant === "header" ? "eager" : "lazy"}
        decoding="async"
        className={`${imgClass} shrink-0 object-contain`}
      />
      <span className="min-w-0 flex flex-col">
        <span className={`font-serif-light ${textClass} tracking-tight text-burgundy leading-none whitespace-nowrap`}>Earnalism</span>
        <span className="mt-1 text-[0.48rem] sm:text-[0.56rem] tracking-[0.18em] uppercase text-gold-deep leading-none whitespace-nowrap">
          A Reo Enterprise Venture
        </span>
      </span>
    </span>
  );
}
