const env = process.env || {};

export const OFFICIAL_SOCIAL_URLS = {
  linkedin: "https://www.linkedin.com/company/earnalism-a-reo-enterprise-venture/",
  email: "mailto:sales@reoenterprise.in",
  facebook: "https://www.facebook.com/profile.php?id=61591315384768",
  instagram: "https://www.instagram.com/theearnalism/",
  x: "https://x.com/earnalism",
  youtube: "https://www.youtube.com/channel/UCw-UnAXdRzqij8_B2TlgQjQ",
};

export const SUPPORTED_SOCIAL_LINKS = [
  {
    id: "linkedin",
    platform: "LinkedIn",
    label: "LinkedIn",
    url: OFFICIAL_SOCIAL_URLS.linkedin,
    envKey: "REACT_APP_LINKEDIN_URL",
    ariaLabel: "Follow The Earnalism on LinkedIn",
    icon: "linkedin",
    external: true,
    enabled: true,
    order: 10,
  },
  {
    id: "email",
    platform: "Email",
    label: "Email",
    url: OFFICIAL_SOCIAL_URLS.email,
    envKey: "REACT_APP_SOCIAL_EMAIL_URL",
    ariaLabel: "Email The Earnalism",
    icon: "mail",
    external: false,
    enabled: true,
    order: 20,
  },
  {
    id: "facebook",
    platform: "Facebook",
    label: "Facebook",
    url: OFFICIAL_SOCIAL_URLS.facebook,
    envKey: "REACT_APP_FACEBOOK_URL",
    ariaLabel: "Follow The Earnalism on Facebook",
    icon: "facebook",
    external: true,
    enabled: true,
    order: 30,
  },
  {
    id: "instagram",
    platform: "Instagram",
    label: "Instagram",
    url: OFFICIAL_SOCIAL_URLS.instagram,
    envKey: "REACT_APP_INSTAGRAM_URL",
    ariaLabel: "Follow The Earnalism on Instagram",
    icon: "instagram",
    external: true,
    enabled: true,
    order: 40,
  },
  {
    id: "x",
    platform: "X",
    label: "X",
    url: OFFICIAL_SOCIAL_URLS.x,
    envKey: "REACT_APP_X_URL",
    ariaLabel: "Follow The Earnalism on X",
    icon: "x",
    aliases: ["twitter"],
    external: true,
    enabled: true,
    order: 50,
  },
  {
    id: "youtube",
    platform: "YouTube",
    label: "YouTube",
    url: OFFICIAL_SOCIAL_URLS.youtube,
    envKey: "REACT_APP_YOUTUBE_URL",
    ariaLabel: "Follow The Earnalism on YouTube",
    icon: "youtube",
    external: true,
    enabled: true,
    order: 60,
  },
];

export function normalizeSocialUrl(url) {
  if (typeof url !== "string") return "";
  const trimmed = url.trim();
  if (!trimmed || trimmed === "#") return "";

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol === "mailto:") {
      const address = decodeURIComponent(parsed.pathname || "").trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) return "";
      return `mailto:${address}`;
    }
    if (!["https:"].includes(parsed.protocol)) return "";
    if (["localhost", "127.0.0.1", "::1"].includes(parsed.hostname)) return "";
    parsed.hash = "";
    return parsed.href;
  } catch (_err) {
    return "";
  }
}

function overrideFor(link, overrides = {}) {
  if (!overrides || Array.isArray(overrides) || typeof overrides !== "object") return "";
  const keys = [link.id, ...(link.aliases || [])];
  for (const key of keys) {
    const normalized = normalizeSocialUrl(overrides[key]);
    if (normalized) return normalized;
  }
  return "";
}

function envOverrideFor(link) {
  return normalizeSocialUrl(env[link.envKey]);
}

export function getEnabledSocialLinks(input) {
  const links = Array.isArray(input) ? input : SUPPORTED_SOCIAL_LINKS;
  const overrides = Array.isArray(input) ? {} : input || {};

  return links
    .map((link) => ({
      ...link,
      url: overrideFor(link, overrides) || envOverrideFor(link) || normalizeSocialUrl(link.url),
    }))
    .filter((link) => link.enabled !== false && Boolean(link.url))
    .sort((left, right) => Number(left.order || 0) - Number(right.order || 0));
}
