const fs = require("fs");
const path = require("path");

module.exports = async () => {
  const root = path.resolve(__dirname, "..");
  const artifactsDir = path.join(root, "regression", "artifacts");
  fs.mkdirSync(artifactsDir, { recursive: true });
  fs.mkdirSync(path.join(artifactsDir, "screenshots"), { recursive: true });
  fs.mkdirSync(path.join(artifactsDir, "traces"), { recursive: true });
  fs.mkdirSync(path.join(artifactsDir, "logs"), { recursive: true });

  const regressionRunId = process.env.REGRESSION_RUN_ID || `reg-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
  process.env.REGRESSION_RUN_ID = regressionRunId;

  fs.writeFileSync(
    path.join(artifactsDir, "run-state.json"),
    JSON.stringify({
      regressionRunId,
      mode: process.env.REGRESSION_MODE || "pr",
      startedAt: new Date().toISOString(),
    }, null, 2),
  );
};
