const path = require("path");

module.exports = {
  rootDir: path.resolve(__dirname, ".."),
  testEnvironment: "node",
  testMatch: ["<rootDir>/regression/modules/**/*.test.js"],
  modulePathIgnorePatterns: [
    "<rootDir>/.venv/",
    "<rootDir>/venv/",
    "<rootDir>/.venv-audio/",
    "<rootDir>/output/",
    "<rootDir>/frontend/node_modules/",
  ],
  testPathIgnorePatterns: [
    "<rootDir>/.venv/",
    "<rootDir>/venv/",
    "<rootDir>/.venv-audio/",
    "<rootDir>/output/",
    "<rootDir>/frontend/node_modules/",
  ],
  testTimeout: 60000,
  globalSetup: "<rootDir>/regression/globalSetup.js",
  globalTeardown: "<rootDir>/regression/globalTeardown.js",
  reporters: [
    "default",
    "<rootDir>/regression/reporters/moduleScoreReporter.js",
  ],
  testResultsProcessor: "<rootDir>/regression/utils/report.js",
};
