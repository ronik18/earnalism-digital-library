import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,copyFileSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
for(const mode of ['enabled','disabled','missing','string-true','held','invalid']) test(`actual SEO generator and verifier preserve access truth: ${mode}`,()=>{
 const temporary=mkdtempSync(path.join(tmpdir(),'earnalism-seo-access-'));
 try {
  const paths=['frontend/scripts/generate-static-seo-snapshots.mjs','frontend/scripts/verify-static-seo-snapshots.mjs','frontend/scripts/static-seo-template.mjs','frontend/scripts/unavailable-title-routes.mjs','frontend/src/content/productCopy.json','frontend/src/content/legalPolicies.json','frontend/public/index.html','frontend/static-seo/controlled-publication-public.json','frontend/static-seo/editorial-public.json','data/controlled_launch.json'];
  for(const file of paths){mkdirSync(path.dirname(path.join(temporary,file)),{recursive:true});copyFileSync(path.join(root,file),path.join(temporary,file));}
  const launchPath=path.join(temporary,'data/controlled_launch.json'); const launch=JSON.parse(readFileSync(launchPath));
  launch.public_paid_commerce_enabled=mode==='enabled'; if(mode==='missing')delete launch.public_paid_commerce_enabled;if(mode==='string-true')launch.public_paid_commerce_enabled='true';
  const contractPath=path.join(temporary,'frontend/static-seo/controlled-publication-public.json'); const contract=JSON.parse(readFileSync(contractPath));
  if(mode==='held'){contract.public_release_held=true;contract.publications=[];launch.live_approved_slugs=[];}
  if(mode==='invalid')contract.schema_version='invalid';
  writeFileSync(launchPath,JSON.stringify(launch));writeFileSync(contractPath,JSON.stringify(contract));
  const run=file=>spawnSync(process.execPath,[path.join(temporary,'frontend/scripts',file)],{encoding:'utf8'});
  const generated=run('generate-static-seo-snapshots.mjs');
  if(mode==='invalid'){assert.notEqual(generated.status,0);return;}
  assert.equal(generated.status,0,generated.stderr);const verified=run('verify-static-seo-snapshots.mjs');assert.equal(verified.status,0,verified.stderr);
  const pricing=readFileSync(path.join(temporary,'frontend/build/pricing/index.html'),'utf8');
  assert.ok(pricing.includes(mode==='held'?'temporarily unavailable':mode==='enabled'?'One-time prepaid Reading Passes':'Reading Pass purchases are not available'));
  const home=readFileSync(path.join(temporary,'frontend/build/index.html'),'utf8');
  if(mode!=='held')assert.ok(home.includes('pass-required editions'));
  assert.ok(!home.includes('"isAccessibleForFree":false'));
 } finally {rmSync(temporary,{recursive:true,force:true});}
});
