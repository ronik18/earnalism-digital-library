/**
 * Customer-facing access copy. Keep the presentation contract separate from
 * server authorization: rendering this text must never imply a client-side
 * entitlement or an audio preview.
 */
export const PUBLIC_PREVIEW_COPY = "First 3 pages free preview";
export const LISTENING_ACCESS_COPY = "Listening requires an active Reading Pass.";
export const PUBLIC_ACCESS_COPY = `${PUBLIC_PREVIEW_COPY}. ${LISTENING_ACCESS_COPY}`;
export const READING_TIME_COPY = "Reading time is used only while you read.";
