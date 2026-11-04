import assert from 'node:assert/strict';
import { assertQuietFolioReaderChrome } from './lib/quiet_folio_brand_chrome_contract.mjs';
import { quietFolioCaptureFixture } from './test_helpers/quiet_folio_capture_fixture.mjs';

const state = { id: 'reader-mobile-390', route: '/reader/a-ghost-story', fixture: 'reader-visual-safe' };
function fixture() {
  const { reader_topbar, reader_navigation, ...chrome } = quietFolioCaptureFixture();
  return { state_id: state.id, route: state.route, fixture: state.fixture, ...chrome,
    zoom_results: { reader_topbar, reader_navigation },
    reader: { protected_content_exposed: false, protected_prefetch: false, balance_consumption: 0 } };
}
assertQuietFolioReaderChrome(fixture(), state);
const mutations = [
  r => { r.reader_chrome_contract = undefined; },
  r => { r.fixture = 'public-safe'; },
  r => { r.route = '/library'; },
  r => { r.state_id = 'another-state'; },
  r => { r.visible_header_count = 2; },
  r => { r.reader_marketing_header_count = 1; },
  r => { r.visible_canonical_lockup_count = 1; },
  r => { r.logo = {}; },
  r => { r.action_row_below_brand = true; },
  r => { r.zoom_results.reader_topbar.children.title.box = null; },
  r => { r.zoom_results.reader_topbar.children.settings.box.width = 0; },
  r => { r.zoom_results.reader_topbar.children.back.clipped_area = 1; },
  r => { r.zoom_results.reader_topbar.scroll_width = 321; },
  r => { r.zoom_results.reader_topbar.control_overlap_area = 1; },
  r => { r.zoom_results.reader_topbar.content_begins_below_topbar = false; },
  r => { r.zoom_results.reader_topbar.action_row_content_overlap_area = 1; },
  r => { r.zoom_results.reader_topbar.children.fullscreen.box.right = 321; },
  r => { r.zoom_results.reader_navigation.children.Contents = null; },
  r => { r.zoom_results.reader_navigation.children['Next page'].clipped_area = 1; },
  r => { r.zoom_results.reader_navigation.control_overlap_area = 1; },
  r => { r.zoom_results.reader_navigation.children.extra = r.zoom_results.reader_navigation.children.Contents; },
  r => { const c = r.zoom_results.reader_navigation.children; r.zoom_results.reader_navigation.children = {Contents:c.Contents,'Previous page':c['Previous page'],'Next page':c['Next page']}; },
  r => { r.reader.protected_content_exposed = true; },
  r => { r.reader.protected_prefetch = true; },
  r => { r.reader.balance_consumption = 1; },
];
for (const mutate of mutations) { const record = fixture(); mutate(record); assert.throws(() => assertQuietFolioReaderChrome(record, state)); }
assert.throws(() => assertQuietFolioReaderChrome(fixture(), { ...state, fixture: 'public-safe' }));
console.log(`Quiet Folio brand contract: ${mutations.length + 2} positive/negative cases PASS (synthetic validator fixtures only)`);
