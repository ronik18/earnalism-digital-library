const LICENSE_URLS = {
  "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
  "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
};

function validSourceURL(value, license) {
  const url = new URL(value);
  if (url.protocol !== "https:" || url.username || url.password) return false;
  if (license === "CC-BY-SA-4.0") {
    return ["bn.wikisource.org", "en.wikisource.org"].includes(url.hostname);
  }
  return url.hostname === "standardebooks.org" || (
    ["github.com", "raw.githubusercontent.com"].includes(url.hostname)
    && url.pathname.startsWith("/standardebooks/")
  );
}

export function approvedTextLicense(book) {
  const notice = book?.text_license;
  if (!notice || notice.schema_version !== "earnalism.text-license.v1" || notice.slug !== book?.slug
    || !Object.prototype.hasOwnProperty.call(LICENSE_URLS, notice.license)
    || notice.license_url !== LICENSE_URLS[notice.license]) return null;
  if (!["attribution", "changes", "scope", "disclaimer"].every(key => typeof notice[key] === "string" && notice[key].trim())) return null;
  try {
    if (![notice.source_url, notice.contributors_url].every(value => validSourceURL(value, notice.license))) return null;
  } catch { return null; }
  return notice;
}
