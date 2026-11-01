import books from './__fixtures__/libraryCatalogue.public.json';
import metadata from '../data/libraryDiscoveryMetadata.json';
import { selectLibraryBooks, availabilityOfBook, languageOfBook } from './libraryCatalog';
import { libraryFiltersFromSearch, listeningFilterFromSearch } from './libraryFilterState';
import { PUBLIC_NAV_ITEMS, isPublicNavItemActive } from '../config/publicNavigation';

// Public metadata snapshot exercises discovery only, never playback or billing.
const audio = new Set(['the-open-window', 'the-selfish-giant']);
const languages = ['all', 'bn', 'en'];
const forms = ['all', 'novel', 'short-story', 'poetry', 'nonfiction'];
const statuses = ['all', 'available', 'hidden'];
const genres = ['all', ...new Set(Object.values(metadata).flatMap(m => m.genres))];
const sorts = ['recently-approved', 'title', 'author', 'short-reads'];
const slugs = rows => rows.map(b => b.slug).sort();

test('all 2160 valid facet/sort combinations match independent metadata set intersections', () => {
  expect(books).toHaveLength(52);
  expect(genres).toHaveLength(12);
  let cases = 0;
  const ids = Object.keys(metadata);
  const languageSets = Object.fromEntries(languages.map(value => [value, new Set(ids.filter(id => value === 'all' || metadata[id].language === value))]));
  const formSets = Object.fromEntries(forms.map(value => [value, new Set(ids.filter(id => value === 'all' || metadata[id].form === value))]));
  const genreSets = Object.fromEntries(genres.map(value => [value, new Set(ids.filter(id => value === 'all' || metadata[id].genres.includes(value)))]));
  for (const language of languages) for (const reading of forms) for (const listening of statuses) for (const genre of genres) {
    const expected = ids.filter(id => languageSets[language].has(id) && formSets[reading].has(id) && genreSets[genre].has(id)
      && (listening === 'all' || (listening === 'available' ? audio.has(id) : !audio.has(id)))).sort();
    for (const sort of sorts) {
      const actual = selectLibraryBooks(books, { language, reading, listening, genre, sort });
      expect(slugs(actual)).toEqual(expected);
      expect(new Set(actual.map(b => b.slug)).size).toBe(actual.length);
      cases += 1;
    }
  }
  expect(cases).toBe(2160);
});

test('specific historical classification errors are repaired without source mutation', () => {
  const before = JSON.stringify(books);
  expect(selectLibraryBooks(books, { reading:'nonfiction' })).toHaveLength(6);
  expect(selectLibraryBooks(books, { language:'bn' })).toHaveLength(9);
  expect(selectLibraryBooks(books, { reading:'novel' }).map(b=>b.slug)).toContain('the-call-of-the-wild');
  expect(selectLibraryBooks(books, { reading:'short-story', genre:'mystery' }).map(b=>b.slug)).toContain('the-adventures-of-sherlock-holmes');
  expect(selectLibraryBooks(books, { genre:'gothic-fiction' }).map(b=>b.slug)).not.toContain('a-scandal-in-bohemia');
  expect(JSON.stringify(books)).toBe(before);
});

test.each(['Oscar Wilde', 'ক্ষু', '(', '.*', 'no such title'])('search is a literal intersection for %s', query => {
  const expected = books.filter(b => `${b.title || ''} ${b.title_en || ''} ${b.author || ''} ${b.short_description || ''}`.normalize('NFC').toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  expect(slugs(selectLibraryBooks(books,{query}))).toEqual(slugs(expected));
});

test('unknown genres produce no results; unsupported enum values normalize predictably', () => {
  expect(selectLibraryBooks(books,{genre:'not-an-existing-genre'})).toEqual([]);
  expect(libraryFiltersFromSearch(new URLSearchParams('language=oops&reading=oops&listening=oops&sort=oops')))
    .toMatchObject({language:'all',reading:'all',listening:'all',sort:'recently-approved'});
});

test('legacy URLs keep their meaning and explicit status wins consistently', () => {
  expect(libraryFiltersFromSearch(new URLSearchParams('category=gothic-fiction'))).toMatchObject({reading:'all',genre:'gothic-fiction'});
  expect(libraryFiltersFromSearch(new URLSearchParams('category=short-story'))).toMatchObject({reading:'short-story',genre:'all'});
  expect(listeningFilterFromSearch(new URLSearchParams('availability=reader-ready'))).toBe('hidden');
  const params = new URLSearchParams('availability=approved-audiobook&listening=all&language=bn');
  expect(listeningFilterFromSearch(params)).toBe('all');
  expect(isPublicNavItemActive(PUBLIC_NAV_ITEMS.find(x=>x.key==='bengali'),{pathname:'/library',search:`?${params}`})).toBe(true);
  expect(PUBLIC_NAV_ITEMS.find(x=>x.key==='bengali').to).toBe('/library?language=bn');
  expect(isPublicNavItemActive(PUBLIC_NAV_ITEMS.find(x=>x.key==='audiobooks'),{pathname:'/library',search:'?language=bn&listening=available'})).toBe(true);
});

test('forged or held audio-shaped metadata never becomes public audio discovery', () => {
  const reader = books.find(b=>b.slug==='frankenstein');
  const approvedAudio = books.find(b=>b.slug==='the-selfish-giant');
  const forged = {...reader, audio_enabled:true,audiobook_enabled:true,audio_qa_status:'QA_PASSED',audiobook_release_gate:'APPROVED',audiobook_delivery_mode:'PROTECTED_PACKAGE_V2',audiobook_package_version:`sha256-${'a'.repeat(64)}`};
  expect(availabilityOfBook(forged)).toBe('reader-ready');
  expect(selectLibraryBooks([forged],{listening:'available'})).toEqual([]);
  expect(selectLibraryBooks([{...approvedAudio,reader_enabled:false}],{listening:'available'})).toEqual([]);
  expect(selectLibraryBooks([{...approvedAudio,audiobook_package_version:'invalid'}],{listening:'available'})).toEqual([]);
});


test('short-read sorting compares consistent minute estimates and puts unknown lengths last', () => {
  const rows = [
    {slug:'hour',estimated_reading_time:'1 hour'},
    {slug:'unknown'}, {slug:'words',word_count:6000},
    {slug:'minutes',estimated_reading_time:'5 min'},
  ];
  expect(selectLibraryBooks(rows,{sort:'short-reads'}).map(b=>b.slug)).toEqual(['minutes','words','hour','unknown']);
});

test('malformed language prefixes cannot override exact accepted discovery language', () => {
  expect(languageOfBook({slug:'the-open-window',language:'benefit'})).toBe('en');
  expect(languageOfBook({slug:'radharani',language:'enough'})).toBe('bn');
});
