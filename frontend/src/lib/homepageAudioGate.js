import { audiobookReleaseState } from "./audioReleaseSafety";

export function approvedHomepageAudiobooks(books = []) {
  return books.filter((book) => audiobookReleaseState(book).canShowControls === true);
}

export function homepageAudiobooksForExposure(books = [], exposureEnabled = false) {
  return exposureEnabled ? approvedHomepageAudiobooks(books) : [];
}
