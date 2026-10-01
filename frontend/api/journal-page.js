const fs = require('node:fs/promises');
const path = require('node:path');
const notFound = require('./not-found');
const escape = value => String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

module.exports = async function journalPage(req, res) {
  const slug = String(req.query?.slug || '');
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) return notFound(req, res);
  try {
    const response = await fetch(`https://api.theearnalism.com/api/blog/${encodeURIComponent(slug)}`, {signal: AbortSignal.timeout(8000)});
    if (response.status === 404) return notFound(req, res);
    if (!response.ok) throw new Error('Journal unavailable');
    const post = await response.json();
    if (post.slug !== slug || post.is_published !== true || !post.title) return notFound(req, res);
    // Monorepo functions may execute with the repository as cwd; the bundled
    // application shell is relative to this frontend handler, not that cwd.
    const shell = await fs.readFile(path.join(__dirname, '../build/journal-app-shell.html'), 'utf8');
    const canonical = `https://theearnalism.com/journal/${slug}`;
    const title = `${post.title} — The Earnalism Journal`;
    const description = String(post.excerpt || '').slice(0, 320);
    const image = /^https:\/\//.test(post.cover_image_url || '') ? post.cover_image_url : '';
    const head = `<title>${escape(title)}</title><link rel="canonical" href="${canonical}"><meta name="description" content="${escape(description)}"><meta property="og:type" content="article"><meta property="og:title" content="${escape(title)}"><meta property="og:description" content="${escape(description)}"><meta property="og:url" content="${canonical}"><meta name="twitter:card" content="summary_large_image">${image ? `<meta property="og:image" content="${escape(image)}">` : ''}`;
    const html = shell.replace(/<title>[\s\S]*?<\/title>/gi, '').replace(/<meta\s+[^>]*(?:name|property)=["'](?:description|twitter:[^"']+|og:[^"']+)["'][^>]*>/gi, '').replace(/<link\s+[^>]*rel=["']canonical["'][^>]*>/gi, '').replace('</head>', head + '</head>');
    res.statusCode = 200;
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=60, must-revalidate');
    res.end(html);
  } catch (error) {
    console.error('Journal page temporarily unavailable', { code: error?.code || 'UPSTREAM_OR_RENDER_FAILURE' });
    res.statusCode = 503;
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Robots-Tag', 'noindex');
    res.end('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Journal temporarily unavailable | The Earnalism</title></head><body style="background:#f6e8d7;color:#4b0f1a;font:20px/1.6 Georgia,serif;padding:48px"><main><h1>This article is taking a brief pause.</h1><p>Please try again shortly.</p><a href="/journal">Return to Blog</a></main></body></html>');
  }
};
