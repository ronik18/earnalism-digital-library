// URL state only. These choices never grant Reader or listening access.
const oneOf = (value, options, fallback = 'all') => options.includes(value) ? value : fallback;
export function listeningFilterFromSearch(params) {
  const explicit = params.get('listening');
  if (['all', 'available', 'hidden'].includes(explicit)) return explicit;
  if (params.get('availability') === 'approved-audiobook') return 'available';
  if (['reader-ready', 'audio-hidden'].includes(params.get('availability'))) return 'hidden';
  return 'all';
}
export function libraryFiltersFromSearch(params) {
  const legacy = params.get('category');
  const forms = ['all', 'novel', 'short-story', 'poetry', 'nonfiction'];
  const genre = params.get('genre') || (legacy && ![...forms, 'live', 'pipeline'].includes(legacy) ? legacy : 'all');
  return {
    query: params.get('q') || '',
    language: oneOf(params.get('language'), ['all', 'bn', 'en']),
    reading: oneOf(params.get('reading') || legacy, forms),
    listening: listeningFilterFromSearch(params),
    genre: /^[a-z0-9-]{1,64}$/.test(genre) ? genre : 'all',
    sort: oneOf(params.get('sort'), ['recently-approved', 'title', 'author', 'short-reads'], 'recently-approved'),
    stage: legacy === 'live' ? 'live' : legacy === 'pipeline' ? 'pipeline' : 'all',
  };
}
