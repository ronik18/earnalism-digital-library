const path = require("path");
const fs = require("fs");
const { createRequire } = require("module");
const frontendRequire = createRequire(path.resolve(__dirname, "../../../frontend/package.json"));
const webpack = frontendRequire("webpack");
const config = require("./visual-harness.webpack.config.cjs");

webpack(config, (error, stats) => {
  if (error) throw error;
  const info = stats.toJson({ all: false, errors: true, warnings: true, assets: true });
  if (stats.hasErrors()) throw new Error(info.errors.map((entry) => entry.message).join("\n"));
  if (info.warnings?.length) process.stderr.write(`${info.warnings.map((entry) => entry.message).join("\n")}\n`);
  const logoSource = path.resolve(__dirname, "../../../frontend/public/assets/brand/earnalism-logo-text.png");
  const logoTarget = path.join(config.output.path, "assets", "brand", "earnalism-logo-text.png");
  fs.mkdirSync(path.dirname(logoTarget), { recursive: true });
  fs.copyFileSync(logoSource, logoTarget);
  process.stdout.write(`VISUAL_HARNESS_BUNDLE=passed assets=${info.assets.map((asset) => asset.name).join(",")}\n`);
});
