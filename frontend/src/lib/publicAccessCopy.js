/**
 * Customer-facing access copy. Keep the presentation contract separate from
 * server authorization: rendering this text must never imply a client-side
 * entitlement or an audio preview.
 */
export const PUBLIC_PREVIEW_COPY = "Read the first 3 pages free.";
export const LISTENING_ACCESS_COPY = "Public audiobooks are unavailable in this launch.";
export const PUBLIC_ACCESS_COPY = `${PUBLIC_PREVIEW_COPY} ${LISTENING_ACCESS_COPY}`;
export const AUTH_PRODUCT_ACCESS_COPY = "The first 3 pages are free where a preview is available. A Reading Pass is required from page 4 on eligible titles. Listening appears only where an edition is approved.";
export const READING_TIME_COPY = "Reading time is used only while you read.";
