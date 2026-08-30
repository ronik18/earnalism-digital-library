import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/pages/MyLibrary.jsx"), "utf8");

describe("My Library shell", () => {
  test("relies on the routed public header instead of rendering a second experience header", () => {
    expect(source).toContain("<ExperienceShell");
    expect(source).not.toContain("<ExperienceHeader");
    expect(source).toContain('data-testid="my-library-mobile"');
  });
});
