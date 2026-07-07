#!/usr/bin/env node
import { execFileSync } from "node:child_process";

const branch = process.env.VERCEL_GIT_COMMIT_REF
  || process.env.GITHUB_REF_NAME
  || process.env.BRANCH_NAME
  || "";
const vercelEnv = process.env.VERCEL_ENV || "";
const prId = process.env.VERCEL_GIT_PULL_REQUEST_ID || process.env.GITHUB_REF?.match(/refs\/pull\/(\d+)/)?.[1] || "";
const relevantPrefixes = [
  "frontend/",
  "package.json",
  "package-lock.json",
  "data/controlled_launch.json",
  "backend/data/controlled_launch.json",
  ".github/workflows/",
];

function logAndBuild(reason) {
  console.log(`Vercel build required: ${reason}`);
  process.exit(1);
}

function logAndSkip(reason) {
  console.log(`Vercel build skipped: ${reason}`);
  process.exit(0);
}

function changedFiles() {
  const explicit = process.env.VERCEL_GIT_COMMIT_REF_CHANGED_FILES
    || process.env.EARNALISM_CHANGED_FILES
    || "";
  if (explicit.trim()) {
    return explicit.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean);
  }

  const candidates = [
    ["diff", "--name-only", "HEAD~1", "HEAD"],
    ["diff", "--name-only", "origin/main...HEAD"],
  ];
  for (const args of candidates) {
    try {
      const output = execFileSync("git", args, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
      const files = output.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
      if (files.length) return files;
    } catch {
      // Fall through to fail-safe build.
    }
  }
  return null;
}

if (branch === "main" || vercelEnv === "production") {
  logAndBuild("main/production deployment");
}

if (prId || vercelEnv === "preview" || branch.startsWith("codex/")) {
  const files = changedFiles();
  if (files === null) {
    logAndBuild("preview branch changed-file detection unavailable");
  }
  if (files.some((file) => relevantPrefixes.some((prefix) => file === prefix.replace(/\/$/, "") || file.startsWith(prefix)))) {
    logAndBuild(`preview branch has frontend/config changes (${files.length} file${files.length === 1 ? "" : "s"})`);
  }
  logAndSkip("preview branch contains only non-frontend no-op changes");
}

const files = changedFiles();
if (files === null) {
  logAndBuild("unknown branch changed-file detection unavailable");
}
if (files.some((file) => relevantPrefixes.some((prefix) => file === prefix.replace(/\/$/, "") || file.startsWith(prefix)))) {
  logAndBuild(`frontend/config changes detected (${files.length} file${files.length === 1 ? "" : "s"})`);
}
logAndSkip("no frontend/config changes detected");
