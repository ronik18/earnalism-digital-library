#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const resultsPath = path.resolve(process.argv[2] || "regression/results.json");
if (!fs.existsSync(resultsPath)) {
  console.error(`Missing regression results: ${resultsPath}`);
  process.exit(1);
}

const raw = JSON.parse(fs.readFileSync(resultsPath, "utf8"));
const report = raw.regression || raw;
if (!report.modules || !Array.isArray(report.modules)) {
  console.error("Regression results do not contain module scores.");
  process.exit(1);
}

const failures = report.modules.filter((module) => module.mandatory && module.score !== 100);
if (failures.length) {
  console.error("GO LIVE regression gate failed:");
  for (const module of failures) {
    console.error(`- ${module.moduleName}: ${module.score}`);
  }
  process.exit(1);
}

console.log("GO LIVE regression gate passed: all mandatory modules scored 100.");
