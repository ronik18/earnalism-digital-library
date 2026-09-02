# A6 PDF data-URI failure reproduction

The exact A6 test command reproduced one Redis SET through `reader-content-v2` for a synthetic `data:application/pdf;base64,` value. The cache bypass result was false.

The value reached `RedisCacheStore.set`, then `canonical_json_bytes`, whose recursive media classifier did not match it. The matcher expected `application/pdf/`; standard data URIs place parameters or a comma after the MIME type. This is classified as `DATA_URI_MEDIA_TYPE_MATCHER_OMITTED_APPLICATION_PDF`.

No PDF bytes, payload body, key, identity, or sentinel was written into this evidence.
