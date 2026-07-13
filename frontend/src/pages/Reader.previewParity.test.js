import fs from "fs";
import path from "path";

const readerSource = fs.readFileSync(path.resolve(__dirname, "Reader.jsx"), "utf8");
const lockedStateSource = readerSource.slice(
  readerSource.indexOf("if (lockedState)"),
  readerSource.indexOf("const colors = THEMES[theme]"),
);

describe("Reader locked-state preview parity", () => {
  test("finds only explicitly marked preview chapters", () => {
    expect(lockedStateSource).toMatch(/chapters\.find\([\s\S]*is_preview === true/);
    expect(lockedStateSource).not.toContain("const previewChapter = chapters[0]");
  });

  test("uses title-neutral access copy", () => {
    expect(lockedStateSource).toContain("A free preview remains available.");
    expect(lockedStateSource).toContain("This edition has no free preview.");
    expect(lockedStateSource).not.toMatch(/Dracula/);
  });

  test("renders the preview CTA only when an explicit preview exists", () => {
    expect(lockedStateSource).toContain("{canOpenPreview && (");
    expect(lockedStateSource).toContain("Read Free Preview");
  });
});
