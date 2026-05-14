# New Book Upload Guide

This guide explains how to prepare, upload, preview, and publish a new Earnalism book from the admin dashboard.

## 1. Purpose

The upload pipeline converts a manuscript into clean reader-ready content while keeping the original uploaded file unchanged. It:

- Extracts manuscript text and basic formatting.
- Preserves paragraphs, headings, lists, quotes, bold, and italic text where supported by the file.
- Removes unsafe HTML, scripts, styles, and unsupported embedded elements.
- Uploads manuscript images and covers to Cloudinary.
- Stores processing status, warnings, and errors for admin review before publishing.

## 2. Supported Book Formats

Use one of these formats for chapter uploads:

- DOCX
- Markdown: `.md` or `.markdown`
- HTML
- Plain text: `.txt`

Maximum chapter upload size: 50MB.

PDF uploads are not currently supported for manuscript extraction. Scanned PDFs and image-only books require OCR before upload.

## 3. Recommended Manuscript Preparation

Before upload:

- Keep one chapter per upload file.
- Use real heading styles in DOCX for chapter headings.
- Use normal paragraphs, not manual line breaks after every sentence.
- Remove comments, tracked changes, hidden text, and page headers/footers.
- Use standard bold, italic, block quote, bullet list, and numbered list formatting.
- Save plain text files as UTF-8.
- For Bengali books, use Unicode Bengali text. Do not use legacy font-encoded text.

## 4. Front Cover Requirements

Front cover is required before publishing.

Recommended:

- JPG, PNG, WebP, or GIF
- Portrait ratio, ideally close to 3:4
- At least 1200px tall when possible
- Clear title and author/publisher text
- Maximum file size: 10MB

The app stores the original Cloudinary URL and optimized display versions. Cover images are displayed without distortion.

## 5. Back Cover Requirements

Back cover is optional.

Recommended:

- JPG, PNG, WebP, or GIF
- Same aspect ratio as the front cover when possible
- Maximum file size: 10MB
- Include synopsis, author note, or publisher information if available

Back cover appears only on the book detail page where it naturally fits.

## 6. Bengali Book Support Notes

Bengali Unicode text is supported for:

- Book title
- Author name
- Chapter title
- Paragraph body
- Headings
- Table of contents
- Admin preview
- Reader display

Best practices:

- Use Unicode Bengali text.
- Avoid scanned images for body text unless OCR has already been done.
- Review matras, conjunct characters, punctuation, and quotes in admin preview.
- Check the reader on mobile before publishing.

Unsupported Bengali cases:

- Scanned Bengali PDFs without OCR
- Image-only manuscripts
- Legacy non-Unicode Bengali font encodings

## 7. Step-by-Step Admin Upload Process

1. Sign in to the admin dashboard.
2. Open the Books tab.
3. Click New book.
4. Fill in title, author, category, descriptions, reading time, and other metadata.
5. Save as Draft first.
6. Open the saved book again.
7. Upload the front cover.
8. Upload the back cover if available.
9. Add a chapter.
10. Save the chapter title.
11. Open the chapter editor and upload the manuscript file for that chapter.
12. Wait for processing to complete.
13. Review status, warnings, and preview.
14. Repeat for each chapter.
15. Publish only after all chapters show `ready`.

## 8. Preview And Formatting Validation

Before publishing, check:

- Chapter title displays correctly.
- Paragraph breaks are preserved.
- Headings are clear.
- Lists are readable.
- Quotes are styled correctly.
- Bold and italic text survived where expected.
- No raw HTML appears in the preview.
- No broken image placeholders appear.
- Long lines wrap correctly on mobile.
- Bengali text, if present, displays with proper line height and characters.

Warnings are not always blockers, but they should be reviewed. A `failed` status must be fixed before publishing.

## 9. Publishing Checklist

Publish only when:

- Title is present.
- Front cover is uploaded.
- Every chapter has status `ready`.
- Processing errors are empty.
- Important warnings have been reviewed.
- Reader preview works.
- Book detail page looks correct.
- Back cover, if uploaded, appears correctly.
- Bengali text, if present, has been checked on desktop and mobile.

## 10. Reader Verification Checklist

After publishing:

- Open the library page and find the book.
- Open the book detail page.
- Confirm cover and metadata are correct.
- Open the reader.
- Check the table of contents.
- Open the first chapter.
- Move between previous and next chapters.
- Check mobile layout.
- Confirm images load and keep aspect ratio.
- Confirm no raw or broken HTML appears.

## 11. Common Issues And Fixes

**Issue: Upload says unsupported format**

Use DOCX, Markdown, HTML, or TXT only.

**Issue: Text looks garbled**

Re-save the manuscript as UTF-8. For Bengali, confirm the manuscript uses Unicode text.

**Issue: Too many blank lines**

Clean extra blank paragraphs in the source file and re-upload.

**Issue: Headings are missing**

Use built-in heading styles in DOCX or heading syntax in Markdown/HTML.

**Issue: Images do not appear**

Check that the file contains embedded images, not links to private local files. Re-upload after confirming Cloudinary is configured.

**Issue: Upload fails during image processing**

Try smaller images or reduce chapter file size. If it still fails, check Cloudinary configuration.

**Issue: Publishing is blocked**

Review the displayed issues. Usually the book needs a front cover or one chapter is still processing/failed.

## 12. Currently Not Supported

- Scanned PDFs without OCR
- Image-only manuscripts without OCR
- Direct PDF manuscript extraction
- Automatic OCR from cover or page images
- Automatic chapter splitting from one full-book file
- Advanced page layout preservation from DOCX/PDF
- Custom embedded fonts from uploaded files
