// Synthetic validator fixtures only. These are not browser or release evidence.
export function quietFolioCaptureFixture() {
  const box = (left, top, width, height) => ({ left, top, width, height, right: left + width, bottom: top + height });
  const control = (left, top, width = 44) => ({ box: box(left, top, width, 44), clipped_area: 0 });
  return {
    reader_chrome_contract: 'QUIET_FOLIO_NO_MARKETING_MASTHEAD',
    visible_header_count: 1, reader_marketing_header_count: 0,
    visible_canonical_lockup_count: 0, logo: null, action_row_below_brand: null,
    reader_topbar: {
      contract: 'QUIET_FOLIO', box: box(0, 0, 320, 54), client_width: 320, scroll_width: 320,
      children: { back: control(0, 0), title: control(44, 0, 180), settings: control(224, 0), fullscreen: control(268, 0) },
      control_overlap_area: 0, content_begins_below_topbar: true, action_row_content_overlap_area: 0,
    },
    reader_navigation: {
      box: box(0, 500, 320, 44), control_overlap_area: 0,
      children: { 'Previous page': control(0, 500), Contents: control(138, 500), 'Next page': control(276, 500) },
    },
  };
}
