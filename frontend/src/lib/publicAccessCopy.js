/**
 * Customer-facing access copy. Keep the presentation contract separate from
 * server authorization: rendering this text must never imply a client-side
 * entitlement or an audio preview.
 */
export const PUBLIC_PREVIEW_COPY = "Read the first 3 pages free.";
export const LISTENING_ACCESS_COPY = "Public audiobooks are unavailable in this launch.";
export const PUBLIC_ACCESS_COPY = `${PUBLIC_PREVIEW_COPY} ${LISTENING_ACCESS_COPY}`;
export const READING_TIME_COPY = "Reading time is used only while you read.";
