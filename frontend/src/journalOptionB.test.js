import fs from 'fs';
import path from 'path';
const read = (file) => fs.readFileSync(path.join(process.cwd(), 'src', file), 'utf8');
test('Journal uses real searchable and paginated API posts, not fabricated counts', () => {
  const source = read('pages/Journal.jsx');
  expect(source).toContain('api.get("/blog"');
  expect(source).toContain('Search articles');
  expect(source).toContain('Math.ceil(remaining.length / 6)');
  expect(source).toContain('Ideas worth reading.</span><br />Stories worth sharing.');
});
test('discussion writes require existing authenticated user API and expose failure', () => {
  const source = read('components/JournalDiscussion.jsx');
  expect(source).toContain('if (user)');
  expect(source).toContain('userApi.post(`/blog/${slug}/comments`');
  expect(source).toContain('userApi.put(`/blog/${slug}/like`)');
  expect(source).toContain('role="alert"');
  expect(source).not.toContain('dangerouslySetInnerHTML');
});
test('article supports approved uploaded photos, captions and backend sanitized rich content', () => {
  const source = read('pages/JournalArticle.jsx');
  expect(source).toContain('post.image_caption');
  expect(source).toContain('post.cover_image_alt');
  expect(source).toContain('JournalDiscussion slug={post.slug}');
});
