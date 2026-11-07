import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';

// Optional isolated exact-lockfile runtime. Never alter the existing installation.
export async function loadRenderLibraries(base) {
  const runtimeRoot=path.resolve(process.env.EARNALISM_REMOTION_RUNTIME||base);
  const authority=JSON.parse(fs.readFileSync(path.join(base,'package.json'),'utf8'));
  const require=createRequire(path.join(runtimeRoot,'package.json'));
  const versions={};
  for(const name of ['remotion','@remotion/bundler','@remotion/renderer','react','react-dom']){
    const actual=require(name+'/package.json').version;
    if(actual!==authority.dependencies[name])throw Error('Render runtime differs from pinned project dependency: '+name);
    versions[name]=actual;
  }
  console.log('Loading pinned renderer '+versions.remotion+' from '+runtimeRoot);
  const metadata=require('@remotion/renderer/package.json');
  const entry=path.resolve(path.dirname(require.resolve('@remotion/renderer/package.json')),metadata.exports['.'].import);
  const renderer=await import(pathToFileURL(entry).href);
  console.log('Loading pinned public CommonJS bundler');
  const {bundle}=require('@remotion/bundler');
  return {...renderer,bundle,runtimeRoot,versions};
}
