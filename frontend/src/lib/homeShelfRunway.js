export const SHELF_RUNWAY_ORDER = [
  "bengali-life-and-legacy",
  "gothic-and-the-uncanny",
  "love-society-and-human-nature",
  "adventure-nature-and-wonder",
  "short-masterpieces",
];

export const SHELF_THEME_CHIPS = {
  "bengali-life-and-legacy": ["Memory & belonging", "Society & reform", "Love & loss"],
  "gothic-and-the-uncanny": ["Haunted worlds", "Divided minds", "Lingering mysteries"],
  "love-society-and-human-nature": ["Desire & dignity", "Class & choice", "Sacrifice & consequence"],
  "adventure-nature-and-wonder": ["Distant worlds", "Untamed nature", "Imaginative journeys"],
  "short-masterpieces": ["One-sitting reads", "Lasting twists", "Complete stories"],
};

export function getShelfVariant(group) {
  if (group?.display_mode === "runway" || group?.layout_area === "short") return "runway";
  if (group?.display_mode === "spotlight") return "spotlight";
  if (group?.display_mode === "duo") return "duo-shelf";
  if (group?.display_mode === "overflow") return "shelf-feature";
  const count = Array.isArray(group?.books) ? group.books.length : 0;
  if (count >= 3) return "shelf-feature";
  if (count === 2) return "duo-shelf";
  if (count === 1) return "spotlight";
  return "hidden";
}
export function getShelfCountLabel(group) {
  const count = Array.isArray(group?.books) ? group.books.length : 0;
  if (count === 1) return "Featured classic";
  return `${count} curated titles`;
}

export function getShelfThemeChips(group) {
  return Array.isArray(group?.theme_chips) && group.theme_chips.length
    ? group.theme_chips
    : SHELF_THEME_CHIPS[group?.id] || [];
}

export function getUniqueShelfBooks(group, limit = 3) {
  const seen = new Set();
  return (Array.isArray(group?.books) ? group.books : [])
    .filter((book) => {
      if (!book?.slug || seen.has(book.slug)) return false;
      seen.add(book.slug);
      return true;
    })
    .slice(0, limit);
}

function shelfBookLimit(group) {
  if (group?.display_mode === "runway" || group?.layout_area === "short" || group?.id === "short-masterpieces") return 6;
  if (group?.display_mode === "duo") return 2;
  if (group?.display_mode === "spotlight") return 1;
  return 3;
}

export function allocateUniqueShelfBooks(groups = []) {
  const allocatedSlugs = new Set();

  return groups.map((group) => {
    const candidates = [
      ...(Array.isArray(group?.books) ? group.books : []),
      ...(Array.isArray(group?.reserve_books) ? group.reserve_books : []),
    ];
    const books = [];

    for (const book of candidates) {
      if (!book?.slug || allocatedSlugs.has(book.slug) || books.some((item) => item.slug === book.slug)) continue;
      books.push(book);
      allocatedSlugs.add(book.slug);
      if (books.length >= shelfBookLimit(group)) break;
    }

    return {
      ...group,
      books,
      visible_books: books,
      reserve_books: [],
      total_count: books.length,
    };
  }).filter((group) => group.books.length > 0);
}
