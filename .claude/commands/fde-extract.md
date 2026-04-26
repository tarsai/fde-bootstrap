You are running /fde-extract — Phase 1 of the FDE pipeline: token, icon, and copy extraction. This is the only job for this session. Do NOT build components. Do NOT scaffold screens.

## Setup

Run `touch .fde/active` to activate FDE stop hooks for this session.

Read `.fde/config.yaml` in full. Every path below refers to keys in that file. Never invent paths.

**Validate config before proceeding** — run this and stop if it exits non-zero:
```
python3 fde/validators/validate_config.py
```
If it fails, show the output and tell the user to fix `target_stack` in `.fde/config.yaml` before continuing.

If `.fde/state.json` exists and shows `extract.approved_at` is already set, tell the user and ask whether to re-run before proceeding.

## Anti-pattern blocklist — any violation blocks phase approval

- No invented colors, sizes, spacing, copy, or icons
- No "approximately like" or "similar shade"
- No rounding of alpha values (0.65 stays 0.65)
- No new components, no screen files
- No silently resolving design ambiguities — surface them as ⚠️ AMBIGUITY entries

## Step 1 — Read source

Read `primary_design_file` in full. Also read all files listed under `context_docs`.

The `:root` block (or equivalent CSS custom properties / theme objects at the top of the stylesheet) holds foundational tokens. The CSS body holds every typography, spacing, radius, border, shadow, and animation value. Inline `<svg>` blocks are icons. Visible text is copy.

## Step 2 — Produce the tokens module at `tokens_path`

Structure by `theme_mode` from config:
- `single`: flat exported objects
- `light+dark` or `multi-theme`: `{ light: {...}, dark: {...} }` keyed structure. If source only shows one theme, stub the other with `// TODO: theme not in source` — do NOT invent values.

Wrap output behind a `useTheme()` hook or equivalent token-resolver pattern appropriate to `target_stack`.

**Token categories — scan exhaustively:**

1. `colors` — every named color including alpha variants. Preserve exact rgba/hsla. camelCase keys.
2. `semanticColors` — color aliases tied to roles (content-type indicators, status, brand, surface levels). Identify by repeated use tied to meaning.
3. `a11yTokens` — accessibility tokens: focus-ring color, focus-ring width/offset, minimum tap-target size, contrast-pair flags. If not explicit in source, derive from existing tokens and flag as `⚠️ derived` in tokens.diff.md.
4. `fonts` — every font family stack. Mark annotation/handwriting fonts as `// dev-only`. If `font_css_path` is set in config, copy the **exact** Google Fonts `<link>` or `@import` URL from the design source into that file — do not alter it (preserves all axes and weights for validator comparison).
5. `typography` — every distinct combination of font-size + line-height + letter-spacing + font-weight + font-family. Named entry per combination. Do not collapse near-duplicates.
6. `spacing` — every padding/gap/margin value.
7. `radii` — every border-radius.
8. `borders` — every border-width + style + color combination.
9. `shadows` — every box-shadow.
10. `motion` — every transition duration, easing curve, and animation duration.
11. `breakpoints` — every responsive breakpoint.
12. `zIndex` — every z-index value used (if more than one).
13. `assetSpecs` — non-obvious geometric values driving specific elements (rail widths, dot sizes, icon stroke weights). Comment each.

## Step 3 — Produce the icon catalog at `icons_path`

For every distinct inline `<svg>` in source:
- Extract path data **verbatim** — do not redraw, do not optimize
- Name semantically (e.g. `bookmark`, `informative` — not `icon-1`)
- One file per icon exporting a typed component with `size` and `color` props (`color` via `currentColor`)
- `icons_path/catalog.md`: one row per icon with name, source line range, viewBox, default stroke-width if applicable, all sizes/colors used in design

## Step 4 — Produce the copy module at `copy_path`

Every visible text string (headings, body copy, button labels, empty-state messages, toast text, placeholders, meta strings):
- Namespaced keys by location/purpose: `feed.empty.caughtUp.title`, `feed.actions.informative`
- Exact wording including punctuation, em-dashes, ellipses
- Mark designer annotations with comment — do not export them
- ICU-style placeholders for interpolation: `"{count} new · tap to refresh"`
- Structure for future i18n even if not adding it yet

## Step 5 — Produce three diff docs

**`tokens.diff.md`** (in same directory as `tokens_path`) — markdown table:

| CSS variable | Source line | Export path | Status |
|---|---|---|---|
| `--bg-raised` | 12 | `colors.bgRaised` | ✅ mapped |

Status values: `✅ mapped` / `⚠️ derived` / `❌ missing`

**`icons.diff.md`** (inside `icons_path`) — table mapping every source `<svg>` to its catalog entry. Include source line range.

**`copy.diff.md`** (in same directory as `copy_path`) — table mapping every visible string to its key path. Flag strings appearing in design but not extracted — commonly missed: aria-labels, alt text, tooltip text.

## Ambiguity protocol

If source contains contradictions (same color used with two hex values, same component drawn differently across sections, conflicting CSS specificity): do NOT silently resolve. Add a `⚠️ AMBIGUITY` section to the relevant diff doc listing every conflict with source line citations.

## Completion signal

After producing all artifacts, print exactly:

```
Phase 1 complete. Artifacts ready for review:
- [list each file path produced]

⚠️ AMBIGUITY entries: N
```

Then stop. Do NOT begin Phase 2. The stop hook will run validators automatically. Once validators pass, run `/fde-approve` to record human approval.
