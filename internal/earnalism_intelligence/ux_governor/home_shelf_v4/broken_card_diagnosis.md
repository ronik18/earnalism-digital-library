# Broken Love card diagnosis

The previous Love card used a content-driven outer grid with the cover stage participating in the same implicit row flow as the title, description, chips, and CTA. The cover list then used negative sibling margins and transforms, while the stage used an outward margin. That combination let the cover stack occupy text space and cross the card’s lower edge when the Bengali title wrapped.

The repair moves every tile to `container-type: inline-size` and gives the body explicit `meta`, `title`, `description`, `chips`, `covers`, and `cta` grid areas. The cover stage is a bounded flow child; cover items have no negative margins and no outer-card transforms. At narrow container widths the body becomes a stacked grid with reserved cover height.

`broken_card_geometry.json` records the deterministic geometry model used by the focused tests. It is explicitly a model audit, not a claim of production DOM measurement. Production visual canary remains required before a 10/10 score.
