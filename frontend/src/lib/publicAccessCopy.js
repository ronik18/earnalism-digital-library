import productCopy from "../content/productCopy.json";

/**
 * Customer-facing access copy. Keep the presentation contract separate from
 * server authorization: rendering this text must never imply a client-side
 * entitlement or an audio preview.
 */
export const PUBLIC_PREVIEW_COPY = productCopy.preview;
export const PUBLIC_READER_ACCESS_COPY = productCopy.readerAccess;
export const LISTENING_ACCESS_COPY = productCopy.listeningAccess;
export const PUBLIC_ACCESS_COPY = `${PUBLIC_PREVIEW_COPY} ${LISTENING_ACCESS_COPY}`;
export const AUTH_PRODUCT_ACCESS_COPY = `${PUBLIC_READER_ACCESS_COPY} ${LISTENING_ACCESS_COPY}`;
export const READING_TIME_COPY = productCopy.readingTime;
