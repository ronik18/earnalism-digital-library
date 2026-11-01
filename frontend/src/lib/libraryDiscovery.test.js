import fs from "fs";
import path from "path";
import acceptedDiscoveryMetadata from "../data/libraryDiscoveryMetadata.json";
import { discoveryMetadataForBook, genresOfBook, readingFormOfBook, LIBRARY_READING_FORMS } from "./libraryDiscovery";

const repoRoot = path.resolve(process.cwd(), "..");
const json = (relative) => JSON.parse(fs.readFileSync(path.join(repoRoot, relative), "utf8"));

test("covers every accepted canonical edition and preserves its source language identity", () => {
  const acceptedSlugs = json("data/controlled_launch.json").live_approved_slugs;
  expect(Object.keys(acceptedDiscoveryMetadata).sort()).toEqual([...acceptedSlugs].sort());
  const forms = LIBRARY_READING_FORMS.filter(({ slug }) => slug !== "all").map(({ slug }) => slug);
  for (const slug of acceptedSlugs) {
    const directory = `data/controlled_publications/${slug}`;
    const book = json(`${directory}/public_book.json`);
    const manifest = json(`${directory}/reader_manifest.json`);
    expect(book.slug).toBe(slug);
    expect(manifest.slug).toBe(slug);
    expect(manifest.language).toMatch(/^(?:bn|ben|en|eng)(?:-|$)/);
    const metadata = discoveryMetadataForBook({ slug });
    expect(metadata.language).toBe(/^(bn|ben)(-|$)/.test(manifest.language) ? "bn" : "en");
    expect(forms).toContain(metadata.form);
    expect(metadata.genres.length).toBeGreaterThan(0);
  }
});

test.each([
  ["the-tell-tale-heart", "short-story"], ["the-gift-of-the-magi", "short-story"],
  ["the-adventures-of-sherlock-holmes", "short-story"], ["the-selfish-giant", "short-story"],
  ["the-call-of-the-wild", "novel"], ["bn-066", "novel"],
  ["agentic-ai-with-python", "nonfiction"], ["the-principles-of-scientific-management", "nonfiction"],
  ["bn-059", "poetry"], ["lokrahasya", "poetry"],
])("classifies %s by edition rather than marketing words", (slug, form) => {
  const book = json(`data/controlled_publications/${slug}/public_book.json`);
  expect(readingFormOfBook(book)).toBe(form);
  expect(readingFormOfBook({ ...book, short_description: "A short story in the history of poetry" })).toBe(form);
});

test("corrects known genre mismatches without modifying canonical category or release metadata", () => {
  const book = Object.freeze({ ...json("data/controlled_publications/a-scandal-in-bohemia/public_book.json"), reader_enabled: false });
  expect(book.category_slug).toBe("gothic-fiction");
  expect(genresOfBook(book)).toEqual(["mystery"]);
  expect(book.category_slug).toBe("gothic-fiction");
  expect(book.reader_enabled).toBe(false);
  expect(Object.keys(discoveryMetadataForBook(book)).sort()).toEqual(["form", "genres", "language"]);
});

test("retains clear secondary genres rather than treating primary genres as exclusive", () => {
  expect(genresOfBook({ slug: "frankenstein" })).toContain("science-fiction");
  expect(genresOfBook({ slug: "the-stolen-white-elephant" })).toEqual(["mystery", "satire"]);
  expect(genresOfBook({ slug: "the-selfish-giant" })).toEqual(["fantasy", "children-classics"]);
});

test("prefers valid explicit runtime labels while rejecting unrelated format/category guesses", () => {
  expect(discoveryMetadataForBook({ slug: "the-selfish-giant", language: "bn-BD", literary_form: "essay", genres: [" Mystery ", "mystery"] }))
    .toEqual({ language: "bn", form: "poetry", genres: ["mystery"] });
  expect(discoveryMetadataForBook({ slug: "the-selfish-giant", language: "invalid", language_code: "eng", form: "mp3", genres: [null, "all", ""], category_slug: "wrong-category" }))
    .toEqual(acceptedDiscoveryMetadata["the-selfish-giant"]);
});

test("unknown or held books receive no inferred novel classification or access grant", () => {
  const book = Object.freeze({ slug: "unknown-held-book", title: "A Short Story", short_description: "poetry", category_slug: "History_Strategy", publication_status: "HELD", reader_enabled: false });
  expect(discoveryMetadataForBook(book)).toEqual({ language: null, form: "unknown", genres: ["history-strategy"] });
  expect(book.reader_enabled).toBe(false);
  expect(book.publication_status).toBe("HELD");
  expect(discoveryMetadataForBook({ slug: "the-open-window", reader_enabled: false })).not.toHaveProperty("reader_enabled");
});

test("returned genre arrays cannot mutate shared accepted discovery records", () => {
  genresOfBook({ slug: "frankenstein" }).push("unreviewed");
  expect(genresOfBook({ slug: "frankenstein" })).toEqual(["gothic-fiction", "science-fiction"]);
});


test("prototype property names are not valid literary forms or canonical identities", () => {
  expect(discoveryMetadataForBook({ slug: "constructor", form: "constructor" }))
    .toEqual({ language: null, form: "unknown", genres: [] });
});


test.each([null, undefined, "not-a-book"])("malformed book input does not create classification or access", (book) => {
  expect(discoveryMetadataForBook(book)).toEqual({ language: null, form: "unknown", genres: [] });
});
