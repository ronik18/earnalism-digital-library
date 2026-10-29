import test from 'node:test';
import assert from 'node:assert/strict';
import { canonicalCover, classifyRecoveryFailures, collectDecodedRecoveryCovers } from './lib/recovery_image_evidence.mjs';
const asset = 'v1788115329/earnalism/covers/front/known.png';
const base = 'https://res.cloudinary.com/dzlrhlfpu/image/upload/';
const old = base + 'f_auto,w_240/' + asset, current = base + 'f_auto,w_480/' + asset;
const failure = { url: old, error: 'net::ERR_ABORTED', resourceType: 'image' };
const proof = { currentSrc: current, visible: true, complete: true, naturalWidth: 480, decoded: true };
const classify = (f = failure, p = proof, allowed = [asset]) => classifyRecoveryFailures([f], [p], allowed);
test('same canonical responsive asset with actual decoded replacement qualifies', () => {
 assert.equal(canonicalCover(old), asset);
 assert.equal(classify().superseded.length, 1);
 assert.deepEqual(classify().fatal, []);
});
for (const [name, changes] of Object.entries({ hidden: {visible:false}, incomplete:{complete:false}, broken:{naturalWidth:0}, undecoded:{decoded:false}, sameRequest:{currentSrc:old}, wrongAsset:{currentSrc:base+'v1/earnalism/covers/front/other.png'} })) {
 test(name+' remains fatal', () => assert.equal(classify(failure, {...proof,...changes}).fatal.length, 1));
}
test('non-image and other network failures remain fatal', () => {
 assert.equal(classify({...failure,resourceType:'fetch'}).fatal.length,1);
 assert.equal(classify({...failure,error:'net::ERR_CONNECTION_RESET'}).fatal.length,1);
});
test('unapproved asset and foreign host remain fatal', () => {
 assert.equal(classify(failure,proof,[]).fatal.length,1);
 assert.equal(canonicalCover(old.replace('res.cloudinary.com','evil.example')),null);
 assert.equal(canonicalCover(old.replace('/dzlrhlfpu/','/other/')),null);
});
test('failure arriving during screenshot is included in final classification', async () => {
 const failures = [failure];
 const screenshot = async () => failures.push({url:'https://example.invalid/app.js', error:'net::ERR_ABORTED',resourceType:'script'});
 await screenshot();
 assert.equal(classifyRecoveryFailures(failures,[proof],[asset]).fatal.length,1);
});

for (const mutation of ['detach','hide','source']) {
 test('async decode '+mutation+' cannot provide current replacement proof', async () => {
  globalThis.getComputedStyle = image => ({visibility:image.hidden?'hidden':'visible'});
  const image = {isConnected:true, currentSrc:current, complete:true,naturalWidth:480,
   getBoundingClientRect:()=>({width:100,height:150}),
   async decode() { if(mutation==='detach') this.isConnected=false; if(mutation==='hide') this.hidden=true; if(mutation==='source') this.currentSrc=old; }
  };
  const images=await collectDecodedRecoveryCovers([image]);
  assert.equal(classifyRecoveryFailures([failure],images,[asset]).fatal.length,1);
 });
}
