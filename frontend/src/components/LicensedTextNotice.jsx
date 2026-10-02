import { approvedTextLicense } from "../lib/textLicense";
export default function LicensedTextNotice({ book }) {
  const notice = approvedTextLicense(book);
  if (!notice) return null;
  const shareAlike = notice.license === "CC-BY-SA-4.0";
  return <aside className="mt-4 text-sm leading-relaxed" aria-label="Text licence and attribution" data-testid="text-license-notice">
    <p>{notice.attribution}</p>
    <p><a href={notice.source_url}>Exact source edition</a> · <a href={notice.contributors_url}>Transcription contributors</a> · <a href={notice.license_url} rel="license">{shareAlike ? "CC BY-SA 4.0" : "CC0 1.0"}</a></p>
    <p>Changes: {notice.changes}</p><p>{notice.scope}</p><p>{notice.disclaimer}</p>
    <p>{shareAlike ? "The delivered transcription may be copied, shared and adapted under CC BY-SA 4.0. Copyrightable adaptations of this text are offered under the same licence." : "The identified transcription contributions are offered under CC0 1.0. This notice does not dedicate covers or other Earnalism assets."}</p>
  </aside>;
}
