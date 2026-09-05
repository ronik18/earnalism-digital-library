# CUSTOMER_READY autonomy reconciliation

The lower-precedence Context Pack proposed a 180-second public audio preview.
That value was rejected before governance activation: the checked-in Reading
Pass contract, domain constant, and zero-public-audio tests require exactly
zero seconds. The operational envelope therefore requires `seconds: 0` and
does not make approval of an audiobook a public-playback grant.

`docs/product/PRODUCT_TRUTH_CONTRACT.md` was not present during this
reconciliation. Its absence is recorded in `MODERNIZATION_STATE.json`; this
governance change does not invent a replacement product contract.

The older sentence in `docs/reading-pass-access.md` that referred to an
approved public preview was superseded because it conflicted with that same
document's explicit zero-second rule. It now describes only the existing
server-authorized playback path.
