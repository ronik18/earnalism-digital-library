import { canonicalShareUrl } from './socialSharing';
test('shares the public canonical article without query credentials, UTM or fragment', () => {
  expect(canonicalShareUrl('https://www.theearnalism.com/journal/quiet-reading?token=private&utm_source=social#comments')).toBe('https://theearnalism.com/journal/quiet-reading');
});
test('retains the actual title route and encodes Bengali route identity', () => {
  expect(canonicalShareUrl('https://theearnalism.com/book/radharani?visual-fixture=1')).toBe('https://theearnalism.com/book/radharani');
  expect(canonicalShareUrl('javascript:alert(1)')).toBe('');
});
