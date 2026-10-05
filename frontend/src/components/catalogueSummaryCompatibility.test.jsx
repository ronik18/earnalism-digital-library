import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
jest.mock("react-router-dom", () => ({ Link: ({ to, children, ...props }) =>
  require("react").createElement("a", { href: to, ...props }, children) }), { virtual: true });
import BookCard from "./BookCard";
import { DRACULA_FALLBACK_BOOK, canShowPreview } from "../lib/controlledLaunch";
import { languageOfBook, sortLibraryBooks, libraryPresentationForBook } from "../lib/libraryCatalog";
import { audiobookReleaseState } from "../lib/audioReleaseSafety";

test("Library summary has identical cards, discovery, preview and audio decisions", () => {
  const full = { ...DRACULA_FALLBACK_BOOK, description: "Detail-only introduction", about_author: "Detail biography",
    learnings: ["Detail"], benefits: ["Detail"],
    chapters: DRACULA_FALLBACK_BOOK.chapters.map(chapter => ({ ...chapter, word_count: 100, content_sha256: "a".repeat(64) })) };
  const { description, about_author, learnings, benefits, ...summary } = full;
  summary.chapters = full.chapters.map(({ id, title, is_preview, chapter_number }) => ({ id, title, is_preview, chapter_number }));
  expect(canShowPreview(summary)).toEqual(canShowPreview(full));
  expect(languageOfBook(summary)).toEqual(languageOfBook(full));
  expect(libraryPresentationForBook(summary)).toEqual(libraryPresentationForBook(full));
  expect(audiobookReleaseState(summary)).toEqual(audiobookReleaseState(full));
  expect(sortLibraryBooks([summary], "short-reads").map(b => b.slug)).toEqual(sortLibraryBooks([full], "short-reads").map(b => b.slug));
  const render = book => renderToStaticMarkup(<BookCard book={book} />);
  expect(render(summary)).toEqual(render(full));
});
