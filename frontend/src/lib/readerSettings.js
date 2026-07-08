export const READER_SETTINGS_STORAGE_KEY = "earnalism.reader.preferences.v1";

export const READER_SETTINGS_DEFAULTS = {
  theme: "beige",
  fontSizeIdx: 0,
  lineSpacingMode: "comfortable",
  marginMode: "classic",
  fontFamilyMode: "sans",
  focusMode: false,
  reducedMotionMode: false,
  highlightIntensity: "medium",
  ttsSpeed: 0.85,
};

const ALLOWED_THEMES = new Set(["beige", "sepia", "dark"]);
const ALLOWED_LINE_SPACING = new Set(["comfortable", "relaxed", "airy"]);
const ALLOWED_READER_MARGINS = new Set(["narrow", "classic", "wide"]);
const ALLOWED_FONT_MODES = new Set(["serif", "sans"]);
const ALLOWED_HIGHLIGHT_INTENSITY = new Set(["low", "medium", "high"]);

function boundedNumber(value, fallback, { min, max, integer = false } = {}) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  const bounded = Math.min(max, Math.max(min, parsed));
  return integer ? Math.round(bounded) : bounded;
}

function booleanSetting(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}

export function sanitizeReaderSettings(value = {}) {
  const source = value && typeof value === "object" && !Array.isArray(value) ? value : {};
  return {
    theme: ALLOWED_THEMES.has(source.theme) ? source.theme : READER_SETTINGS_DEFAULTS.theme,
    fontSizeIdx: boundedNumber(source.fontSizeIdx, READER_SETTINGS_DEFAULTS.fontSizeIdx, { min: 0, max: 3, integer: true }),
    lineSpacingMode: ALLOWED_LINE_SPACING.has(source.lineSpacingMode)
      ? source.lineSpacingMode
      : READER_SETTINGS_DEFAULTS.lineSpacingMode,
    marginMode: ALLOWED_READER_MARGINS.has(source.marginMode) ? source.marginMode : READER_SETTINGS_DEFAULTS.marginMode,
    fontFamilyMode: ALLOWED_FONT_MODES.has(source.fontFamilyMode)
      ? source.fontFamilyMode
      : READER_SETTINGS_DEFAULTS.fontFamilyMode,
    focusMode: booleanSetting(source.focusMode, READER_SETTINGS_DEFAULTS.focusMode),
    reducedMotionMode: booleanSetting(source.reducedMotionMode, READER_SETTINGS_DEFAULTS.reducedMotionMode),
    highlightIntensity: ALLOWED_HIGHLIGHT_INTENSITY.has(source.highlightIntensity)
      ? source.highlightIntensity
      : READER_SETTINGS_DEFAULTS.highlightIntensity,
    ttsSpeed: boundedNumber(source.ttsSpeed, READER_SETTINGS_DEFAULTS.ttsSpeed, { min: 0.7, max: 1.8 }),
  };
}

function browserStorage() {
  if (typeof window === "undefined" || !window.localStorage) return null;
  return window.localStorage;
}

export function loadReaderSettings(storage = browserStorage()) {
  if (!storage) return READER_SETTINGS_DEFAULTS;
  try {
    return sanitizeReaderSettings(JSON.parse(storage.getItem(READER_SETTINGS_STORAGE_KEY) || "{}"));
  } catch {
    return READER_SETTINGS_DEFAULTS;
  }
}

export function saveReaderSettings(settings, storage = browserStorage()) {
  if (!storage) return false;
  try {
    storage.setItem(READER_SETTINGS_STORAGE_KEY, JSON.stringify(sanitizeReaderSettings(settings)));
    return true;
  } catch {
    return false;
  }
}
