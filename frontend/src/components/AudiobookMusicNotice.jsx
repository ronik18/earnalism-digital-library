import { approvedAudiobookMusicCredit } from "../lib/audiobookMusicCredits";
export default function AudiobookMusicNotice({ book }) {
  const notice = approvedAudiobookMusicCredit(book);
  if (!notice) return null;
  const credit = notice.credit;
  return <aside className="mt-4 text-sm leading-relaxed" aria-label="Audiobook music licence and attribution" data-testid="audiobook-music-notice">
    <p>Music: {credit.music} — {credit.composer} (incompetech.com).</p>
    <p><a href={credit.source_url}>Music source</a> · <a href={credit.licence_url} rel="license">CC BY 4.0</a> (including its disclaimer of warranties).</p>
    <p>Changes: {credit.changes}</p>
    <p>The identified music retains its CC BY 4.0 copying, sharing and adaptation permissions; Earnalism terms add no restrictions to those permissions. This notice does not license the separate narration, covers, branding or software. Sign-in, territorial and Reading Pass requirements remain in force.</p>
  </aside>;
}
