import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('./profile_reader_real_e2e.mjs',import.meta.url),'utf8');
test('Real Reader harness uses native AuthProvider, with no API replacement',()=>{
 assert.match(source,/frontend\/src\/context\/AuthContext.jsx/);
 assert.doesNotMatch(source,/NormalModuleReplacementPlugin|route\.fulfill|fixture-manuscript/);
});
test('Real Reader harness uses Locator waits and closes browser',()=>{
 assert.doesNotMatch(source,/waitForSelector\(/);
 assert.match(source,/finally\{await browser.close\(\)/);
});
test('Fixture entitlement write is constrained to disposable loopback UAT',()=>{
 assert.match(source,/process.env.ENVIRONMENT!=='uat'/);
 assert.match(source,/p.hostname=='127.0.0.1'/);
 assert.match(source,/p.path=='\/earnalism_uat'/);
 assert.match(source,/r.matched_count==1/);
});
test('Protected content negative control fails on disclosure',()=>{
 assert.match(source,/unauthorized.status\(\)===200\)throw Error/);
});
