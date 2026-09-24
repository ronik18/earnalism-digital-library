const USER_AGENT_MARKERS = /(?:Mozilla\/|AppleWebKit\/|Chrome\/|CriOS\/|Firefox\/|FxiOS\/|Safari\/|Edg\/|OPR\/)/i;

export function formatSessionDeviceLabel(value) {
  const label = String(value || "").trim();
  if (!label) return "Browser";
  if (!USER_AGENT_MARKERS.test(label)) {
    if (/[\/;]|\b(?:Mozilla|AppleWebKit|Gecko|Version|rv:)/i.test(label)) return "Browser";
    if (/^MacIntel\s*[·|]/i.test(label)) return "Browser on Mac";
    if (/^iPhone\s*[·|]/i.test(label)) return "Mobile browser on iPhone";
    if (/^iPad\s*[·|]/i.test(label)) return "Mobile browser on iPad";
    if (/^Win(?:32|64)?\s*[·|]/i.test(label)) return "Browser on Windows";
    if (/^Linux\s*[·|]/i.test(label)) return "Browser on Linux";
    if (/\bMobile\b/i.test(label)) return "Mobile browser";
    return label.slice(0, 48);
  }

  const browser = /Edg\//i.test(label)
    ? "Edge"
    : /OPR\//i.test(label)
      ? "Opera"
      : /(?:CriOS|Chrome)\//i.test(label)
        ? "Chrome"
        : /(?:FxiOS|Firefox)\//i.test(label)
          ? "Firefox"
          : /Safari\//i.test(label)
            ? "Safari"
            : "Browser";
  const platform = /iPhone/i.test(label)
    ? "iPhone"
    : /iPad/i.test(label)
      ? "iPad"
      : /Android/i.test(label)
        ? "Android"
        : /Windows/i.test(label)
          ? "Windows"
          : /Macintosh|Mac OS X|MacIntel/i.test(label)
            ? "Mac"
            : /Linux/i.test(label)
              ? "Linux"
              : "";

  if (platform) return `${browser} on ${platform}`;
  if (/Mobile/i.test(label)) return "Mobile browser";
  return browser;
}

export function sortSessionDevices(devices = []) {
  return [...devices].sort((left, right) => {
    const leftActive = left.status === "active";
    const rightActive = right.status === "active";
    if (Boolean(left.current) !== Boolean(right.current)) return left.current ? -1 : 1;
    if (leftActive !== rightActive) return leftActive ? -1 : 1;
    return new Date(right.last_seen_at || 0) - new Date(left.last_seen_at || 0);
  });
}

export function formatSessionLastActive(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}
