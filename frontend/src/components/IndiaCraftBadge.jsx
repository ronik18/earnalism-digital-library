export default function IndiaCraftBadge() {
  return (
    <span
      className="india-origin-badge"
      data-testid="india-origin-badge"
      aria-label="Indian national flag"
      title="Indian national flag"
    >
      <svg
        className="india-origin-badge__mark"
        viewBox="0 0 88 52"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="india-atelier-saffron" x1="9" x2="79" y1="10" y2="16">
            <stop offset="0" stopColor="#ffe2b5" />
            <stop offset="0.46" stopColor="#ff9933" />
            <stop offset="1" stopColor="#c9651d" />
          </linearGradient>
          <linearGradient id="india-atelier-ivory" x1="9" x2="79" y1="19" y2="31">
            <stop offset="0" stopColor="#fffdf6" />
            <stop offset="0.54" stopColor="#fff9ea" />
            <stop offset="1" stopColor="#eadfc8" />
          </linearGradient>
          <linearGradient id="india-atelier-green" x1="9" x2="79" y1="32" y2="42">
            <stop offset="0" stopColor="#8fcf88" />
            <stop offset="0.46" stopColor="#138808" />
            <stop offset="1" stopColor="#0b5e2f" />
          </linearGradient>
          <linearGradient id="india-atelier-silk" x1="7" x2="80" y1="5" y2="47">
            <stop offset="0" stopColor="#ffffff" stopOpacity="0.74" />
            <stop offset="0.36" stopColor="#ffffff" stopOpacity="0.08" />
            <stop offset="0.68" stopColor="#2d1b10" stopOpacity="0.12" />
            <stop offset="1" stopColor="#ffffff" stopOpacity="0.24" />
          </linearGradient>
        </defs>
        <path className="india-origin-badge__flag-shadow" d="M11.5 12.8c13.1-7.3 25.6-7.2 37.8-2.4 9.6 3.8 17.6 3.2 27.3-2.6v30.3c-9.9 6.2-18.6 6.8-28.9 2.6-11.5-4.7-22.8-4.1-36.2 3.3z" />
        <path className="india-origin-badge__flag-rim" d="M10.2 11.4c13.8-7.6 26.9-7.5 39.6-2.5 9.2 3.7 17.5 3.1 27.9-3.2v30.8c-10.9 6.8-20 7.3-30.5 3-11.8-4.8-23.2-4.1-37 3.8z" />
        <path className="india-origin-badge__band india-origin-badge__band--saffron" d="M12.1 12.9c12.5-6.3 24.3-6.1 36.1-1.4 8.7 3.5 17 3.2 27.2-2.5v9.2c-10.1 5.4-18.5 5.4-27.5 1.8-11.9-4.7-23.4-4.8-35.8 1.2z" />
        <path className="india-origin-badge__band india-origin-badge__band--ivory" d="M12.1 21.2c12.4-6 23.9-5.9 35.8-1.2 9 3.6 17.4 3.6 27.5-1.8v8.8c-10.3 5.4-18.9 5.2-28.1 1.5-11.5-4.7-22.8-4.4-35.2 1.7z" />
        <path className="india-origin-badge__band india-origin-badge__band--green" d="M12.1 30.2c12.4-6.1 23.7-6.4 35.2-1.7 9.2 3.7 17.8 3.9 28.1-1.5v8.4c-10.2 6-18.7 6.4-28.6 2.3-11.1-4.5-22.4-3.7-34.7 3z" />
        <path className="india-origin-badge__silk" d="M12.1 12.9c12.5-6.3 24.3-6.1 36.1-1.4 8.7 3.5 17 3.2 27.2-2.5v26.4c-10.2 6-18.7 6.4-28.6 2.3-11.1-4.5-22.4-3.7-34.7 3z" />
        <circle className="india-origin-badge__wheel" cx="43.6" cy="24.7" r="5.1" />
        <path className="india-origin-badge__wheel-lines" d="M43.6 19.7v10M38.6 24.7h10M40.1 21.2l7 7M47.1 21.2l-7 7M41.6 20.1l4.1 9.1M45.7 20.1l-4.1 9.1M39.2 22.7l8.9 4M48.1 22.7l-8.9 4" />
      </svg>
    </span>
  );
}
