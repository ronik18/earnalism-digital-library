import { approvedTextLicense } from "../lib/textLicense";
export default function LicensedTextNotice({ book }) {
  const notice = approvedTextLicense(book);
  if (!notice) return null;
  return <aside className="mt-4 text-sm leading-relaxed" aria-label="Text licence and attribution" data-testid="text-license-notice">
    <p>{notice.attribution}</p>
    <p><a href={notice.source_url}>Exact source edition</a> · <a href={notice.contributors_url}>Transcription contributors</a> · <a href={notice.license_url} rel="license">CC BY-SA 4.0</a></p>
    <p>Changes: {notice.changes}</p><p>{notice.scope}</p><p>{notice.disclaimer}</p>
    <p>The delivered transcription may be copied, shared and adapted under CC BY-SA 4.0. Copyrightable adaptations of this text are offered under the same licence.</p>
  </aside>;
}
