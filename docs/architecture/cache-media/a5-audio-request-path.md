# A5 audio request path

All playable routes remain same-origin and release-gated. The route resolves controlled-release truth and Reading Pass authorization before object metadata, ETag/length disclosure, Range planning, B2 HEAD/GET, or streaming bytes. Listener manifests may use the existing `reader-manifest` metadata cache; protected audio-object metadata does not use Redis.

`GET` performs HEAD then complete GET, validates length and available ETag before emitting bytes, and refreshes once only when replacement is detected. Valid range GETs retain the established direct ranged GET and exact `Content-Range` validation. Streaming uses a bounded 1 MiB off-loop iterator with idempotent close on completion, error, and disconnect. Aggregate diagnostics are protected through `/admin/cache/status` only.
