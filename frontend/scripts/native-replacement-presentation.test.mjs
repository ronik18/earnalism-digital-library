// Actual adapter and release-safety modules, loaded without a bundler; no UI/live claim.
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const url=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');
const chapter=url(readFileSync(resolve(root,'src/lib/chapterIndex.js'),'utf8'));
const controlled=url(readFileSync(resolve(root,'src/lib/controlledLaunch.js'),'utf8').replace("'./chapterIndex'",JSON.stringify(chapter)));
const safety=url(readFileSync(resolve(root,'src/lib/audioReleaseSafety.js'),'utf8').replace('"./controlledLaunch"',JSON.stringify(controlled)));
const adapter=readFileSync(resolve(root,'src/experiences-v2/shared/ReleaseTruthAdapter.js'),'utf8').replace('"../../lib/audioReleaseSafety"',JSON.stringify(safety));
const {listenerReleasePresentation}=await import(url(adapter));
const old='sha256-'+'a'.repeat(64),fresh='sha256-'+'b'.repeat(64);
const book={slug:'the-selfish-giant',title:'The Selfish Giant',author:'Oscar Wilde',
  _readerManifest:{access:{authenticated:true,role:'user'},audio:{enabled:true,delivery_mode:'PROTECTED_PACKAGE_V2',
    asset_slug:'the-selfish-giant',version:'prior-edition',package_version:old,release_gate:'APPROVED',qa_status:'QA_PASSED',duration_ms:777000}}};
let result=listenerReleasePresentation(book);
assert.equal(result.release.status,'approved');assert.notEqual(result.release.status,'private_member_review');
const privateBook=structuredClone(book);
privateBook._readerManifest.audio.transport_canary={enabled:true,slug:book.slug,scope:'native_replacement_authorized_member_only',
  package_version:fresh,release_descriptor_sha256:'c'.repeat(64),duration_ms:541807};
result=listenerReleasePresentation(privateBook);
assert.equal(result.release.status,'private_member_review');assert.equal(result.packageVersion,fresh);assert.equal(result.durationSeconds,541.807);
assert.equal(result.mediaUrl,'');assert.equal(result.packageManifestUrl,'');
for (const mutation of ['guest','wrong-title','percentage','bad-version']) {
  const malformed=structuredClone(privateBook);
  if (mutation==='guest')malformed._readerManifest.access.authenticated=false;
  if (mutation==='wrong-title')malformed._readerManifest.audio.transport_canary.slug='other-book';
  if (mutation==='percentage')malformed._readerManifest.audio.transport_canary.rollout_percentage=5;
  if (mutation==='bad-version')malformed._readerManifest.audio.transport_canary.package_version='invalid';
  assert.notEqual(listenerReleasePresentation(malformed).release.status,'private_member_review');
}
const legacy=structuredClone(privateBook);legacy._readerManifest.audio.transport_canary.scope='transport_canary_only_no_customer_discovery';legacy._readerManifest.audio.transport_canary.rollout_percentage=5;
assert.equal(listenerReleasePresentation(legacy).release.status,'transport_canary');
console.log('7 actual adapter contract cases passed; customer browser rendering remains unverified');
