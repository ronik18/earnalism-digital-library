const fs = require("fs");
const path = require("path");

function loadModules() {
  return JSON.parse(fs.readFileSync(path.resolve("regression", "config", "modules.json"), "utf8"));
}

function currentMode() {
  return (process.env.REGRESSION_MODE || "pr").toLowerCase();
}

function moduleForTestFile(testFilePath, modules) {
  const base = path.basename(testFilePath || "");
  return modules.find((item) => base.includes(item.filePattern)) || {
    moduleName: base || "Unknown module",
    mandatory: true,
    allowedSkipModes: [],
  };
}

function assertionFailure(assertion) {
  return {
    title: assertion.fullName || assertion.title,
    status: assertion.status,
    failureMessages: assertion.failureMessages || [],
    ancestorTitles: assertion.ancestorTitles || [],
  };
}

function buildModuleReport(jestResults) {
  const mode = currentMode();
  const modules = loadModules();
  const byName = new Map();

  for (const testResult of jestResults.testResults || []) {
    const mod = moduleForTestFile(testResult.testFilePath, modules);
    const key = mod.moduleName;
    if (!byName.has(key)) {
      byName.set(key, {
        moduleName: key,
        totalChecks: 0,
        passedChecks: 0,
        failedChecks: 0,
        skippedChecks: 0,
        score: 0,
        mandatory: mod.mandatory !== false,
        allowedSkipForMode: (mod.allowedSkipModes || []).includes(mode),
        failures: [],
        artifacts: [],
      });
    }
    const row = byName.get(key);
    for (const assertion of testResult.testResults || testResult.assertionResults || []) {
      row.totalChecks += 1;
      if (assertion.status === "passed") row.passedChecks += 1;
      else if (assertion.status === "pending" || assertion.status === "skipped" || assertion.status === "todo") {
        row.skippedChecks += 1;
        row.failures.push(assertionFailure(assertion));
      } else {
        row.failedChecks += 1;
        row.failures.push(assertionFailure(assertion));
      }
    }
    if (testResult.failureMessage && !(testResult.assertionResults || []).length) {
      row.totalChecks += 1;
      row.failedChecks += 1;
      row.failures.push({ title: path.basename(testResult.testFilePath), status: "failed", failureMessages: [testResult.failureMessage] });
    }
  }

  for (const mod of modules) {
    if (!byName.has(mod.moduleName)) {
      byName.set(mod.moduleName, {
        moduleName: mod.moduleName,
        totalChecks: 0,
        passedChecks: 0,
        failedChecks: 0,
        skippedChecks: 0,
        score: 0,
        mandatory: mod.mandatory !== false,
        allowedSkipForMode: (mod.allowedSkipModes || []).includes(mode),
        failures: [{ title: "module file missing or not executed", status: "failed", failureMessages: [] }],
        artifacts: [],
      });
    }
  }

  const moduleScores = [...byName.values()].map((row) => {
    const effectiveFailed = row.failedChecks + (row.allowedSkipForMode ? 0 : row.skippedChecks);
    const denominator = Math.max(1, row.totalChecks);
    const passed = Math.max(0, row.totalChecks - effectiveFailed);
    return {
      ...row,
      score: Math.round((passed / denominator) * 10000) / 100,
    };
  });

  const mandatoryFailures = moduleScores.filter((row) => row.mandatory && row.score !== 100);
  return {
    regressionRunId: process.env.REGRESSION_RUN_ID || "",
    mode,
    generatedAt: new Date().toISOString(),
    pass: mandatoryFailures.length === 0,
    mandatoryFailures: mandatoryFailures.map((row) => row.moduleName),
    modules: moduleScores,
    summary: {
      totalModules: moduleScores.length,
      passedModules: moduleScores.filter((row) => row.score === 100).length,
      failedMandatoryModules: mandatoryFailures.length,
    },
  };
}

function writeReport(report) {
  const outPath = path.resolve(process.env.REGRESSION_RESULTS_FILE || "regression/results.json");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  return outPath;
}

function testResultsProcessor(results) {
  const report = buildModuleReport(results);
  writeReport(report);
  results.regression = report;
  results.success = Boolean(results.success && report.pass);
  return results;
}

testResultsProcessor.buildModuleReport = buildModuleReport;
testResultsProcessor.writeReport = writeReport;

module.exports = testResultsProcessor;
