import {
  READER_SETTINGS_DEFAULTS,
  READER_SETTINGS_STORAGE_KEY,
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
