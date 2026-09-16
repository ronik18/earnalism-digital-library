export const READER_SETTINGS_STORAGE_KEY = "earnalism.reader.preferences.v1";
export const READER_TYPOGRAPHY_VERSION = 2;
export const READER_TEXT_SIZE_REM_STEPS = Object.freeze([1.125, 1.25, 1.375, 1.5, 1.625, 1.75, 1.875, 2]);
const LEGACY_FONT_SIZE_REMS = Object.freeze([1.125, 1.125, 1.25, 1.375]);

export const READER_SETTINGS_DEFAULTS = {
  theme: "beige",
  fontSizeIdx: 1,
  lineSpacingMode: "comfortable",
  marginMode: "classic",
  fontFamilyMode: "sans",
  focusMode: false,
  reducedMotionMode: false,
  highlightIntensity: "medium",
  ttsSpeed: 0.85,
  readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
  readerTextSizeRem: null,
  readerFontFamilyPreference: null,
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

function own(source, key) {
  return Object.prototype.hasOwnProperty.call(source, key);
}

function supportedTextSize(value) {
  const parsed = Number(value);
  return READER_TEXT_SIZE_REM_STEPS.includes(parsed) ? parsed : null;
}

// The v1 17px setting predates the accessible 1.125rem minimum. It is
// deliberately moved to that minimum; the original index remains intact for
// the legacy Reader and all other legacy sizes retain their visual meaning.
function migratedTextSize(source, legacyIndex) {
  if (Number(source.readerTypographyVersion) >= READER_TYPOGRAPHY_VERSION) {
    return supportedTextSize(source.readerTextSizeRem);
  }
  const rawLegacyIndex = Number(source.fontSizeIdx);
  return own(source, "fontSizeIdx") && Number.isInteger(rawLegacyIndex) && rawLegacyIndex >= 0 && rawLegacyIndex < LEGACY_FONT_SIZE_REMS.length
    ? LEGACY_FONT_SIZE_REMS[rawLegacyIndex]
    : null;
}

export function sanitizeReaderSettings(value = {}) {
  const source = value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const fontSizeIdx = boundedNumber(source.fontSizeIdx, READER_SETTINGS_DEFAULTS.fontSizeIdx, { min: 0, max: 3, integer: true });
  const fontFamilyMode = ALLOWED_FONT_MODES.has(source.fontFamilyMode)
    ? source.fontFamilyMode
    : READER_SETTINGS_DEFAULTS.fontFamilyMode;
  const isTypographyV2 = Number(source.readerTypographyVersion) >= READER_TYPOGRAPHY_VERSION;
  const fontFamilyPreference = isTypographyV2
    ? (ALLOWED_FONT_MODES.has(source.readerFontFamilyPreference) ? source.readerFontFamilyPreference : null)
    : (own(source, "fontFamilyMode") && ALLOWED_FONT_MODES.has(source.fontFamilyMode) ? fontFamilyMode : null);
  return {
    theme: ALLOWED_THEMES.has(source.theme) ? source.theme : READER_SETTINGS_DEFAULTS.theme,
    fontSizeIdx,
    lineSpacingMode: ALLOWED_LINE_SPACING.has(source.lineSpacingMode)
      ? source.lineSpacingMode
      : READER_SETTINGS_DEFAULTS.lineSpacingMode,
    marginMode: ALLOWED_READER_MARGINS.has(source.marginMode) ? source.marginMode : READER_SETTINGS_DEFAULTS.marginMode,
    fontFamilyMode,
    focusMode: booleanSetting(source.focusMode, READER_SETTINGS_DEFAULTS.focusMode),
    reducedMotionMode: booleanSetting(source.reducedMotionMode, READER_SETTINGS_DEFAULTS.reducedMotionMode),
    highlightIntensity: ALLOWED_HIGHLIGHT_INTENSITY.has(source.highlightIntensity)
      ? source.highlightIntensity
      : READER_SETTINGS_DEFAULTS.highlightIntensity,
    ttsSpeed: boundedNumber(source.ttsSpeed, READER_SETTINGS_DEFAULTS.ttsSpeed, { min: 0.7, max: 1.8 }),
    readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
    readerTextSizeRem: migratedTextSize(source, fontSizeIdx),
    readerFontFamilyPreference: fontFamilyPreference,
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
