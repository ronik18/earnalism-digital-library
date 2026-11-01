import acceptedDiscoveryMetadata from "../data/libraryDiscoveryMetadata.json";

// Discovery labels only. This module never determines publication, rights,
// preview, listening or Reading Pass eligibility.
export const LIBRARY_READING_FORMS = Object.freeze([
  { slug: "all", name: "All forms" },
  { slug: "novel", name: "Novels & novellas" },
  { slug: "short-story", name: "Short stories & collections" },
  { slug: "poetry", name: "Poetry & essays" },
  { slug: "nonfiction", name: "Nonfiction" },
]);

const normalizeLabel = (value) => typeof value === "string"
  ? value.trim().toLowerCase().replace(/[\s_]+/g, "-")
  : "";
const normalizeLanguage = (value) => {
  const language = normalizeLabel(value);
  if (["bengali", "bangla"].includes(language) || /^(?:bn|ben)(?:-|$)/.test(language)) return "bn";
  if (language === "english" || /^(?:en|eng)(?:-|$)/.test(language)) return "en";
  return null;
};
const FORM_ALIASES = Object.freeze({
  novel: "novel", novels: "novel", novella: "novel", novellas: "novel", "novels-and-novellas": "novel",
  "short-story": "short-story", "short-stories": "short-story", "story-collection": "short-story",
  "short-story-collection": "short-story", "short-stories-and-collections": "short-story", "short-fiction": "short-story",
  poetry: "poetry", poem: "poetry", poems: "poetry", verse: "poetry", essay: "poetry", essays: "poetry",
  "essay-collection": "poetry", "poetry-and-essays": "poetry", "essays-and-poetry": "poetry",
  nonfiction: "nonfiction", "non-fiction": "nonfiction",
});
const normalizeForm = (value) => {
  const form = normalizeLabel(value);
  return Object.prototype.hasOwnProperty.call(FORM_ALIASES, form) ? FORM_ALIASES[form] : null;
};
const normalizeGenres = (values) => [...new Set((Array.isArray(values) ? values : [values])
  .map(normalizeLabel)
  .filter((value) => /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value) && !["all", "none", "unknown"].includes(value)))];
const firstValid = (values, normalize) => values.map(normalize).find(Boolean);

export function discoveryMetadataForBook(book = {}) {
  const candidate = book && typeof book === "object" ? book : {};
  const slug = typeof candidate.slug === "string" ? candidate.slug.trim().toLowerCase() : "";
  const accepted = Object.prototype.hasOwnProperty.call(acceptedDiscoveryMetadata, slug) ? acceptedDiscoveryMetadata[slug] : null;
  const language = firstValid([candidate.language, candidate.language_code, candidate.lang, candidate.locale], normalizeLanguage)
    || accepted?.language || null;
  const form = firstValid([candidate.literary_form, candidate.reading_form, candidate.form], normalizeForm)
    || accepted?.form || "unknown";
  const explicitGenres = normalizeGenres(candidate.genres);
  const explicitGenre = normalizeGenres(candidate.genre);
  const genres = explicitGenres.length ? explicitGenres
    : explicitGenre.length ? explicitGenre
      : accepted?.genres ? [...accepted.genres]
        : normalizeGenres(candidate.category_slug);
  return { language, form, genres };
}

export const readingFormOfBook = (book = {}) => discoveryMetadataForBook(book).form;
export const genresOfBook = (book = {}) => discoveryMetadataForBook(book).genres;
