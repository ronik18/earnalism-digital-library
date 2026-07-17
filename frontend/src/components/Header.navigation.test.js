import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/Header.jsx"), "utf8");

describe("premium header navigation", () => {
  test("uses only valid application routes and approved library filters", () => {
    expect(source).toContain('{ to: "/library", label: "Library" }');
    expect(source).toContain('label: "Bengali Classics"');
    expect(source).toContain('label: "English Classics"');
    expect(source).toContain('{ to: "/library?availability=approved-audiobook", label: "Audiobooks" }');
    expect(source).toContain('{ to: "/pricing", label: "Membership" }');
    expect(source).toContain('{ to: "/about", label: "About" }');
    expect(source).toContain('const accountHref = isAuthed ? "/account" : "/login"');
    expect(source).not.toMatch(/href=["']#|to=["']#|javascript:/i);
  });

  test("uses a working library CTA on desktop and mobile", () => {
    expect(source).toContain('data-testid="header-cta-library">Start Reading');
    expect(source).toContain('data-testid="mobile-cta-library">Start Reading');
  });
});
