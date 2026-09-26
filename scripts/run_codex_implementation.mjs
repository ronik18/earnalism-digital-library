import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import process from "node:process";
import { Codex } from "@openai/codex-sdk";

const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, all) => {
  if (value.startsWith("--")) pairs.push([value.slice(2), all[index + 1]]);
  return pairs;
}, []));

if (!process.env.EARNALISM_CODEX_OPENAI_API_KEY) throw new Error("executor credential is not configured");
const attempt = Number(args.attempt || 1);
if (![1, 2].includes(attempt)) throw new Error("bounded acceptance fixture allows at most two executions");
const workingDirectory = process.cwd();
const correctionContext = args["correction-context"] || "";
const prompt = attempt === 1
  ? "In the isolated bridge_fixtures/codex_acceptance_fixture.py only, implement the first half of the acceptance brief: change LABEL from pending to ready. Do not change format_label yet; the independent reviewer will require that as the bounded correction. Run only the focused fixture test if useful, and report the file changed. Do not touch any other path."
  : "In the isolated bridge_fixtures/codex_acceptance_fixture.py only, apply the reviewer correction: keep LABEL=ready and make format_label return the uppercase label. Do not touch any other path. Run python3 scripts/codex_fixture_test.py and report the file changed."
  + ` This is a bounded non-production fixture. Make the source edit, do not merely describe it. Reviewer findings from the prior attempt: ${correctionContext.slice(0, 3000)}`;

const started = Date.now();
const codex = new Codex({ apiKey: process.env.EARNALISM_CODEX_OPENAI_API_KEY });
const thread = codex.startThread({
  workingDirectory,
  sandboxMode: "workspace-write",
  approvalPolicy: "never",
  networkAccessEnabled: false,
  model: "gpt-5.6-luna",
  modelReasoningEffort: "low",
});
const turn = await thread.run(prompt);
const diff = execFileSync("git", ["diff", "--name-only", "--", "bridge_fixtures"], { encoding: "utf8" }).trim().split("\n").filter(Boolean);
const result = {
  executor: "openai-codex-sdk",
  task_id: args["task-id"],
  attempt,
  model: "gpt-5.6-luna",
  duration_ms: Date.now() - started,
  files_changed: diff,
  summary: turn.finalResponse,
  usage: turn.usage ?? null,
  budget_ceiling_usd: 2.0,
  execution_count: attempt,
};
writeFileSync(args.output || "codex-result.json", JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify({ ...result, summary: result.summary?.slice(0, 500) }));
