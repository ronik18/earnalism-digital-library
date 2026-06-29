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
          <clipPath id="india-origin-flag-clip">
            <path d="M10 12.4 C24 4.7 39.8 5.9 53.2 10.3 C63.7 13.8 73.7 12.2 82 6.8 L82 31.5 C72.6 37 62 38 51.2 34.6 C37.8 30.4 23.1 30.1 10 37.2 Z" />
          </clipPath>
        </defs>
        <path
          className="india-origin-badge__flag-shadow"
          d="M9.2 13.8 C23.8 5.3 40.1 6.4 53.8 10.8 C64.1 14.1 74 12.8 82.8 7.2 L82.8 32.4 C72.8 38.1 62.1 39.1 50.8 35.5 C37 31.1 22.2 31.1 9.2 38.4 Z"
        />
        <g clipPath="url(#india-origin-flag-clip)">
          <rect className="india-origin-badge__band india-origin-badge__band--saffron" x="5" y="3" width="84" height="13.8" />
          <rect className="india-origin-badge__band india-origin-badge__band--ivory" x="5" y="16.8" width="84" height="11.2" />
          <rect className="india-origin-badge__band india-origin-badge__band--green" x="5" y="28" width="84" height="14" />
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
        <strong>Made in India</strong>
        <small>literary craft</small>
      </span>
    </span>
  );
}
