# A7 frontend audio lifecycle map

The reproduced defect was route-owned Reader/Listener request cancellation, not
browser-managed audio transport. Each manifest and Reader page effect now owns
an `AbortController`, aborts on route/unmount cleanup, keeps its identity guard,
and suppresses only cancellation errors. The protected audio element remains
React-owned and conditional on current authorization; it is paused on unmount.
No object URL, full-media blob, autoplay, retry loop, public source, or new pass
consumption path exists. See the JSON map for operation-level ownership.
