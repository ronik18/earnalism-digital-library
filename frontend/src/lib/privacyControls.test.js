import { OPTIONAL_ANALYTICS_ENABLED } from './privacyControls';
import { analyticsNetworkEnabled, getAnonymousLaunchSessionId, getLaunchAnalyticsAttribution, trackFunnelEvent, resetLaunchAnalyticsForTests } from './funnelAnalytics';

test('launch privacy gate prevents storage and network despite old enable flags', () => {
  const fetchBefore = global.fetch;
  const flagBefore = process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS;
  const globalBefore = window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__;
  global.fetch = jest.fn();
  process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS = 'true';
  window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__ = true;
  window.sessionStorage.clear();
  window.history.replaceState({}, '', '/?utm_source=campaign');
  resetLaunchAnalyticsForTests();
  try {
    expect(OPTIONAL_ANALYTICS_ENABLED).toBe(false);
    expect(analyticsNetworkEnabled()).toBe(false);
    expect(getAnonymousLaunchSessionId()).toBe('');
    expect(getLaunchAnalyticsAttribution()).toEqual({});
    trackFunnelEvent('homepage_view');
    expect(window.sessionStorage.length).toBe(0);
    expect(global.fetch).not.toHaveBeenCalled();
  } finally {
    global.fetch = fetchBefore;
    if (flagBefore === undefined) delete process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS; else process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS = flagBefore;
    if (globalBefore === undefined) delete window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__; else window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__ = globalBefore;
  }
});
