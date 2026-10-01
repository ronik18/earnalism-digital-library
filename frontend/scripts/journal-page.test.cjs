const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const handler = require('../api/journal-page');
test('new published article deep links get escaped social metadata and the real app shell', async () => {
  const originalFetch=global.fetch, originalRead=fs.readFile;
  const render = async (slug, response) => {
    global.fetch=async url=>{ assert.equal(url,`https://api.theearnalism.com/api/blog/${slug}`); return response; };
    let body; const headers={}; const res={setHeader:(k,v)=>headers[k]=v,end:s=>body=s};
    await handler({query:{slug}},res); return {status:res.statusCode,body,headers};
  };
  try {
    fs.readFile=async()=>'<html><head><title>Old</title><meta property="og:title" content="Old"></head><body><div id="root"></div><script src="/static/js/main.js"></script></body></html>';
    const result=await render('new-note',{ok:true,status:200,json:async()=>({slug:'new-note',is_published:true,title:'<script>bad</script>',excerpt:'A "quiet" note',cover_image_url:'https://example.com/a.jpg'})});
    assert.equal(result.status,200); assert.match(result.body,/&lt;script&gt;bad/); assert.match(result.body,/og:url/); assert.match(result.body,/theearnalism.com\/journal\/new-note/); assert.match(result.body,/static\/js\/main.js/); assert.doesNotMatch(result.body,/<title>Old/);
    assert.equal((await render('missing',{status:404})).status,404);
    assert.equal((await render('draft',{status:200,ok:true,json:async()=>({slug:'draft',is_published:false,title:'Draft'})})).status,404);
    assert.equal((await render('offline',{status:503,ok:false})).status,503);
    const invalid={setHeader(){},end(){}}; await handler({query:{slug:'../secret'}},invalid); assert.equal(invalid.statusCode,404);
  } finally { global.fetch=originalFetch; fs.readFile=originalRead; }
});
