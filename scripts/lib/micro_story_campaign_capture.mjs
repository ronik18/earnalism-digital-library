export const MICRO_STORY_PRIMARY_CTA_SELECTOR = '[data-testid="micro-story-library-cta"]';

export function captureMicroStoryCampaign(selector = MICRO_STORY_PRIMARY_CTA_SELECTOR) {
  const visible = (node) => {
    if (!node) return false;
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  };
  const heroVisible = visible(document.querySelector(".micro-story-hero"));
  const primaryCtaVisible = visible(document.querySelector(selector));
  return {
    micro_story_campaign_state: heroVisible && primaryCtaVisible ? "ACTIVE_CAMPAIGN" : "INACTIVE",
    micro_story_primary_cta_present: primaryCtaVisible,
  };
}
