import fs from "fs";
import path from "path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

describe("approved Reader direct-route contract", () => {
  const app = read("src/App.js");
  const vercel = JSON.parse(read("vercel.json"));

  test("keeps verified reader-enabled titles reachable before the generic reader 404 policy", () => {
    expect(app).toContain('<Route path="/reader/:slug" element={<ReaderV2 />} />');
    const rewrites = vercel.rewrites || [];
    const dynamicNotFound = rewrites.findIndex(
      (rule) => rule.source === "/reader/:slug" && rule.destination === "/api/not-found",
    );
    expect(dynamicNotFound).toBeGreaterThanOrEqual(0);

    [
      "/reader/a-white-heron",
      "/reader/a-white-heron/",
      "/reader/the-selfish-giant",
      "/reader/the-selfish-giant/",
    ].forEach((source) => {
      const index = rewrites.findIndex(
        (rule) => rule.source === source && rule.destination === "/index.html",
      );
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(dynamicNotFound);
    });
  });

  test("keeps all other reader slugs behind the explicit not-found policy", () => {
    expect(vercel.rewrites).toContainEqual({
      source: "/reader/:slug",
      destination: "/api/not-found",
    });
  });
});
