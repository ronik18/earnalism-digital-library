const path = require("path");

module.exports = {
  rootDir: path.resolve(__dirname, ".."),
  testEnvironment: "node",
  testMatch: ["<rootDir>/regression/modules/**/*.test.js"],
  testTimeout: 60000,
  globalSetup: "<rootDir>/regression/globalSetup.js",
  globalTeardown: "<rootDir>/regression/globalTeardown.js",
  reporters: [
    "default",
    "<rootDir>/regression/reporters/moduleScoreReporter.js",
  ],
  testResultsProcessor: "<rootDir>/regression/utils/report.js",
};
