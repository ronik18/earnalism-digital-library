import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('./profile_reader_branch.mjs',import.meta.url),'utf8');
test('Reader profiler waits without allocating persistent element handles',()=>{assert.doesNotMatch(source,/page\.waitForSelector\(/);assert.match(source,/page\.locator\('\[data-testid="reader-reading-text"\]'\)\.waitFor/);assert.match(source,/page\.locator\('\[data-pagination-ready="true"\]'\)\.waitFor/)});
test('Profiler closes browser contexts and server',()=>{assert.match(source,/await context\.close\(\)/);assert.match(source,/finally \{await browser\.close\(\)/);assert.match(source,/server\.close\(resolve\)/)});
