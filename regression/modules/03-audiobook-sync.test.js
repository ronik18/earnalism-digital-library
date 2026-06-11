const { apiGet, request } = require("../utils/http");
const { frontendUrl } = require("../utils/envGuard");
const { isGoLive } = require("../utils/envGuard");
const { audioLanguage, publicAudioSlug, audioMarkedAvailable } = require("../utils/audio");

describe("Audiobook Quality & Text Highlight Sync", () => {
  const fullAudioTest = (isGoLive() || process.env.REGRESSION_ENABLE_AUDIO_CHECKS === "true") ? test : test.skip;

  fullAudioTest("audiobook availability is backed by playable assets and cues", async () => {
    const books = (await apiGet("/books")).data;
    const audioBooks = books.filter(audioMarkedAvailable);
    expect(Array.isArray(audioBooks)).toBe(true);

    for (const book of audioBooks) {
      const lang = audioLanguage(book);
      const slug = publicAudioSlug(book);
      const audio = await request(`${frontendUrl()}/audio/${lang}/${slug}.mp3`, { method: "GET", skipBody: true });
      expect(audio.ok).toBe(true);
      expect(audio.headers.get("content-type") || "").toMatch(/audio|octet-stream/i);
      const cues = await request(`${frontendUrl()}/audio/${lang}/${slug}_timestamps.json`);
      expect(cues.ok).toBe(true);
      const parsed = JSON.parse(cues.text || "[]");
      expect(Array.isArray(parsed) || typeof parsed === "object").toBe(true);
    }
  });

  fullAudioTest("books without complete audio are not marked publicly available", async () => {
    const books = (await apiGet("/books")).data;
    for (const book of books) {
      if (!audioMarkedAvailable(book)) {
        expect(!book.audiobook_assets || Object.keys(book.audiobook_assets).length === 0).toBe(true);
      }
    }
  });
});
