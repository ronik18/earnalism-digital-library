#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const root = process.cwd();
const runner = path.join(root, "scripts/run_seamless_brand_article_stability_gate.mjs");
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "article-stability-gate-test-"));
const fixture = path.join(temp, "fixture.json");
const stub = path.join(temp, "capture-stub.mjs");
const manifest = path.join(temp, "manifest.json");
const inventory = path.join(temp, "inventory.json");
fs.writeFileSync(manifest, "{}\n"); fs.writeFileSync(inventory, "{}\n"); fs.writeFileSync(fixture, JSON.stringify({}));
fs.writeFileSync(stub, `import fs from 'node:fs'; import path from 'node:path'; const args=process.argv.slice(2); const get=(key)=>args[args.indexOf(key)+1]; const out=get('--output'), browser=get('--browser'); const config=JSON.parse(fs.readFileSync(process.env.ARTICLE_GATE_FIXTURE,'utf8')); if(config.processNonzero) process.exit(9); fs.mkdirSync(path.join(out,'states',config.wrongState ? 'wrong-state':'article-mobile'),{recursive:true}); if(!config.missingSummary) fs.writeFileSync(path.join(out,'capture-summary.json'),JSON.stringify({expected_state_count:config.expected ?? 1,captured_state_count:config.captured ?? 1,stable_state_count:config.stable ?? 1,production_surface_sha256:'synthetic-production'})); if(!config.missingMetadata) fs.writeFileSync(path.join(out,'states',config.wrongState ? 'wrong-state':'article-mobile','metadata.json'),JSON.stringify({state_id:config.wrongState ? 'wrong-state':'article-mobile',browser_version:browser+' synthetic',visual_quiescence:{result:config.quiescence ?? 'PASS'},console_error_count:config.console ?? 0,page_error_count:config.page ?? 0,failed_required_request_count:config.requests ?? 0,stability_attempts:config.unstable ? [{stable:false}] : [{stable:true}]}));`);
let cases = 0;
function test(name, callback) { callback(); cases += 1; console.log(`PASS ${cases}: ${name}`); }
function invoke(config = {}, extra = []) { fs.writeFileSync(fixture, JSON.stringify(config)); const output=path.join(temp, `out-${cases}`); return spawnSync(process.execPath, [runner, '--base-url','http://127.0.0.1:1','--output',output,'--manifest',manifest,'--route-inventory',inventory,'--capture-script',stub,'--state-id','article-mobile','--webkit-runs','10','--chromium-runs','5','--firefox-runs','5',...extra], {cwd:root,encoding:'utf8',env:{...process.env,ARTICLE_GATE_FIXTURE:fixture}}); }
function fails(config, expression) { const result=invoke(config); assert.notEqual(result.status,0); assert.match(`${result.stderr}${result.stdout}`,expression); }
test('valid 10/5/5 aggregate passes',()=>assert.equal(invoke().status,0));
test('capture process non-zero fails',()=>fails({processNonzero:true},/capture process failed/));
test('missing summary fails',()=>fails({missingSummary:true},/Missing capture summary/));
test('missing metadata fails',()=>fails({missingMetadata:true},/Missing state metadata/));
test('expected count not 1 fails',()=>fails({expected:0},/count must be 1\/1\/1/));
test('captured count not 1 fails',()=>fails({captured:0},/count must be 1\/1\/1/));
test('stable count not 1 fails',()=>fails({stable:0},/count must be 1\/1\/1/));
test('visual quiescence failure fails',()=>fails({quiescence:'FAIL'},/visual quiescence/));
test('console error fails',()=>fails({console:1},/console_error_count/));
test('page error fails',()=>fails({page:1},/page_error_count/));
test('required-request failure fails',()=>fails({requests:1},/failed_required_request_count/));
test('one unstable attempt fails',()=>fails({unstable:true},/paired screenshot attempts/));
test('wrong state ID fails',()=>fails({wrongState:true},/Missing state metadata/));
test('missing browser run fails',()=>{ const result=invoke({},['--firefox-runs','0']); assert.notEqual(result.status,0); assert.match(result.stderr,/positive integer/); });
test('duplicate run directory fails',()=>{ const output=path.join(temp,'duplicate-run'); fs.mkdirSync(path.join(output,'webkit','run-1'),{recursive:true}); fs.writeFileSync(fixture,'{}'); const result=spawnSync(process.execPath,[runner,'--base-url','http://127.0.0.1:1','--output',output,'--manifest',manifest,'--route-inventory',inventory,'--capture-script',stub,'--state-id','article-mobile'],{cwd:root,encoding:'utf8',env:{...process.env,ARTICLE_GATE_FIXTURE:fixture}}); assert.notEqual(result.status,0); assert.match(result.stderr,/Duplicate Article stability run directory/); });
test('output path traversal is rejected',()=>{ fs.writeFileSync(fixture,'{}'); const result=spawnSync(process.execPath,[runner,'--base-url','http://127.0.0.1:1','--output','../escape','--manifest',manifest,'--route-inventory',inventory,'--capture-script',stub,'--state-id','article-mobile'],{cwd:root,encoding:'utf8',env:{...process.env,ARTICLE_GATE_FIXTURE:fixture}}); assert.notEqual(result.status,0); assert.match(result.stderr,/path traversal/); });
test('result JSON records all browser counts',()=>{ const output=path.join(temp,'counts'); fs.writeFileSync(fixture,'{}'); const r=spawnSync(process.execPath,[runner,'--base-url','http://127.0.0.1:1','--output',output,'--manifest',manifest,'--route-inventory',inventory,'--capture-script',stub,'--state-id','article-mobile'],{cwd:root,encoding:'utf8',env:{...process.env,ARTICLE_GATE_FIXTURE:fixture}}); assert.equal(r.status,0,r.stderr); const payload=JSON.parse(fs.readFileSync(path.join(output,'article-stability-results.json'))); assert.deepEqual([payload.article_mobile.webkit.captured,payload.article_mobile.chromium.captured,payload.article_mobile.firefox.captured],[10,5,5]); });
test('current PR head is recorded',()=>{ const payload=JSON.parse(fs.readFileSync(path.join(temp,'counts','article-stability-results.json'))); assert.match(payload.exact_pr_head,/^[0-9a-f]{40}$/); });
test('child process is executed without a shell',()=>assert.match(fs.readFileSync(runner,'utf8'),/shell: false/));
test('complete synthetic result passes schema validation',()=>{ const payload=JSON.parse(fs.readFileSync(path.join(temp,'counts','article-stability-results.json'))); assert.equal(payload.result,'PASS'); assert.equal(payload.article_mobile.webkit.stable,10); });
test('wrong state argument is rejected',()=>{ fs.writeFileSync(fixture,'{}'); const result=spawnSync(process.execPath,[runner,'--base-url','http://127.0.0.1:1','--output',path.join(temp,'bad-state'),'--manifest',manifest,'--route-inventory',inventory,'--capture-script',stub,'--state-id','home-mobile'],{cwd:root,encoding:'utf8',env:{...process.env,ARTICLE_GATE_FIXTURE:fixture}}); assert.notEqual(result.status,0); assert.match(result.stderr,/must be article-mobile/); });
console.log(JSON.stringify({result:'PASS',testCaseCount:cases,temp}));
