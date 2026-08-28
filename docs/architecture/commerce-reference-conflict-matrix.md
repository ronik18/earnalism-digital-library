# Commerce reference-conflict matrix

The dedicated Commerce reference is preserved as a `REGION_REFERENCE`. The raw pixel score remains literal: `64.246647` after the Commerce checkpoint, with no masking. The corresponding structured data is in `commerce-reference-conflict-matrix.json`.

| Reference region | Raw mismatch pixels | Classification | Truthful production replacement | Owner input still needed |
| --- | ---: | --- | --- | --- |
| Header | 23,416 | CORRECTABLE_STRUCTURE, CORRECTABLE_STYLE | Canonical logo and current navigation | None |
| Dark hero and proof panel | 41,170 | CORRECTABLE_STRUCTURE, CORRECTABLE_STYLE, OWNER_SOURCE_ASSET_REQUIRED | Existing approved library artwork and policy facts | Production-resolution chair-and-lamp source asset |
| Offer grid | 127,551 | CORRECTABLE_STRUCTURE, CORRECTABLE_TYPOGRAPHY, DYNAMIC_PRODUCTION_DATA | Current configured offers | None |
| Pathways and trust row | 164,762 | CORRECTABLE_STRUCTURE, PRODUCT_CAPABILITY_NOT_AVAILABLE | Supported institution/publisher and trust cards | Configured Gift capability if required |
| Editorial insight rail | 229,035 | CORRECTABLE_STYLE, UNSUPPORTED_REFERENCE_CLAIM | Verified access, privacy, preview, and approval facts | Verified research, ratings, testimonials, and reader imagery |

The matrix deliberately preserves reference geometry where possible. It does not convert unsupported mock claims into live content, use a crop of the composite board as a production asset, or expand the mask policy.
