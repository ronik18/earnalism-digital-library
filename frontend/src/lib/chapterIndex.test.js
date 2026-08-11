import {
  CHAPTER_INDEX_CONTRACT_VERSION,
  chapterIndexEntry,
  normalizeChapterDisplayTitle,
  sortedChapterIndex,
} from './chapterIndex';
import fs from 'fs';
import path from 'path';

describe('chapter index contract', () => {
  test('normalizes Dracula continuation titles without duplicate numeral systems', () => {
    expect(normalizeChapterDisplayTitle('CHAPTER II. JONATHAN HARKER’S JOURNAL-- continued'))
      .toBe('Chapter 2. Jonathan Harker’s Journal');
    expect(chapterIndexEntry({ title: 'CHAPTER II. JONATHAN HARKER’S JOURNAL-- continued' }, 2, 27))
      .toMatchObject({
        index_contract: CHAPTER_INDEX_CONTRACT_VERSION,
        index_sequence_label: '02',
        index_secondary_label: 'Chapter 2',
        index_title: 'Jonathan Harker’s Journal',
      });
  });

  test('keeps unsubtitled and Bengali entries meaningful', () => {
    expect(chapterIndexEntry({ title: 'CHAPTER V' }, 5, 27).index_title).toBe('Chapter 5');
    expect(chapterIndexEntry({ title: 'প্রথম পরিচ্ছেদ' }, 1, 4).index_title).toBe('প্রথম পরিচ্ছেদ');
  });

  test('sorts deterministically and uses a stable sequence width', () => {
    const entries = sortedChapterIndex([
      { id: 'b', order: 2, title: 'Chapter II' },
      { id: 'a', order: 1, title: 'Chapter I. Opening' },
    ]);
    expect(entries.map((entry) => entry.id)).toEqual(['a', 'b']);
    expect(entries.map((entry) => entry.index_sequence_label)).toEqual(['01', '02']);
  });

  test('renders every controlled publication through the same deterministic contract', () => {
    const controlledRoot = path.resolve(process.cwd(), '../backend/data/controlled_publications');
    const manifests = fs.readdirSync(controlledRoot)
      .map((slug) => path.join(controlledRoot, slug, 'reader_manifest.json'))
      .filter((manifestPath) => fs.existsSync(manifestPath))
      .sort();
    expect(manifests).toHaveLength(79);

    let auditedChapters = 0;
    manifests.forEach((manifestPath) => {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
      const first = sortedChapterIndex(manifest.chapters || []);
      const second = sortedChapterIndex(manifest.chapters || []);
      expect(first).toEqual(second);
      expect(first).toHaveLength(manifest.chapter_count);
      expect(new Set(first.map((entry) => entry.id)).size).toBe(first.length);
      expect(first.every((entry) => entry.index_title.trim())).toBe(true);
      expect(first.every((entry) => entry.index_contract === CHAPTER_INDEX_CONTRACT_VERSION)).toBe(true);
      auditedChapters += first.length;
    });
    expect(auditedChapters).toBe(691);
  });
});
