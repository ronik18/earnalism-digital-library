import { authorizedBookPlans, measuredChapterEntry, bookPageDomain } from './authorizedBookMap';
import { chapterWindowPlan } from './authorizedChapter';

const manifest = { canonical_pages: { page_count: 4, preview_policy: { public_limit: 2 }, pages: [1,2,3,4].map(index => ({ page_number: index, page_id: `p${index}`, chapter_id: index <= 2 ? 'a' : 'b', content_hash: String(index).repeat(64) })) }, chapters: [{ id: 'a', title: 'One' }, { id: 'b', title: 'Two' }] };
const entry = (plan, count) => ({ key: plan.key, chapterId: plan.chapterId, boundaries: Array.from({ length: count }, (_, index) => ({ start: index * 10, end: (index + 1) * 10, anchor: { page: plan.first, offset: index * 10, revision: 'hash' } })) });

test('preview metadata creates no plan for unauthorized chapters', () => {
  const plans = authorizedBookPlans(manifest, false, chapterWindowPlan);
  expect(plans.map(plan => plan.rows.map(row => row.page_number))).toEqual([[1,2]]);
});
test('full access preserves canonical chapter order and chunk membership', () => {
  const plans = authorizedBookPlans(manifest, true, chapterWindowPlan);
  expect(plans.map(plan => plan.chapterId)).toEqual(['a','b']);
  expect(plans[1].rows.map(row => row.page_number)).toEqual([3,4]);
});
test('unmapped prefix never fabricates a global number or final total', () => {
  const plans = authorizedBookPlans(manifest, true, chapterWindowPlan);
  const result = bookPageDomain(plans, { [plans[1].key]: entry(plans[1], 3) }, plans[1].key, 1);
  expect(result.currentNumber).toBeNull(); expect(result.total).toBeNull();
  expect(result.options.every(option => option.number === null)).toBe(true);
});
test('complete domain produces one numbering and selector across chapters', () => {
  const plans = authorizedBookPlans(manifest, true, chapterWindowPlan);
  const entries = Object.fromEntries(plans.map((plan,index) => [plan.key, entry(plan,index+2)]));
  const result = bookPageDomain(plans, entries, plans[1].key, 1);
  expect(result.total).toBe(5); expect(result.currentNumber).toBe(4);
  expect(result.options.map(option => option.number)).toEqual([1,2,3,4,5]);
  expect(result.options[2].anchor.page).toBe(3);
});
test('grants with changed revision or preview scope cannot match leased plans', () => {
  const full = authorizedBookPlans(manifest, true, chapterWindowPlan);
  const preview = authorizedBookPlans(manifest, false, chapterWindowPlan);
  const entries = { [full[0].key]: entry(full[0],2) };
  expect(bookPageDomain(preview, entries, preview[0].key,0).total).toBeNull();
  const changed = JSON.parse(JSON.stringify(manifest)); changed.canonical_pages.pages[0].content_hash = 'f'.repeat(64);
  const revised = authorizedBookPlans(changed,true,chapterWindowPlan);
  expect(bookPageDomain(revised,entries,revised[0].key,0).currentNumber).toBeNull();
});
test.each([
  [{start:0,end:10},{start:11,end:20}],
  [{start:0,end:10},{start:9,end:20}],
  [{start:0,end:10}],
])('source gaps, overlaps and incomplete reconstruction are rejected', pages => {
  expect(() => measuredChapterEntry({ plan: {key:'a',chapterId:'a'},textLength:20 },pages,offset => ({offset}))).toThrow();
});
test('a measured map retains only stable anchors and contiguous boundaries', () => {
  const result = measuredChapterEntry({plan:{key:'a',chapterId:'a'},textLength:20},[{start:0,end:10,html:'secret',text:'secret'},{start:10,end:20}],offset => ({page:1,offset,revision:'hash'}));
  expect(result.boundaries.map(row => row.anchor.offset)).toEqual([0,10]);
  expect(JSON.stringify(result)).not.toContain('secret');
});
