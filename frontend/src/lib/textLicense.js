export function approvedTextLicense(book) {
  const n = book?.text_license;
  if (!n || n.schema_version !== "earnalism.text-license.v1" || n.slug !== book?.slug || n.license !== "CC-BY-SA-4.0" || n.license_url !== "https://creativecommons.org/licenses/by-sa/4.0/") return null;
  if (!["attribution", "changes", "scope", "disclaimer"].every(k => typeof n[k] === "string" && n[k].trim())) return null;
  try {
    if (![n.source_url, n.contributors_url].every(v => { const u = new URL(v); return u.protocol === "https:" && ["bn.wikisource.org", "en.wikisource.org"].includes(u.hostname); })) return null;
  } catch { return null; }
  return n;
}
