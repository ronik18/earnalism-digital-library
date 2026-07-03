export default function IndiaCraftBadge() {
  return (
    <span
      className="india-origin-badge"
      data-testid="india-origin-badge"
      aria-label="Made in India"
      title="Made in India"
    >
      <svg
        className="india-origin-badge__mark"
        viewBox="0 0 92 44"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="india-origin-saffron-3d" x1="5" x2="88" y1="5" y2="17">
            <stop offset="0" stopColor="#fff0cf" />
            <stop offset="0.2" stopColor="#f59d39" />
            <stop offset="0.72" stopColor="#d9741f" />
            <stop offset="1" stopColor="#ffd59a" />
          </linearGradient>
          <linearGradient id="india-origin-ivory-3d" x1="5" x2="88" y1="14" y2="29">
            <stop offset="0" stopColor="#ffffff" />
            <stop offset="0.52" stopColor="#fff8e8" />
            <stop offset="1" stopColor="#eadfc7" />
          </linearGradient>
          <linearGradient id="india-origin-green-3d" x1="5" x2="88" y1="28" y2="42">
            <stop offset="0" stopColor="#bce6bd" />
            <stop offset="0.25" stopColor="#278b4f" />
            <stop offset="0.78" stopColor="#0c6436" />
            <stop offset="1" stopColor="#7ccf91" />
          </linearGradient>
          <radialGradient id="india-origin-flag-glow" cx="42%" cy="36%" r="60%">
            <stop offset="0" stopColor="#ffffff" stopOpacity="0.74" />
            <stop offset="0.48" stopColor="#ffffff" stopOpacity="0.12" />
            <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
          </radialGradient>
          <clipPath id="india-origin-flag-clip">
            <path d="M10 12.4 C24 4.7 39.8 5.9 53.2 10.3 C63.7 13.8 73.7 12.2 82 6.8 L82 31.5 C72.6 37 62 38 51.2 34.6 C37.8 30.4 23.1 30.1 10 37.2 Z" />
          </clipPath>
        </defs>
        <g className="india-origin-badge__sprinkles" aria-hidden="true">
          <circle className="india-origin-badge__sprinkle india-origin-badge__sprinkle--saffron" cx="9" cy="8" r="1.2" />
          <circle className="india-origin-badge__sprinkle india-origin-badge__sprinkle--ivory" cx="17" cy="5.8" r="0.78" />
          <circle className="india-origin-badge__sprinkle india-origin-badge__sprinkle--green" cx="26.3" cy="7.8" r="0.95" />
          <circle className="india-origin-badge__sprinkle india-origin-badge__sprinkle--saffron" cx="74" cy="4.5" r="0.86" />
          <circle className="india-origin-badge__sprinkle india-origin-badge__sprinkle--green" cx="86" cy="33.6" r="1.12" />
          <circle className="india-origin-badge__sprinkle india-origin-badge__sprinkle--ivory" cx="78.4" cy="38" r="0.72" />
          <path className="india-origin-badge__sprinkle-stroke india-origin-badge__sprinkle-stroke--saffron" d="M3.9 18.2 l3.6 -1.6" />
          <path className="india-origin-badge__sprinkle-stroke india-origin-badge__sprinkle-stroke--green" d="M5.1 33.8 l3.7 1.2" />
        </g>
        <path
          className="india-origin-badge__flag-shadow"
          d="M9.2 13.8 C23.8 5.3 40.1 6.4 53.8 10.8 C64.1 14.1 74 12.8 82.8 7.2 L82.8 32.4 C72.8 38.1 62.1 39.1 50.8 35.5 C37 31.1 22.2 31.1 9.2 38.4 Z"
        />
        <g clipPath="url(#india-origin-flag-clip)">
          <rect className="india-origin-badge__band india-origin-badge__band--saffron" x="5" y="3" width="84" height="13.8" />
          <rect className="india-origin-badge__band india-origin-badge__band--ivory" x="5" y="16.8" width="84" height="11.2" />
          <rect className="india-origin-badge__band india-origin-badge__band--green" x="5" y="28" width="84" height="14" />
          <path
            className="india-origin-badge__flag-glow"
            d="M7 11.7 C24 6.1 38.2 7 53.7 11.7 C63.2 14.6 72.6 13.6 86 7.2 L86 18.2 C72.8 21.2 62.9 20 51.2 16.4 C36.9 12 23.9 11.3 7 18.7 Z"
          />
          <path
            className="india-origin-badge__flag-bevel"
            d="M7.4 35.8 C22.5 28.8 37.8 29.1 51.5 33.4 C62.3 36.8 73.1 35.9 85.2 29.2 L85.2 35.2 C73.4 41.1 62 42.1 50.1 38.2 C36.8 33.8 22.7 33.9 7.4 41.7 Z"
          />
          <path
            className="india-origin-badge__silk"
            d="M4 14 C22 5 39 6.2 54 11 C65 14.6 75 12.8 90 3 M4 30 C22 23.5 39 24 54.8 29 C65.2 32.3 75.4 31.1 90 23"
          />
        </g>
        <path
          className="india-origin-badge__flag-rim"
          d="M10 12.4 C24 4.7 39.8 5.9 53.2 10.3 C63.7 13.8 73.7 12.2 82 6.8 L82 31.5 C72.6 37 62 38 51.2 34.6 C37.8 30.4 23.1 30.1 10 37.2 Z"
        />
        <circle className="india-origin-badge__wheel" cx="46.2" cy="22.4" r="5.5" />
        <path
          className="india-origin-badge__wheel-lines"
          d="M46.2 16.9 V27.9 M40.7 22.4 H51.7 M42.3 18.5 L50.1 26.3 M50.1 18.5 L42.3 26.3 M44.1 17.3 L48.3 27.5 M48.3 17.3 L44.1 27.5 M41.1 20.2 L51.3 24.6 M51.3 20.2 L41.1 24.6"
        />
        <circle className="india-origin-badge__wheel-core" cx="46.2" cy="22.4" r="1.1" />
      </svg>
      <span className="india-origin-badge__text">
        <small className="india-origin-badge__eyebrow">Literary atelier</small>
        <strong>Made in India</strong>
        <span className="india-origin-badge__subline">
          <span className="india-origin-badge__dot" aria-hidden="true" />
          <span>Editorial craft</span>
        </span>
      </span>
    </span>
  );
}
