import fs from "fs";
import path from "path";

const sourceRoot = path.resolve(__dirname);
const forbiddenCopy = [
  "chapter 1 is free",
  "first chapter free",
  "chapter 1 is on us",
  "first 3 minutes free",
  "first 180 seconds free",
  "free audiobook preview",
  "free listening sample",
];

function collectProductionSource(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const filePath = path.join(directory, entry.name);
    if (entry.isDirectory()) return collectProductionSource(filePath);
    if (!/\.(js|jsx)$/.test(entry.name) || /\.(test|spec)\.(js|jsx)$/.test(entry.name)) return [];
    return [filePath];
  });
}

describe("public product-truth copy", () => {
  test("production React source has the canonical-page and zero-public-audio contract", () => {
    const source = collectProductionSource(sourceRoot)
      .map((filePath) => fs.readFileSync(filePath, "utf8"))
      .join("\n")
      .toLowerCase();

    expect(source).toContain("read the first 3 pages free.");
    expect(source).toContain("listening requires an active reading pass.");
    forbiddenCopy.forEach((phrase) => expect(source).not.toContain(phrase));
  });
});
