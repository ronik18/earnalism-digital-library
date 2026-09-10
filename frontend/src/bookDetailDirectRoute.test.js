import fs from "fs";
import path from "path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

describe("approved Book Detail direct-route contract", () => {
  const app = read("src/App.js");
  const vercel = JSON.parse(read("vercel.json"));

  test("keeps the two approved public titles reachable before the dynamic 404 policy", () => {
    expect(app).toContain('<Route path="/book/:slug" element={<BookDetail />} />');
    const rewrites = vercel.rewrites || [];
    const dynamicNotFound = rewrites.findIndex((rule) => rule.source === "/book/:slug" && rule.destination === "/api/not-found");
    expect(dynamicNotFound).toBeGreaterThanOrEqual(0);

    [
      "/book/a-white-heron",
      "/book/a-white-heron/",
      "/book/the-selfish-giant",
      "/book/the-selfish-giant/",
    ].forEach((source) => {
      const index = rewrites.findIndex((rule) => rule.source === source && rule.destination === "/index.html");
      expect(index).toBeGreaterThanOrEqual(0);
      expect(index).toBeLessThan(dynamicNotFound);
    });
  });

  test("retains the true-unknown and retired status-document policies", () => {
    const rewrites = vercel.rewrites || [];
    expect(rewrites).toContainEqual({ source: "/book/:slug", destination: "/api/not-found" });
    expect(rewrites).toContainEqual({ source: "/product", destination: "/api/removed-content?path=/product" });
  });
});
