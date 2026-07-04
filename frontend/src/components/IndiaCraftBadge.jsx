export default function IndiaCraftBadge() {
  return (
    <span
      className="india-origin-badge"
      data-testid="india-origin-badge"
      aria-label="Made in India - Literary Atelier"
      title="Made in India - Literary Atelier"
    >
      <svg
        className="india-origin-badge__mark"
        viewBox="0 0 68 38"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="india-atelier-saffron" x1="8" x2="60" y1="7" y2="12">
            <stop offset="0" stopColor="#ffd7a4" />
            <stop offset="0.48" stopColor="#ff9933" />
            <stop offset="1" stopColor="#c96d20" />
          </linearGradient>
          <linearGradient id="india-atelier-ivory" x1="8" x2="60" y1="14" y2="22">
            <stop offset="0" stopColor="#fffdf6" />
            <stop offset="0.58" stopColor="#fff8e7" />
            <stop offset="1" stopColor="#eadfc8" />
          </linearGradient>
          <linearGradient id="india-atelier-green" x1="8" x2="60" y1="25" y2="32">
            <stop offset="0" stopColor="#87c987" />
            <stop offset="0.46" stopColor="#138808" />
            <stop offset="1" stopColor="#0b5e2f" />
          </linearGradient>
        </defs>
        <path className="india-origin-badge__flag-shadow" d="M9 10.8c10.8-5.7 21-5.7 31.1-1.8 6.9 2.7 12.8 2.5 18.9-1.1v22.6c-6.6 3.9-13.1 4.2-20.4 1.2-9.6-3.9-19.3-3.3-29.6 2.2z" />
        <path className="india-origin-badge__flag-rim" d="M8.2 9.8c11-5.9 21.6-5.9 32-1.9 6.7 2.6 12.7 2.4 19.6-1.6v22.9c-7.1 4.2-13.7 4.6-21.2 1.5-9.8-4-19.5-3.4-30.4 2.5z" />
        <path className="india-origin-badge__band india-origin-badge__band--saffron" d="M9.6 10.9c10.1-4.9 19.8-4.7 29.6-1 6.4 2.5 12.5 2.5 18.9-.6v6.9c-6.5 3-12.7 2.8-19.2.3-9.8-3.8-19.3-3.9-29.3.8z" />
        <path className="india-origin-badge__band india-origin-badge__band--ivory" d="M9.6 17.3c10-4.7 19.5-4.6 29.3-.8 6.5 2.5 12.7 2.7 19.2-.3v6.4c-6.6 3.1-12.9 2.9-19.5.2-9.7-3.9-19.1-3.7-29 1.2z" />
        <path className="india-origin-badge__band india-origin-badge__band--green" d="M9.6 24c9.9-4.9 19.3-5.1 29-1.2 6.6 2.7 12.9 2.9 19.5-.2v6.1c-6.5 3.5-12.7 3.7-19.7.9-9.4-3.8-18.9-3.2-28.8 2.1z" />
        <circle className="india-origin-badge__wheel" cx="34.2" cy="19.4" r="4.1" />
        <path className="india-origin-badge__wheel-lines" d="M34.2 15.3v8.2M30.1 19.4h8.2M31.3 16.5l5.8 5.8M37.1 16.5l-5.8 5.8M32.5 15.7l3.4 7.4M35.9 15.7l-3.4 7.4M30.6 17.8l7.2 3.2M37.8 17.8l-7.2 3.2" />
      </svg>
      <span className="india-origin-badge__text">Made in India - Literary Atelier</span>
    </span>
  );
}
