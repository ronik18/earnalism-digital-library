import {
  READER_SETTINGS_DEFAULTS,
  READER_SETTINGS_STORAGE_KEY,
  READER_TYPOGRAPHY_VERSION,
  loadReaderSettings,
  sanitizeReaderSettings,
  saveReaderSettings,
} from "./readerSettings";

function memoryStorage(initial = {}) {
  const store = { ...initial };
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value;
    },
  };
}

describe("reader settings persistence", () => {
  test("sanitizes invalid stored values back to comfort defaults", () => {
    expect(sanitizeReaderSettings({
      theme: "neon",
      fontSizeIdx: 999,
      lineSpacingMode: "cramped",
      marginMode: "wall-to-wall",
      fontFamilyMode: "comic",
      focusMode: "yes",
      reducedMotionMode: "no",
      highlightIntensity: "laser",
      ttsSpeed: 4,
    })).toEqual({
      ...READER_SETTINGS_DEFAULTS,
      fontSizeIdx: 3,
      ttsSpeed: 1.8,
    });
  });

  test("loads valid persisted reader settings", () => {
    const storage = memoryStorage({
      [READER_SETTINGS_STORAGE_KEY]: JSON.stringify({
        theme: "dark",
        fontSizeIdx: 2,
        lineSpacingMode: "airy",
        marginMode: "wide",
        fontFamilyMode: "serif",
        focusMode: true,
        reducedMotionMode: true,
        highlightIntensity: "high",
        ttsSpeed: 1.1,
      }),
    });

    expect(loadReaderSettings(storage)).toMatchObject({
      theme: "dark",
      fontSizeIdx: 2,
      lineSpacingMode: "airy",
      marginMode: "wide",
      fontFamilyMode: "serif",
      focusMode: true,
      reducedMotionMode: true,
      highlightIntensity: "high",
      ttsSpeed: 1.1,
      readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
      readerTextSizeRem: 1.25,
      readerFontFamilyPreference: "serif",
    });
  });

  test("migrates legacy sizes without silently changing the stored index", () => {
    const smallest = sanitizeReaderSettings({ fontSizeIdx: 0, fontFamilyMode: "sans" });
    const larger = sanitizeReaderSettings({ fontSizeIdx: 3, fontFamilyMode: "serif" });

    // 17px is below the new 1.125rem minimum, so it moves to the documented
    // minimum while the v1 index remains available to the legacy Reader.
    expect(smallest).toMatchObject({
      fontSizeIdx: 0,
      readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
      readerTextSizeRem: 1.125,
      readerFontFamilyPreference: "sans",
    });
    expect(larger).toMatchObject({
      fontSizeIdx: 3,
      readerTextSizeRem: 1.375,
      readerFontFamilyPreference: "serif",
    });
  });

  test("keeps language defaults available for a new record and preserves an explicit v2 size", () => {
    expect(sanitizeReaderSettings({})).toMatchObject({
      readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
      readerTextSizeRem: null,
      readerFontFamilyPreference: null,
    });
    expect(sanitizeReaderSettings({
      readerTypographyVersion: READER_TYPOGRAPHY_VERSION,
      readerTextSizeRem: 2,
      readerFontFamilyPreference: "sans",
    })).toMatchObject({
      readerTextSizeRem: 2,
      readerFontFamilyPreference: "sans",
    });
  });

  test("saves only sanitized reader settings", () => {
    const storage = memoryStorage();

    expect(saveReaderSettings({ theme: "sepia", fontSizeIdx: -10, lineSpacingMode: "relaxed" }, storage)).toBe(true);
    expect(JSON.parse(storage.getItem(READER_SETTINGS_STORAGE_KEY))).toMatchObject({
      theme: "sepia",
      fontSizeIdx: 0,
      lineSpacingMode: "relaxed",
    });
  });
});
