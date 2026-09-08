#!/usr/bin/env node
import assert from "node:assert/strict";
import { chromium } from "playwright";
import {
  MICRO_STORY_PRIMARY_CTA_SELECTOR,
  captureMicroStoryCampaign,
} from "./lib/micro_story_campaign_capture.mjs";

const cases = [
  ["visible hero and hooked CTA", '<section class="micro-story-hero"><a data-testid="micro-story-library-cta">Explore</a></section>', "ACTIVE_CAMPAIGN", true],
  ["visible hero without hooked CTA", '<section class="micro-story-hero"><a class="micro-story-hero__cta">Decoy</a></section>', "INACTIVE", false],
  ["visible hero with hidden hooked CTA", '<section class="micro-story-hero"><a data-testid="micro-story-library-cta" style="display:none">Explore</a></section>', "INACTIVE", false],
  ["hidden hero with visible hooked CTA", '<section class="micro-story-hero" style="display:none"></section><a data-testid="micro-story-library-cta">Explore</a>', "INACTIVE", true],
];

assert.equal(MICRO_STORY_PRIMARY_CTA_SELECTOR, '[data-testid="micro-story-library-cta"]');
const browser = await chromium.launch({ headless: true });
try {
  for (const [label, markup, state, ctaPresent] of cases) {
    const page = await browser.newPage();
    await page.setContent(markup);
    assert.deepEqual(await page.evaluate(captureMicroStoryCampaign, MICRO_STORY_PRIMARY_CTA_SELECTOR), {
      micro_story_campaign_state: state,
      micro_story_primary_cta_present: ctaPresent,
    }, label);
    await page.close();
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify({ result: "PASS", testCaseCount: cases.length }));
