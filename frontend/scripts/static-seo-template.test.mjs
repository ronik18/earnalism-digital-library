import test from 'node:test';
import assert from 'node:assert/strict';
import { cleanStaticSeoTemplate } from './static-seo-template.mjs';
test('rerun does not carry Home fallback into held routes',()=>{const body='<main class="static-seo-snapshot" data-static-seo-snapshot="true"><h1>Home</h1><div>Released preview</div></main>';const source=`<head><script src="app.js"></script></head><noscript>${body}</noscript><div id="root">${body}</div>`;const actual=cleanStaticSeoTemplate(source);assert.equal(actual,'<head><script src="app.js"></script></head><noscript></noscript><div id="root"></div>');assert.equal(cleanStaticSeoTemplate(actual),actual);});
test('ordinary app main and assets remain intact',()=>{const source='<div id="root"><main id="reader">Runtime</main></div><script src="app.js"></script>';assert.equal(cleanStaticSeoTemplate(source),source);});
