const test = require('node:test');
const assert = require('node:assert/strict');
const proxy = require('../api/[...proxy]');
const { readerRefreshGuidance: guide } = proxy;
const page = '/api/reading-pass/books/test-book/pages/1';
const original = { detail: { code: 'PREVIEW_REQUIRES_PASS', message: 'A Reading Pass is required.', reason: 'oversized' }, request_id: 'dummy-request' };
const bytes = Buffer.from(JSON.stringify(original));
const invoke = (overrides = {}) => guide(overrides.method ?? 'GET', overrides.path ?? page, overrides.status ?? 403, overrides.contentType ?? 'application/json; charset=utf-8', overrides.body ?? bytes);

test('recognized denial preserves every field except appended conditional guidance', () => {
  const result = JSON.parse(invoke());
  assert.match(result.detail.message, /^A Reading Pass is required\. If this tab was open before the Reader update, refresh it once/);
  assert.match(result.detail.message, /Reader's access controls/);
  const copy = structuredClone(result); copy.detail.message = original.detail.message;
  assert.deepEqual(copy, original);
  assert.deepEqual(JSON.parse(bytes), original);
  assert.deepEqual(invoke({ body: invoke() }), invoke(), 'guidance must not be appended twice');
});

for (const [label, overrides] of [
  ['HEAD', {method:'HEAD'}], ['POST', {method:'POST'}], ['success', {status:200}], ['unauthorized', {status:401}], ['territory', {status:451}],
  ['manifest', {path:'/api/reading-pass/books/test-book/manifest'}], ['session', {path:'/api/reading-pass/sessions/start'}], ['audio', {path:'/api/reader/book/test-book/audiobook/manifest'}], ['zero page', {path:'/api/reading-pass/books/test-book/pages/0'}], ['trailing path', {path:page+'/anything'}],
  ['wrong content type', {contentType:'text/html'}], ['unsupported charset', {contentType:'application/json; charset=iso-8859-1'}],
  ['invalid JSON', {body:Buffer.from('{broken')}], ['invalid UTF8', {body:Buffer.from([123,34,120,34,58,34,255,34,125])}], ['oversized error', {body:Buffer.alloc(8193,32)}],
  ['unsafe numeric field', {body:Buffer.from('{"detail":{"code":"PREVIEW_REQUIRES_PASS","message":"denied"},"unrelated_number":9007199254740993}')}],
  ['overflow numeric field', {body:Buffer.from('{"detail":{"code":"PREVIEW_REQUIRES_PASS","message":"denied"},"unrelated_number":1e400}')}],
  ['precise fractional field', {body:Buffer.from('{"detail":{"code":"PREVIEW_REQUIRES_PASS","message":"denied"},"unrelated_number":0.123456789123456789}')}],
  ['ordinary numeric extension', {body:Buffer.from('{"detail":{"code":"PREVIEW_REQUIRES_PASS","message":"denied","count":3}}')}],
  ['array body', {body:Buffer.from('[]')}], ['array detail', {body:Buffer.from('{"detail":[]}')}], ['different code', {body:Buffer.from('{"detail":{"code":"AUTH_REQUIRED","message":"sign in"}}')}],
  ['nonstring message', {body:Buffer.from('{"detail":{"code":"PREVIEW_REQUIRES_PASS","message":null}}')}], ['long message', {body:Buffer.from(JSON.stringify({detail:{code:'PREVIEW_REQUIRES_PASS',message:'x'.repeat(1025)}}))}],
]) {
  test(`unrelated or invalid ${label} passes through exact bytes`, () => {
    const input = overrides.body ?? bytes;
    assert.strictEqual(invoke(overrides), input);
  });
}

test('actual proxy handler keeps denial, cookies and private cache controls without another request', async () => {
  const before = { fetch: global.fetch, secret: process.env.EARNALISM_RELEASE_PROXY_SECRET, env: process.env.VERCEL_ENV };
  process.env.EARNALISM_RELEASE_PROXY_SECRET = 'local-dummy-release-signing-secret-long-enough';
  process.env.VERCEL_ENV = 'production';
  const cookies = ['dummy_session=fixture; HttpOnly; Secure; Path=/', 'dummy_device=fixture; HttpOnly; Secure; Path=/'];
  let calls = 0;
  global.fetch = async (_url, options) => {
    calls++; assert.equal(options.method, 'GET');
    assert.equal(options.headers.get('authorization'), 'Bearer dummy-only');
    assert.match(options.headers.get('x-earnalism-release-signature'), /^[a-f0-9]{64}$/);
    return { status:403, headers:new Headers([['content-type','application/json; charset=utf-8'],...cookies.map(v=>['set-cookie',v])]), arrayBuffer:async()=>bytes };
  };
  try {
    const res = { headers:{}, setHeader(k,v){this.headers[k.toLowerCase()]=v;}, end(body){this.body=body;} };
    await proxy({url:page,method:'GET',headers:{'x-vercel-ip-country':'IN',authorization:'Bearer dummy-only'}},res);
    assert.equal(res.statusCode,403); assert.equal(calls,1);
    assert.deepEqual(res.headers['set-cookie'],cookies);
    for (const name of ['cache-control','cdn-cache-control','vercel-cdn-cache-control']) assert.match(res.headers[name],/no-store/);
    assert.equal(JSON.parse(res.body).detail.code,'PREVIEW_REQUIRES_PASS');
    assert.match(JSON.parse(res.body).detail.message,/refresh it once/);
  } finally {
    global.fetch=before.fetch;
    for (const [name,value] of [['EARNALISM_RELEASE_PROXY_SECRET',before.secret],['VERCEL_ENV',before.env]]) { if(value===undefined) delete process.env[name]; else process.env[name]=value; }
  }
});
