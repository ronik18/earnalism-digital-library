import { normalizeReaderContentHtml } from './readerContent';

describe('normalizeReaderContentHtml', () => {
  test('turns legacy plain text into semantic paragraphs and line breaks', () => {
    expect(normalizeReaderContentHtml('প্রথম অনুচ্ছেদ।\n\nদ্বিতীয় অনুচ্ছেদ।\nদ্বিতীয় লাইন।'))
      .toBe('<p>প্রথম অনুচ্ছেদ।</p><p>দ্বিতীয় অনুচ্ছেদ।<br>দ্বিতীয় লাইন।</p>');
  });

  test('escapes plain text markup before rendering', () => {
    const html = normalizeReaderContentHtml('৫ < ৬\n\nনিরাপদ পাঠ।');

    expect(html).toContain('৫ &lt; ৬');
    expect(html).toContain('নিরাপদ পাঠ।');
    expect(html).not.toContain('< ৬');
  });

  test('preserves existing html for the sanitizer pipeline', () => {
    expect(normalizeReaderContentHtml('<p>Already structured.</p>'))
      .toBe('<p>Already structured.</p>');
  });
});
