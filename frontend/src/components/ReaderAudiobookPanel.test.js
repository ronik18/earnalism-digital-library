import fs from 'fs';
import path from 'path';
import { formatAudiobookTime } from './ReaderAudiobookPanel';

const panelSource = fs.readFileSync(
  path.join(process.cwd(), 'src/components/ReaderAudiobookPanel.jsx'),
  'utf8',
);
const panelStyles = fs.readFileSync(
  path.join(process.cwd(), 'src/components/ReaderAudiobookPanel.css'),
  'utf8',
);

describe('ReaderAudiobookPanel', () => {
  test('formats short and long audiobook positions', () => {
    expect(formatAudiobookTime(0)).toBe('0:00');
    expect(formatAudiobookTime(65)).toBe('1:05');
    expect(formatAudiobookTime(3661)).toBe('1:01:01');
  });

  test('exposes the essential listening controls with explicit labels', () => {
    expect(panelSource).toContain('aria-label="Skip back 15 seconds"');
    expect(panelSource).toContain('aria-label="Skip forward 30 seconds"');
    expect(panelSource).toContain('aria-label="Playback speed"');
    expect(panelSource).toContain('aria-label="Audiobook volume"');
    expect(panelSource).toContain('aria-label="Seek within current audiobook section"');
    expect(panelSource).toContain('aria-modal="true"');
    expect(panelSource).toContain("event.key === 'Escape'");
  });

  test('uses the front cover as artwork and ambient backdrop without owning an audio element', () => {
    expect(panelSource).toContain('reader-listening-room__backdrop');
    expect(panelSource).toContain('reader-listening-room__artwork');
    expect(panelSource).not.toMatch(/<audio|speechSynthesis|SpeechSynthesisUtterance/);
  });

  test('does not repeat book and author details outside the front cover', () => {
    expect(panelSource).not.toContain('reader-listening-room__identity');
    expect(panelSource).toContain("{title || 'Audiobook'} audiobook player");
    expect(panelSource).toContain('className="sr-only"');
    expect(panelSource).toContain('data-book-slug={bookSlug || undefined}');
  });

  test('maintains accessible targets and a mobile full-screen listening room', () => {
    expect(panelStyles).toContain('min-width: 44px;');
    expect(panelStyles).toContain('min-height: 44px;');
    expect(panelStyles).toContain('min-height: 100dvh;');
    expect(panelStyles).toContain('@media (prefers-reduced-motion: reduce)');
  });
});
