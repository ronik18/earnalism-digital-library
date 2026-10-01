const assert = require("node:assert/strict");
const { frontendResourceUrl } = require("../regression/utils/envGuard");

const priorMode = process.env.REGRESSION_MODE;
const priorFrontend = process.env.REGRESSION_FRONTEND_URL;
try {
  const cover = "https://theearnalism.com/assets/books/agentic-ai-with-python/front-cover-release-20261001.webp";
  process.env.REGRESSION_MODE = "pr";
  process.env.REGRESSION_FRONTEND_URL = "http://127.0.0.1:13001";
  assert.equal(frontendResourceUrl(cover), "http://127.0.0.1:13001/assets/books/agentic-ai-with-python/front-cover-release-20261001.webp");
  assert.equal(frontendResourceUrl("/assets/books/front.webp"), "http://127.0.0.1:13001/assets/books/front.webp");
  assert.equal(frontendResourceUrl("https://res.cloudinary.com/example/cover.webp"), "https://res.cloudinary.com/example/cover.webp");
  assert.equal(frontendResourceUrl("https://theearnalism.com/api/books"), "https://theearnalism.com/api/books");
  assert.equal(frontendResourceUrl("https://theearnalism.com.example.test/assets/cover.webp"), "https://theearnalism.com.example.test/assets/cover.webp");
  process.env.REGRESSION_MODE = "canary";
  assert.equal(frontendResourceUrl(cover), cover);
  process.env.REGRESSION_MODE = "go-live";
  assert.equal(frontendResourceUrl(cover), cover);
  console.log("PASS: candidate assets use loopback; external origins and production canaries remain exact");
} finally {
  if (priorMode === undefined) delete process.env.REGRESSION_MODE;
  else process.env.REGRESSION_MODE = priorMode;
  if (priorFrontend === undefined) delete process.env.REGRESSION_FRONTEND_URL;
  else process.env.REGRESSION_FRONTEND_URL = priorFrontend;
}
