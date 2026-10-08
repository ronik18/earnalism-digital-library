import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';

const root = path.resolve(process.argv[2] || 'frontend/build');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'asset-manifest.json'), 'utf8'));
const main = fs.readFileSync(path.join(root, manifest.files['main.js'].replace(/^\//, '')));
const gzipBytes = gzipSync(main).length;
assert.ok(gzipBytes <= 165_000, `Initial main JS ${gzipBytes} gzip bytes exceeds 165000 budget`);
for (const file of fs.readdirSync(path.join(root, 'static/js')).filter(f => f.endsWith('.js'))) {
  const bytes = gzipSync(fs.readFileSync(path.join(root, 'static/js', file))).length;
  assert.ok(bytes <= 170_000, `${file}: ${bytes} gzip bytes exceeds 170000 chunk budget`);
}
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert.ok(!/<link[^>]+(?:premium-library-reference-exact|premium-library-mobile-cinematic)/.test(html), 'Retired hero art must not be globally preloaded');
const media = path.join(root, 'static/media');
const fontBytes = fs.readdirSync(media).filter(file => /^(?:cormorant-garamond|eb-garamond|outfit).*\.woff2$/.test(file))
  .reduce((total, file) => total + fs.statSync(path.join(media, file)).size, 0);
assert.ok(fontBytes > 0 && fontBytes <= 1_000_000, `Lossless Latin font derivatives ${fontBytes} bytes exceed 1000000 budget or are absent`);
console.log(JSON.stringify({ status: 'PASS', main_gzip_bytes: gzipBytes, maximum_main_gzip_bytes: 165000, maximum_chunk_gzip_bytes: 170000 }));
