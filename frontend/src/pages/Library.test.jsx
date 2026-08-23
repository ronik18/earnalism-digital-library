import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/pages/Library.jsx"), "utf8");

describe("Library experience", () => {
  test("uses the single editorial collection architecture and approved copy", () => {
    expect(source).toContain("ReferenceLibrarySurface");
    expect(source).toContain("Explore the collection.");
    expect(source).toContain("Search the Library");
    expect(source).toContain("Search by title or author");
    expect(source).toContain("No editions match these filters.");
    expect(source).toContain("Try removing a filter or searching for another title or author.");
    expect(source).not.toContain("Choose a shelf without losing the quiet.");
    expect(source).not.toContain("Three ways into the library");
    expect(source).not.toContain("Curated Reader-Ready Shelves");
  });

  test("preserves release-safe book rendering and URL-synced filters", () => {
    expect(source).toContain("<BookCard");
    expect(source).toContain('params.get("language")');
    expect(source).toContain('params.get("reading")');
    expect(source).toContain('params.get("listening")');
    expect(source).toContain('params.get("sort")');
    expect(source).toContain('params.get("q")');
    expect(source).toContain("Listening appears only where the release evidence allows it.");
    expect(source).toContain("library-filter-drawer");
    expect(source).toContain('aria-modal="true"');
  });
});
