import { getShelfVariant } from "./homeShelfRunway";

test("shelf variants adapt without a title allowlist", () => {
  expect(getShelfVariant({ display_mode: "spotlight", books: [{}] })).toBe("spotlight");
  expect(getShelfVariant({ display_mode: "duo", books: [{}, {}] })).toBe("duo-shelf");
  expect(getShelfVariant({ display_mode: "runway", books: [{}, {}, {}] })).toBe("runway");
  expect(getShelfVariant({ display_mode: "overflow", books: [{}, {}, {}] })).toBe("shelf-feature");
  expect(getShelfVariant({ books: [{}, {}, {}] })).toBe("shelf-feature");
});
