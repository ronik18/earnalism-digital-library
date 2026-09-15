import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/ReaderTestimonialsSection.jsx"), "utf8");
const styles = fs.readFileSync(path.join(process.cwd(), "src/components/ReaderTestimonialsSection.css"), "utf8");

describe("ReaderTestimonialsSection", () => {
  test("renders the four approved editorial sample cards with local avatars", () => {
    expect(source).toContain("What Our Readers Say");
    expect(source).toContain("Small notes from readers who found quiet companionship, beauty, and depth inside Earnalism.");
    expect(source).toContain("Editorial sample notes, ready to be replaced with verified reader quotes.");
    expect(source.match(/avatar: "\/assets\/testimonials\//g)).toHaveLength(4);
    ["Ananya S.", "Ritam D.", "Mrittika P.", "Soham R."].forEach((name) => expect(source).toContain(name));
    expect(source).toContain('<blockquote>“{quote}”</blockquote>');
  });

  test("keeps the responsive and reduced-motion presentation constrained", () => {
    expect(styles).toContain("grid-template-columns: repeat(4, minmax(0, 1fr))");
    expect(styles).toContain("grid-template-columns: repeat(2, minmax(0, 1fr))");
    expect(styles).toContain(".reference-reader-testimonials__grid { grid-template-columns: 1fr; }");
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
