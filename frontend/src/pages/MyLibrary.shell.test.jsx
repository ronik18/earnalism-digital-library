import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/pages/MyLibrary.jsx"), "utf8");

describe("My Library shell", () => {
  test("relies on the routed public header instead of rendering a second experience header", () => {
    expect(source).toContain("<ExperienceShell");
    expect(source).not.toContain("<ExperienceHeader");
    expect(source).toContain('data-testid="my-library-mobile"');
  });

  test("uses a truthful empty shelf instead of inventing saved-title or resume data", () => {
    expect(source).toContain("This page doesn’t yet show saved books or reading progress. Explore the Library to choose your next read.");
    expect(source).toContain('to="/library?availability=reader-ready"');
    expect(source).toContain('to="/pricing"');
    expect(source).not.toMatch(/Dracula|continue reading|saved progress/i);
  });

  test("keeps the supplied Header out of the redesign while exposing keyboard-reachable customer actions", () => {
    expect(source).not.toContain("<Header");
    expect(source).toContain('data-testid="my-library-browse-ready"');
    expect(source).toContain("<ExperienceBottomNavigation");
  });
});
