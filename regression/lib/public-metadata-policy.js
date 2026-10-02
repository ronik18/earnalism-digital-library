const LICENSE_URLS = Object.freeze({
  'CC-BY-SA-4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
  'CC0-1.0': 'https://creativecommons.org/publicdomain/zero/1.0/',
});
function validSourceURL(value, license) {
  if (typeof value !== 'string') return false;
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return false;
    if (license === 'CC-BY-SA-4.0') return ['bn.wikisource.org', 'en.wikisource.org'].includes(url.hostname);
    return url.hostname === 'standardebooks.org' || (
      ['github.com', 'raw.githubusercontent.com'].includes(url.hostname) && url.pathname.startsWith('/standardebooks/')
    );
  } catch { return false; }
}
function validPublicTextLicense(book) {
  const notice = book?.text_license;
  return Boolean(notice && !Array.isArray(notice) && notice.schema_version === 'earnalism.text-license.v1'
    && typeof book.slug === 'string' && book.slug && notice.slug === book.slug
    && Object.prototype.hasOwnProperty.call(LICENSE_URLS, notice.license)
    && notice.license_url === LICENSE_URLS[notice.license]
    && ['attribution', 'changes', 'scope', 'disclaimer'].every(key => typeof notice[key] === 'string' && notice[key].trim())
    && [notice.source_url, notice.contributors_url].every(url => validSourceURL(url, notice.license)));
}
// Return every key except the legally required source URL in a validated,
// direct public-book license notice. This neither mutates nor authorizes data.
function publicMetadataKeys(value) {
  if (Array.isArray(value)) return value.flatMap(publicMetadataKeys);
  if (!value || typeof value !== 'object') return [];
  const approvedNotice = validPublicTextLicense(value) ? value.text_license : null;
  function visit(item) {
    if (Array.isArray(item)) return item.flatMap(visit);
    if (!item || typeof item !== 'object') return [];
    return Object.entries(item).flatMap(([key, child]) => [
      ...(item === approvedNotice && key === 'source_url' ? [] : [key]), ...visit(child),
    ]);
  }
  return visit(value);
}
module.exports = { publicMetadataKeys, validPublicTextLicense };
