Build a complete design system based on your selections from search_style_guide results.

Usage:
- USE for any design task that benefits from creative direction or visual inspiration
- USE when creating landing pages, marketing sites, dashboards, or app screens
- USE when the user asks for a specific aesthetic, style, or mood
- USE when designing from scratch, on a blank canvas, or exploring new directions
- USE when remixing, restyling, or creating variations
- Consider SKIPPING only when the task is purely compositional (e.g., "add a button here") with an existing design system
- Call this AFTER reviewing candidates from "search_style_guide"
- ONLY use index or name received from the earlier "search_style_guide" call
- Provide your selection for each domain (style, color, typography, layout) using either the index or name
- Returns a complete design system markdown with colors, typography, spacing, etc.

## Selection Rules

- Each domain (style, color, typography, layout) is optional. Pick the closest candidate from search_style_guide; only omit a domain when no candidate is available.

## Returned Design System

The returned design system is the default authority — use its exact color values, typography, border-radius, and effect parameters (e.g. Background `#FAF5FF` → `#FAF5FF`; border-radius DEFAULT 4px → 4px).

## Post-build Adjustment

When the picked candidate does not fully match the user's intent (e.g. user wants dark mode but the picked palette is light-mode), you may adjust specific token values on the returned system. Constraints:
- Adjust the minimum set of values needed; do not rewrite the whole domain.
- Stay within the same domain (a color mismatch only justifies color adjustments).
- Preserve structural relationships: Background/Foreground/Card contrast, Heading/Body font roles, radius hierarchy.
- Trigger must be a concrete mismatch with user intent, not personal preference.
- Domains you omitted (no candidate) are authored freely with your own design knowledge — not adjustments.
