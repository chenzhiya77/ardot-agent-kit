Search for style guide candidates across multiple design domains.

⚠️ ALL keyword parameters MUST be English. The catalog is indexed in English only and non-ASCII input (Chinese / Japanese / etc.) is rejected. Translate the user's intent into standard English design vocabulary BEFORE calling — do not pass the user's original-language words. Example: "赛博朋克音乐 App" → designKeywords: "music app cyberpunk neon futuristic".

Usage:
- USE for any design task that benefits from creative direction or visual inspiration
- USE when creating landing pages, marketing sites, dashboards, or app screens
- USE when the user asks for a specific aesthetic, style, or mood
- USE when designing from scratch or on a blank canvas
- USE when remixing, restyling, or exploring variations
- Consider SKIPPING only when the task is purely compositional (e.g., "add a button here") with an existing design system
- Returns candidates per domain (styles, colors, typography, and possibly additional layout-related domains depending on topic)
- The `score` field reflects BM25 keyword overlap density, not semantic suitability — do not default to the highest-scored candidate; judge by record content against user intent
- The `source` field on style candidates indicates retrieval path ("direct" = matched via keywords; "product" = matched via the product type's recommended styles; "direct_product" = matched by both paths) — treat it as supplementary context only; judge primarily by record content

## Selection Protocol (call once)

Review each domain's candidates against the user's intent:
- **style**: Does the Style Category match the requested visual style?
- **color**: Check Background, Card, and Foreground values specifically (e.g. dark-mode intent vs light backgrounds).
- **typography**: Does the mood match? Is the font available?

For each domain, pick the closest candidate and pass its index/name to `build_style_guide`. If the picked candidate is imperfect, refine on the build result rather than re-searching.

Per-parameter mode: pass a keyword string to search; omit optional params to fall back to designKeywords.
