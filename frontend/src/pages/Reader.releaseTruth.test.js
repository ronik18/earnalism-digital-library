import fs from "fs";
import path from "path";

const readerSourcePath = path.resolve(__dirname, "Reader.jsx");
const readerSource = fs.readFileSync(readerSourcePath, "utf8");

describe("Reader release-truth and reading-room guardrails", () => {
  test("does not expose browser speech as an audiobook fallback", () => {
    expect(readerSource).not.toMatch(/speechSynthesis|SpeechSynthesisUtterance|synthRef|system speech|browser speech/i);
  });

  test("does not derive static audio URLs", () => {
    expect(readerSource).not.toMatch(/\/audio\//);
    expect(readerSource).not.toMatch(/audioUrl\s*\|\|/);
    expect(readerSource).not.toMatch(/timestampsUrl\s*\|\|/);
  });

  test("keeps Reader audio controls behind shared approval evidence", () => {
    expect(readerSource).toMatch(/canExposeAudiobookControls/);
    expect(readerSource).toMatch(/hasGeneratedAudioEnabled\(book,\s*bookId\)/);
    expect(readerSource).toMatch(/generatedAudioAvailable/);
    expect(readerSource).toMatch(/Audio will appear only after narration, sync, and browser gates pass/);
  });

  test("does not claim word-level sync in customer copy", () => {
    expect(readerSource).not.toMatch(/word-level|word level|word sync/i);
    expect(readerSource).toMatch(/Section-following narration/);
    expect(readerSource).toMatch(/Paragraph\/Stanza Sync/);
  });

  test("represents premium reading settings for bilingual long-form reading", () => {
    expect(readerSource).toMatch(/label:\s*'Light'/);
    expect(readerSource).toMatch(/label:\s*'Sepia'/);
    expect(readerSource).toMatch(/label:\s*'Night'/);
    expect(readerSource).toMatch(/Bengali font mode/);
    expect(readerSource).toMatch(/Literary Bengali serif/);
    expect(readerSource).toMatch(/Clear Bengali sans/);
    expect(readerSource).toMatch(/Reduced motion/);
    expect(readerSource).toMatch(/Highlight intensity/);
    expect(readerSource).toMatch(/aria-labelledby="reader-settings-title"/);
  });

  test("hardens Reader settings for persistence and accessibility", () => {
    expect(readerSource).toMatch(/loadReaderSettings/);
    expect(readerSource).toMatch(/saveReaderSettings/);
    expect(readerSource).toMatch(/resetReaderSettings/);
    expect(readerSource).toMatch(/Reset comfort defaults/);
    expect(readerSource).toMatch(/aria-modal="true"/);
    expect(readerSource).toMatch(/data-testid="reader-settings-panel"/);
    expect(readerSource).toMatch(/data-reader-settings-initial-focus/);
    expect(readerSource).toMatch(/event\.key === 'Escape'/);
  });

  test("keeps Settings copy free of public audiobook claims", () => {
    const settingsSource = readerSource.slice(readerSource.indexOf('{showSettings && ('));
    expect(settingsSource).not.toMatch(/Listen CTA|AudioObject|browser speech|system speech|word-level|word sync/i);
    expect(settingsSource).toMatch(/Reading tone/);
    expect(settingsSource).toMatch(/Typography/);
    expect(settingsSource).toMatch(/Bengali comfort/);
    expect(settingsSource).toMatch(/Focus and motion/);
  });
});
