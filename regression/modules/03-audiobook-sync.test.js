const { apiGet, request, mapLimit } = require("../utils/http");
const { apiOrigin } = require("../utils/envGuard");
const { isGoLive } = require("../utils/envGuard");
const { audioMarkedAvailable, audioAssetCandidates, manifestAudio } = require("../utils/audio");

const AUDIO_SAMPLE_LIMIT = Number(process.env.REGRESSION_AUDIO_SAMPLE_LIMIT || (isGoLive() ? 24 : 8));
const AUDIO_CONCURRENCY = Number(process.env.REGRESSION_AUDIO_CONCURRENCY || 6);

function absoluteAssetUrl(value) {
  if (!value) return "";
  try {
    return new URL(value, apiOrigin()).toString();
  } catch {
    return "";
  }
}

async function expectPlayableAudio(url) {
  const response = await request(url, { method: "HEAD", skipBody: true, timeoutMs: 20000 });
  expect(response.ok).toBe(true);
  expect(response.headers.get("content-type") || "").toMatch(/audio|mpeg|octet-stream/i);
  expect(response.headers.get("accept-ranges") || "bytes").toMatch(/bytes/i);
}

async function expectSyncCues(url) {
  const response = await request(url, { timeoutMs: 20000 });
  expect(response.ok).toBe(true);
  if ((response.headers.get("content-type") || "").includes("text/vtt") || url.endsWith(".vtt")) {
    expect(response.text).toMatch(/WEBVTT|-->/i);
    return;
  }
  const parsed = JSON.parse(response.text || "[]");
  expect(Array.isArray(parsed) || typeof parsed === "object").toBe(true);
}

describe("Audiobook Quality & Text Highlight Sync", () => {
  const fullAudioTest = (isGoLive() || process.env.REGRESSION_ENABLE_AUDIO_CHECKS === "true") ? test : test.skip;

  fullAudioTest("audiobook availability is backed by playable assets and cues", async () => {
    const books = (await apiGet("/books")).data;
    const audioBooks = books.filter(audioMarkedAvailable);
    expect(audioBooks.length).toBeGreaterThan(0);

    await mapLimit(audioBooks.slice(0, AUDIO_SAMPLE_LIMIT), AUDIO_CONCURRENCY, async (book) => {
      const manifestResponse = await apiGet(`/reader/book/${book.slug}/manifest`, { timeoutMs: 20000 });
      expect(manifestResponse.ok).toBe(true);
      const manifestTrack = manifestAudio(manifestResponse.data);
      const fallbackTrack = audioAssetCandidates(book);
      const audioUrl = absoluteAssetUrl(manifestTrack.audio || fallbackTrack.audio);
      const cueUrl = absoluteAssetUrl(manifestTrack.timestamps || manifestTrack.vtt || fallbackTrack.timestamps || fallbackTrack.vtt);

      expect(manifestTrack.enabled).toBe(true);
      expect(audioUrl).toBeTruthy();
      expect(cueUrl).toBeTruthy();
      await expectPlayableAudio(audioUrl);
      await expectSyncCues(cueUrl);
    });
  });

  fullAudioTest("books with staged audio assets are not exposed as enabled unless explicitly marked", async () => {
    const books = (await apiGet("/books")).data;
    const stagedOnly = books.filter((book) => !audioMarkedAvailable(book) && Object.keys(book.audiobook_assets || {}).length > 0);
    for (const book of stagedOnly) {
      expect(book.audiobook_enabled).not.toBe(true);
      expect(book.generate_audiobook).not.toBe(true);
    }
  });
});
