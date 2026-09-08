"use strict";

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[character]));
}

function actionMarkup(action, variant) {
  if (!action) return "";
  const href = String(action.href || "");
  if (!href.startsWith("/") || href.startsWith("//")) throw new Error("Status page: invalid action URL.");
  return `<a class="status-page__action status-page__action--${variant}" href="${escapeHtml(href)}">${escapeHtml(action.label)}</a>`;
}

/**
 * Server-safe direct-status document shared by the 404 and tombstone handlers.
 * Every caller supplies controlled copy; dynamic values are escaped defensively.
 */
function renderBrandedStatusPage({ statusCode, documentTitle, eyebrow, heading, body, primaryAction, secondaryAction }) {
  const safeStatusCode = Number(statusCode);
  if (![404, 410].includes(safeStatusCode)) throw new Error("Status page: unsupported status code.");

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>${escapeHtml(documentTitle)}</title>
    <style>
      @font-face { font-family: "EB Garamond"; src: url("/assets/fonts/eb-garamond-400.ttf") format("truetype"); font-style: normal; font-weight: 400; font-display: swap; }
      @font-face { font-family: "Outfit"; src: url("/assets/fonts/outfit-400.ttf") format("truetype"); font-style: normal; font-weight: 400; font-display: swap; }
      @font-face { font-family: "Outfit"; src: url("/assets/fonts/outfit-600.ttf") format("truetype"); font-style: normal; font-weight: 600; font-display: swap; }
      :root { color-scheme: light; }
      * { box-sizing: border-box; }
      body { margin: 0; background: #F6EDDC; color: #2A171B; font-family: Outfit, Arial, sans-serif; line-height: 1.6; }
      .status-page__masthead { display: flex; width: 100%; min-height: 88px; align-items: center; border: 0; border-bottom: 1px solid rgba(42,23,27,.18); border-radius: 0; background: #FFF9EE; box-shadow: none; padding: 10px clamp(16px,5vw,64px); }
      .status-page__brand-link { display: inline-flex; width: clamp(184px, 22vw, 288px); align-items: center; border: 0; border-radius: 0; background: transparent; box-shadow: none; padding: 0; }
      .status-page__brand-link:focus-visible, .status-page__action:focus-visible { outline: 3px solid #651D32; outline-offset: 4px; }
      .status-page__brand { display: block; width: 100%; height: auto; border: 0; border-radius: 0; background: transparent; box-shadow: none; transform: none; }
      .status-page__content { position: relative; width: min(100% - 40px, 84rem); min-height: calc(100vh - 88px); margin: 0 auto; padding: clamp(72px,12vw,150px) clamp(20px,8vw,110px); overflow: hidden; background: linear-gradient(112deg, #F6EDDC 0%, #F6EDDC 61%, #EEE1C9 61%); }
      .status-page__content::after { position: absolute; right: clamp(-88px,-3vw,0px); bottom: clamp(-110px,-6vw,0px); width: clamp(220px,30vw,430px); height: clamp(220px,30vw,430px); border: 1px solid rgba(190,152,84,.55); border-radius: 50%; content: ""; pointer-events: none; }
      .status-page__eyebrow { position: relative; z-index: 1; margin: 0 0 12px; color: #651D32; font-size: 12px; font-weight: 600; letter-spacing: .16em; text-transform: uppercase; }
      .status-page__heading { position: relative; z-index: 1; max-width: 13ch; margin: 0; color: #2A171B; font-family: "EB Garamond", Georgia, serif; font-size: clamp(42px,7vw,72px); font-weight: 400; line-height: .98; }
      .status-page__body { position: relative; z-index: 1; max-width: 58ch; margin: 24px 0 0; color: #513D40; font-size: clamp(17px,2vw,20px); }
      .status-page__actions { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 12px; margin: 34px 0 0; }
      .status-page__action { display: inline-flex; min-height: 44px; align-items: center; justify-content: center; border: 1px solid #651D32; border-radius: 3px; padding: 11px 18px; color: #651D32; font-weight: 600; text-decoration: none; }
      .status-page__action--primary { color: #FFF9EE; background: #651D32; }
      .status-page__action--secondary { background: transparent; }
      @media (max-width: 640px) { .status-page__masthead { min-height: 76px; padding-inline: 16px; } .status-page__brand-link { width: min(240px, calc(100vw - 32px)); } .status-page__content { width: min(100% - 32px, 760px); min-height: calc(100vh - 76px); padding: 72px 24px; background: #F6EDDC; } .status-page__action { width: 100%; } }
      @media (max-width: 359px) { .status-page__brand-link { width: min(208px, calc(100vw - 32px)); } }
    </style>
  </head>
  <body>
    <header class="status-page__masthead" data-testid="status-brand-masthead">
      <a class="status-page__brand-link" href="/" aria-label="The Earnalism home">
        <img class="status-page__brand" src="/assets/brand/earnalism-brand-lockup.png" width="2400" height="720" alt="The Earnalism — Read. Reflect. Remember.">
      </a>
    </header>
    <main class="status-page__content">
      <p class="status-page__eyebrow">${escapeHtml(eyebrow)}</p>
      <h1 class="status-page__heading">${escapeHtml(heading)}</h1>
      <p class="status-page__body">${escapeHtml(body)}</p>
      <p class="status-page__actions">${actionMarkup(primaryAction, "primary")}${actionMarkup(secondaryAction, "secondary")}</p>
    </main>
  </body>
</html>`;
}

module.exports = { renderBrandedStatusPage };
