import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const buildDir = path.join(frontendDir, "build");
const snapshots = [
  {
    route: "/",
    file: path.join(buildDir, "index.html"),
    required: ["Read the first 3 pages free. Listening requires an active Reading Pass."],
    forbidden: ["Chapter 1 is free", "Read Chapter 1", "First 3 minutes free", "First 180 seconds free", "Free audiobook preview", "Free listening sample"],
  },
  {
    route: "/book/dracula",
    file: path.join(buildDir, "book", "dracula", "index.html"),
    required: ["first 3 canonical pages", "View Reading Passes", "Read the first 3 pages free. Listening requires an active Reading Pass."],
    forbidden: ["Chapter 1 is free", "Read Chapter 1", "7-Day", "7-day", "First 3 minutes free", "First 180 seconds free", "Free audiobook preview", "Free listening sample"],
  },
  {
    route: "/library",
    file: path.join(buildDir, "library", "index.html"),
    required: ["Read the first 3 pages free. Listening requires an active Reading Pass."],
    forbidden: ["Chapter 1 is free", "Read Chapter 1", "First 3 minutes free", "First 180 seconds free", "Free audiobook preview", "Free listening sample"],
  },
  {
    route: "/pricing",
    file: path.join(buildDir, "pricing", "index.html"),
    required: ["Reading Pass", "No subscription", "Read the first 3 pages free. Listening requires an active Reading Pass."],
    forbidden: ["The First Chapter", "Start with Chapter 1", "7-Day", "7-day", "First 3 minutes free", "First 180 seconds free", "Free audiobook preview", "Free listening sample"],
  },
  {
    route: "/reader/dracula",
    file: path.join(buildDir, "reader", "dracula", "index.html"),
    required: ["Read the first 3 pages free. Listening requires an active Reading Pass."],
    forbidden: ["Read Dracula Chapter 1", "Preview chapter unlocked", "Get 7-Day Reading Pass", "First 3 minutes free", "First 180 seconds free", "Free audiobook preview", "Free listening sample"],
  },
];

let inspected = 0;
let requiredAssertions = 0;
let forbiddenAssertions = 0;
let failures = 0;

for (const snapshot of snapshots) {
  console.log(`Inspecting ${snapshot.route}: ${snapshot.file}`);
  let html;
  try {
    html = await readFile(snapshot.file, "utf8");
  } catch (error) {
    failures += snapshot.required.length + snapshot.forbidden.length + 1;
    console.error(`Missing snapshot ${snapshot.file}: ${error.code || error.message}`);
    continue;
  }
  inspected += 1;
  const normalized = html.toLowerCase();
  for (const phrase of snapshot.required) {
    requiredAssertions += 1;
    if (!normalized.includes(phrase.toLowerCase())) {
      failures += 1;
      console.error(`Missing required phrase for ${snapshot.route}: ${phrase}`);
    }
  }
  for (const phrase of snapshot.forbidden) {
    forbiddenAssertions += 1;
    if (normalized.includes(phrase.toLowerCase())) {
      failures += 1;
      console.error(`Forbidden phrase for ${snapshot.route}: ${phrase}`);
    }
  }
}

console.log(`Static SEO snapshot verifier: inspected=${inspected} required=${requiredAssertions} forbidden=${forbiddenAssertions} failed=${failures}`);
if (failures > 0 || inspected !== snapshots.length) process.exitCode = 1;
