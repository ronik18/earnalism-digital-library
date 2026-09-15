import { Link } from "react-router-dom";
import "./FooterWordmark.css";

const PUBLIC_URL = process.env.PUBLIC_URL || "";
const FOOTER_WORDMARK = `${PUBLIC_URL}/assets/brand/earnalism-footer-wordmark-ivory.png`;

/** A footer-only derivative; the full canonical lockup remains reserved for the header. */
export default function FooterWordmark() {
  return (
    <Link
      to="/"
      className="footer-wordmark"
      aria-label="Earnalism home"
      data-testid="footer-wordmark"
    >
      <img
        src={FOOTER_WORDMARK}
        alt=""
        width="1280"
        height="330"
        decoding="async"
      />
    </Link>
  );
}
