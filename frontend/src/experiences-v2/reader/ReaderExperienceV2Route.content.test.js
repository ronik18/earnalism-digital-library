import { paragraphsFromHtml } from "./readerContent";

describe("Reader canonical HTML rendering", () => {
  test("preserves paragraph markup as ordered Reader paragraphs", () => {
    expect(paragraphsFromHtml("<p>First.</p><p>Second.</p>")).toEqual(["First.", "Second."]);
  });

  test("preserves readable canonical text when a package uses no paragraph elements", () => {
    expect(paragraphsFromHtml("<article><h2>Opening</h2><div>Readable body</div></article>")).toEqual(["Opening", "Readable body"]);
  });
});
