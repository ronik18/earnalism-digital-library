import fs from 'fs';
import path from 'path';
import { formatReadingPassTime } from './ReadingPassTimer';

const timerSource = fs.readFileSync(path.join(process.cwd(), 'src/components/ReadingPass/ReadingPassTimer.jsx'), 'utf8');
const paywallSource = fs.readFileSync(path.join(process.cwd(), 'src/components/ReadingPass/ReadingPassPaywall.jsx'), 'utf8');
const styles = fs.readFileSync(path.join(process.cwd(), 'src/components/ReadingPass/ReadingPass.css'), 'utf8');
const readerSource = fs.readFileSync(path.join(process.cwd(), 'src/pages/Reader.jsx'), 'utf8');
const accountSource = fs.readFileSync(path.join(process.cwd(), 'src/pages/Account.jsx'), 'utf8');
const apiSource = fs.readFileSync(path.join(process.cwd(), 'src/lib/readingPassApi.js'), 'utf8');

describe('Reading Pass responsive access UI', () => {
  test('formats authoritative seconds as HH:MM:SS', () => {
    expect(formatReadingPassTime(0)).toBe('00:00:00');
    expect(formatReadingPassTime(65)).toBe('00:01:05');
    expect(formatReadingPassTime(3661)).toBe('01:01:01');
    expect(formatReadingPassTime(-10)).toBe('00:00:00');
  });

  test('keeps the timer labelled and exposes status beyond color', () => {
    expect(timerSource).toContain('aria-label="Reading Pass status"');
    expect(timerSource).toContain('{status}');
    expect(timerSource).toContain('contentType');
    expect(timerSource).toContain('aria-label="Add Reading Pass time"');
  });

  test('paywall is modal, keyboard trapped, escape closable, and returns focus', () => {
    expect(paywallSource).toContain('role="dialog"');
    expect(paywallSource).toContain('aria-modal="true"');
    expect(paywallSource).toContain("event.key === 'Escape'");
    expect(paywallSource).toContain("event.key !== 'Tab'");
    expect(paywallSource).toContain('previous?.focus?.()');
  });

  test('supports required responsive geometry and safe areas', () => {
    expect(styles).toContain('min-width: 44px');
    expect(styles).toContain('min-height: 44px');
    expect(styles).toContain('env(safe-area-inset-top');
    expect(styles).toContain('env(safe-area-inset-bottom');
    expect(styles).toContain('@media (max-width: 640px)');
    expect(styles).toContain('@media (max-width: 360px)');
    expect(styles).toContain('@media (prefers-reduced-motion: reduce)');
  });

  test('reader uses canonical server pages and clears protected HTML on pause', () => {
    expect(readerSource).toContain('getReadingPassPage(');
    expect(readerSource).toContain('canonicalPageIndex');
    expect(readerSource).toContain("setProcessedHtml('')");
    expect(readerSource).toContain('SESSION_ACTIVE_ELSEWHERE');
    expect(readerSource).toContain('resumeReadingPass');
  });

  test('locked reader CTAs return to a real signup route and clear the paywall before reopening preview', () => {
    expect(readerSource).toContain("navigate(`/signup?next=${encodeURIComponent(getCurrentReaderPath())}`)");
    expect(readerSource).not.toContain("navigate(`/register?next=${encodeURIComponent(getCurrentReaderPath())}`)");
    expect(readerSource).toContain('setLockedState(null);');
    expect(readerSource).toContain('setReadingPassPaywall(null);');
    expect(readerSource).toContain('goToCanonicalPage(Math.min(3, canonicalPageIndex));');
  });

  test('audiobooks have no public preview and begin at the protected entitlement boundary', () => {
    expect(apiSource).not.toContain('/preview/manifest');
    expect(apiSource).toContain('duration_seconds: 0');
    expect(apiSource).toContain("content_type: 'audio'");
    expect(apiSource).toContain('withCredentials: true');
    expect(readerSource).toContain("syncReadingPassAudioState('playing')");
    expect(paywallSource).not.toContain('Replay free preview');
  });

  test('account exposes multi-device session revocation only with Reading Pass enabled', () => {
    expect(accountSource).toContain('getReadingPassConfig');
    expect(accountSource).toContain('getReadingPassDevices');
    expect(accountSource).toContain('revokeReadingPassDevice');
    expect(accountSource).toContain('{readingPassEnabled && (');
    expect(accountSource).toContain('only one may consume Reading Pass time');
  });
});
