import fs from "fs";
import path from "path";

function source(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), "utf8");
}

describe("Book Detail unframed cover contract", () => {
  const detail = source("src/pages/BookDetail.jsx");
  const cover = source("src/components/BookCoverImage.jsx");
  const globalStyles = source("src/index.css");
  const referenceStyles = source("src/pages/BookDetailReference.css");

  test("uses the shared natural cover mode for every Book Detail edition", () => {
    expect(detail).toContain("<BookCoverImage");
    expect(detail).toContain("unframed");
    expect(detail).not.toContain("book-detail-cover-frame aspect-[3/4]");
    expect(cover).toContain("unframed = false");
    expect(cover).toContain("!unframed && sources.backgroundColor");
    expect(cover).toContain('"book-cover-image--unframed"');
  });

  test("does not leave a visible frame or a sampled-color gutter around artwork", () => {
    expect(globalStyles).toContain(".book-detail-cover-frame {");
    expect(globalStyles).toContain("padding: 0;");
    expect(globalStyles).toContain("border-radius: 0;");
    expect(globalStyles).toContain("background: transparent;");
    expect(globalStyles).toContain(".book-cover-image--unframed .book-cover-image__img");
    expect(globalStyles).toContain("height: auto;");
    expect(globalStyles).toContain("object-fit: contain;");
    expect(referenceStyles).toContain(".book-detail-page--reference .book-detail-cover-frame { padding:0; overflow:visible; border:0; border-radius:0; background:transparent; box-shadow:none; }");
  });

  test("keeps the established desktop and mobile cover widths", () => {
    expect(referenceStyles).toContain("max-width: 20rem");
    expect(referenceStyles).toContain("max-width: 10.8rem");
    expect(referenceStyles).toContain("@media (min-width: 440px) and (max-width: 767px)");
  });
});
