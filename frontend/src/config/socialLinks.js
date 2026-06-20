const env = process.env || {};

export const SUPPORTED_SOCIAL_LINKS = [
  {
    id: "instagram",
    label: "Instagram",
    url: env.REACT_APP_INSTAGRAM_URL,
    ariaLabel: "Follow The Earnalism on Instagram",
    icon: "instagram",
    enabled: true,
    order: 10,
  },
  {
    id: "youtube",
    label: "YouTube",
    url: env.REACT_APP_YOUTUBE_URL,
    ariaLabel: "Follow The Earnalism on YouTube",
    icon: "youtube",
    enabled: true,
    order: 20,
  },
  {
    id: "facebook",
    label: "Facebook",
    url: env.REACT_APP_FACEBOOK_URL,
    ariaLabel: "Follow The Earnalism on Facebook",
    icon: "facebook",
    enabled: true,
    order: 30,
  },
  {
    id: "linkedin",
    label: "LinkedIn",
    url: env.REACT_APP_LINKEDIN_URL,
    ariaLabel: "Follow The Earnalism on LinkedIn",
    icon: "linkedin",
    enabled: true,
    order: 40,
  },
  {
    id: "x",
    label: "X",
    url: env.REACT_APP_X_URL,
    ariaLabel: "Follow The Earnalism on X",
    icon: "x",
    enabled: true,
    order: 50,
  },
  {
    id: "whatsapp-channel",
    label: "WhatsApp Channel",
    url: env.REACT_APP_WHATSAPP_CHANNEL_URL,
    ariaLabel: "Follow The Earnalism WhatsApp Channel",
    icon: "whatsapp",
    enabled: true,
    order: 60,
  },
  {
    id: "telegram-channel",
    label: "Telegram Channel",
    url: env.REACT_APP_TELEGRAM_CHANNEL_URL,
    ariaLabel: "Follow The Earnalism Telegram Channel",
    icon: "telegram",
    enabled: true,
    order: 70,
  },
];

export function normalizeSocialUrl(url) {
  if (typeof url !== "string") return "";
  const trimmed = url.trim();
  if (!trimmed || trimmed === "#") return "";

  try {
    const parsed = new URL(trimmed);
    if (!["http:", "https:"].includes(parsed.protocol)) return "";
    return parsed.href;
  } catch (_err) {
    return "";
  }
}

export function getEnabledSocialLinks(links = SUPPORTED_SOCIAL_LINKS) {
  return links
    .map((link) => ({
      ...link,
      url: normalizeSocialUrl(link.url),
    }))
    .filter((link) => link.enabled !== false && Boolean(link.url))
    .sort((left, right) => Number(left.order || 0) - Number(right.order || 0));
}
