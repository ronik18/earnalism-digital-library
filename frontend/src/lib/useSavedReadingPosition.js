import { useEffect, useState } from "react";
import { getReadingPassPosition } from "./readingPassApi";

const object = value => value !== null && typeof value === "object" && !Array.isArray(value);

// Navigation metadata never grants access. Only an exact absent-row response
// proves this book has no saved progress; malformed/foreign records stay unknown.
export function classifySavedReadingPosition(record, userId, slug, pages) {
  if (!userId || !slug || !object(record) || record.content_type !== "text" || record.content_id !== slug
    || !Number.isSafeInteger(record.version) || record.version < 0 || !object(record.position)
    || ("user_id" in record && record.user_id !== userId)) return "unknown";
  if (record.version === 0 && !("user_id" in record) && Object.keys(record.position).length === 0) return "new";
  if (record.user_id !== userId || record.version < 1 || !Object.keys(record.position).length) return "unknown";
  const position = record.position;
  const row = Array.isArray(pages?.pages) ? pages.pages.find(value => value?.page_number === position.canonical_page_index) : null;
  return record.publication_version_compatibility === "active" && position.publication_version_state === "bound"
    && Number.isSafeInteger(position.canonical_page_index) && position.canonical_page_index > 0
    && Number.isSafeInteger(pages?.page_count) && position.canonical_page_index <= pages.page_count && row?.chapter_id === position.chapter_id
    && pages?.schema_version && pages?.content_revision
    && position.segmentation_version === pages.schema_version && position.manifest_version === pages.content_revision
    ? "resume" : "existing";
}

export default function useSavedReadingPosition({ user, slug, enabled, canonicalPages }) {
  const eligible = Boolean(enabled && user?.id && user?.role === "user" && slug);
  const scope = eligible ? JSON.stringify([user.id, slug]) : "";
  const [result, setResult] = useState({ scope: "", record: null, loading: false });
  useEffect(() => {
    if (!scope) {
      setResult(current => current.scope ? { scope: "", record: null, loading: false } : current);
      return undefined;
    }
    let cancelled = false;
    setResult({ scope, record: null, loading: true });
    void (async () => {
      try {
        const record = await getReadingPassPosition({ contentType: "text", contentId: slug });
        if (!cancelled) setResult({ scope, record, loading: false });
      } catch {
        if (!cancelled) setResult({ scope, record: null, loading: false });
      }
    })();
    return () => { cancelled = true; };
  }, [scope, slug]);
  // Scope both in-flight completion and the current render across account/book
  // switches. No session start, progress save, local storage write or retry.
  let kind = eligible && result.scope === scope
    ? classifySavedReadingPosition(result.record, user.id, slug, canonicalPages) : "unknown";
  if (kind === "new") {
    // Reader resumes from device metadata first. An empty server row alone
    // cannot prove this browser has never opened the title. Storage is read-only.
    try {
      const key = `earnalism:reader-position:${encodeURIComponent(user.id)}:${encodeURIComponent(slug)}`;
      if (localStorage.getItem(key) !== null) kind = "existing";
    } catch { kind = "unknown"; }
  }
  return {
    kind,
    loading: eligible && (result.scope !== scope || result.loading),
  };
}
