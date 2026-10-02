/** Public share URLs never carry session tokens, tracking queries or private fragments. */
export function canonicalShareUrl(value) {
  try {
    const url = new URL(value);
    if (!['https:', 'http:'].includes(url.protocol)) return '';
    if (['theearnalism.com', 'www.theearnalism.com'].includes(url.hostname)) {
      url.protocol = 'https:';
      url.hostname = 'theearnalism.com';
      url.port = '';
    }
    url.search = '';
    url.hash = '';
    url.username = '';
    url.password = '';
    return url.href;
  } catch { return ''; }
}
