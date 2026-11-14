import {resolveRenderBrowser, resolveRenderPublic} from '../src/render-browser.mjs';
import {loadRenderLibraries} from '../src/render-runtime.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const base = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const [propsFile, out, format = 'CondensationLandscape', stillFrame] = process.argv.slice(2);
if (!propsFile || !out) throw Error('Usage: node condensation/render.mjs props.json output CondensationLandscape|CondensationShorts|CondensationCleanShorts|CoverLandscape|CoverShorts [still-frame,...]');
if (fs.existsSync(out)) throw Error('Refusing overwrite ' + out);
const inputProps = JSON.parse(fs.readFileSync(propsFile, 'utf8'));
if (!format.startsWith('Cover')) {
  if (!Array.isArray(inputProps.scenes) || inputProps.scenes.length === 0) throw Error('A nonempty episode timeline is required; no blank narration-integration claim');
  if (!Number.isFinite(inputProps.duration) || inputProps.duration <= 0) throw Error('A positive body duration is required');
  const {sceneKinds} = await import('./layout.mjs');
  let end = 0;
  for (const scene of inputProps.scenes) {
    if (!sceneKinds.includes(scene.scene) || !Number.isFinite(scene.start) || !Number.isFinite(scene.end) || scene.end <= scene.start || Math.abs(scene.start - end) > 1 / 30) throw Error('Invalid or discontinuous scene timeline');
    end = scene.end;
  }
  if (Math.abs(end - inputProps.duration) > .1) throw Error('Body duration does not match scene timeline');
}
const browserExecutable = resolveRenderBrowser();
const {bundle, selectComposition, renderMedia, renderStill, runtimeRoot} = await loadRenderLibraries(base);
// Reuse the exact approved emblem/end-ident files without modifying or recopying them.
const serveUrl = await bundle({entryPoint: path.join(base, 'condensation/index.tsx'), publicDir: resolveRenderPublic(base), rootDir: runtimeRoot});
const composition = await selectComposition({serveUrl, id: format, inputProps, browserExecutable});
fs.mkdirSync(path.dirname(path.resolve(out)), {recursive: true});
if (stillFrame !== undefined) {
  for (const value of stillFrame.split(',')) {
    const frame = Number(value);
    if (!Number.isInteger(frame) || frame < 0 || frame >= composition.durationInFrames) throw Error('Frame outside composition');
    const output = stillFrame.includes(',') ? out.replace(/\.png$/i, '-' + value + '.png') : out;
    if (fs.existsSync(output)) throw Error('Refusing overwrite ' + output);
    await renderStill({serveUrl, composition, inputProps, browserExecutable, output, frame, imageFormat: 'png'});
  }
} else {
  let threshold = .2;
  await renderMedia({serveUrl, composition, inputProps, browserExecutable, outputLocation: out,
    codec: 'h264', pixelFormat: 'yuv420p', colorSpace: 'bt709', crf: 20,
    disableSharedMemoryCapture: true, imageFormat: 'png',
    frameRange: process.env.CONDENSATION_FRAME_RANGE ? JSON.parse(process.env.CONDENSATION_FRAME_RANGE) : undefined,
    concurrency: 4, onProgress: ({progress}) => {
      if (progress >= threshold) {console.log(Math.round(progress * 100) + '%'); threshold += .2;}
    },
  });
  console.log('SILENT ANIMATION ONLY — narration integration is not established by this file.');
}
console.log(out);
