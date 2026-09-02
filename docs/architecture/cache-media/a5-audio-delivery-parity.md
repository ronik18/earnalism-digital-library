# A5 audio delivery parity

The protected route set, authorization order, release gating, disabled-audio behavior, Range vectors, ETag/304 behavior, private cache control, controlled-publication data, and frontend production tree remain unchanged. The deliberate changes are bounded B2 transport settings, pre-byte full-object consistency validation with one retry, cancellation-safe cleanup, `Content-Disposition: inline`, and protected aggregate diagnostics. `If-Range` and Last-Modified are not added because the established ETag contract is authoritative.

Each configured store retains one cached B2 client. Non-secret transport defaults are connect timeout 3 s (clamped 1–10), read timeout 30 s (5–120), standard retry attempts 3 (1–5), and a 20-connection pool (1–100), with TCP keepalive. Malformed environment overrides safely use the default; no Railway setting or credential changed.
