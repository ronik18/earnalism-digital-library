/** Remove only our generated fallback, never runtime application markup/assets. */
export function cleanStaticSeoTemplate(source) {
  return String(source).replace(/<main\b[^>]*\bdata-static-seo-snapshot="true"[^>]*>[\s\S]*?<\/main>/g, '');
}
