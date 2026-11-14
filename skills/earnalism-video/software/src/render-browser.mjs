// Resolve an already installed browser. Never downloads or disables its sandbox.
import fs from 'node:fs';
import path from 'node:path';

export function resolveRenderBrowser(env = process.env, platform = process.platform) {
  if (env.EARNALISM_RENDER_BROWSER) {
    const supplied = env.EARNALISM_RENDER_BROWSER;
    if (!path.isAbsolute(supplied)) throw Error('EARNALISM_RENDER_BROWSER must be an absolute installed executable');
    fs.accessSync(supplied, fs.constants.X_OK);
    return supplied;
  }
  const candidates = platform === 'darwin'
    ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    : ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/opt/google/chrome/chrome'];
  for (const candidate of candidates) {
    try { fs.accessSync(candidate, fs.constants.X_OK); return candidate; } catch {}
  }
  throw Error('No installed rendering browser; provision the qualified Linux browser or set EARNALISM_RENDER_BROWSER before rendering');
}

export function resolveRenderPublic(base, env = process.env) {
  const selected = env.EARNALISM_RENDER_PUBLIC || path.join(base, 'refraction/public');
  if (!path.isAbsolute(selected) || !fs.statSync(selected).isDirectory()) throw Error('Bound rendering public-assets directory is missing');
  return selected;
}
