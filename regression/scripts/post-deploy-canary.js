#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { request, getJson } = require("../utils/http");
const { frontendUrl, apiOrigin, apiUrl } = require("../utils/envGuard");
const reportUtils = require("../utils/report");

function moduleRow(moduleName, checks) {
  const failed = checks.filter((check) => check.status === "failed");
  const skipped = checks.filter((check) => check.status === "skipped");
  const passed = checks.filter((check) => check.status === "passed");
  return {
    moduleName,
    totalChecks: checks.length,
    passedChecks: passed.length,
    failedChecks: failed.length,
    skippedChecks: skipped.length,
    score: checks.length ? Math.round((passed.length / checks.length) * 10000) / 100 : 0,
    mandatory: true,
    failures: [...failed, ...skipped],
    artifacts: [],
  };
}

async function check(name, fn) {
  try {
    await fn();
    return { title: name, status: "passed", failureMessages: [] };
  } catch (error) {
    return { title: name, status: "failed", failureMessages: [error.message] };
  }
}

async function main() {
  process.env.REGRESSION_MODE = "canary";
  const checks = [];
  checks.push(await check("frontend homepage is reachable", async () => {
    const response = await request(frontendUrl(), { skipBody: true });
    if (!response.ok) throw new Error(`frontend status=${response.status}`);
  }));
  checks.push(await check("backend healthz is ok", async () => {
    const response = await request(`${apiOrigin()}/healthz`);
    if (!response.ok || !/ok/i.test(response.text)) throw new Error(`healthz status=${response.status}`);
  }));
  checks.push(await check("public books API returns books", async () => {
    const response = await getJson(`${apiUrl()}/books`);
    if (!response.ok || !Array.isArray(response.data) || response.data.length === 0) throw new Error("books API empty or unavailable");
  }));
  checks.push(await check("admin API still requires auth", async () => {
    const response = await request(`${apiUrl()}/admin/books`, { skipBody: true });
    if (![401, 403].includes(response.status)) throw new Error(`admin API status=${response.status}`);
  }));

  const report = {
    regressionRunId: process.env.REGRESSION_RUN_ID || `canary-${Date.now()}`,
    mode: "canary",
    generatedAt: new Date().toISOString(),
    modules: [moduleRow("Post-deploy Canary", checks)],
  };
  report.pass = report.modules.every((module) => module.score === 100);
  report.mandatoryFailures = report.modules.filter((module) => module.score !== 100).map((module) => module.moduleName);
  report.summary = {
    totalModules: report.modules.length,
    passedModules: report.modules.filter((module) => module.score === 100).length,
    failedMandatoryModules: report.mandatoryFailures.length,
  };

  fs.mkdirSync(path.resolve("regression"), { recursive: true });
  reportUtils.writeReport(report);
  if (!report.pass) {
    console.error("Canary failed. Roll back the last deployment and inspect regression/results.json.");
    process.exit(1);
  }
  console.log("Canary passed.");
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
