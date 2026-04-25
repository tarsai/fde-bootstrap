You are running /fde-build — Phase 2 of the FDE pipeline: component build with state matrix and behavior spec. This session has two gates: inventory approval (mid-session) then component build.

## Setup

Run `touch .fde/active` to activate FDE stop hooks for this session.

Read `.fde/config.yaml` in full. All paths come from that file.

**Phase gate check**: run this command and stop if it exits non-zero:
```
python3 -c "import sys; sys.path.insert(0,'.');  from fde.lib.state import require_prior_approved; require_prior_approved('build')"
```

Phase 1 artifacts are FROZEN: `tokens_path`, `icons_path`, `copy_path`. Import only — do not modify.

## Anti-pattern blocklist — any violation blocks phase approval

- No new style values — every value from tokens. If you need something not in tokens, STOP and report it as a delta.
- No inline SVG in components — every icon from the icon catalog
- No hardcoded strings — every visible string from the copy module
- No screen-level files — do not touch any non-dev route
- No invented states — state matrix is the contract
- No silently resolving design ambiguities — surface as ⚠️ AMBIGUITY entries

## Source files to read

- `primary_design_file` (full)
- `tokens_path` (read-only reference)
- `icons_path/catalog.md` (read-only reference)
- `copy_path` (read-only reference)
- All `context_docs`

## Gate 1 — Inventory + behavior spec (produce first, stop for review)

Read `primary_design_file` end-to-end. Produce `component_lib_path/INVENTORY.md` containing two documents:

### Document A — Component inventory

**Three tiers:**
- **Atoms** — no component dependencies
- **Molecules** — compose atoms
- **Composites** — compose molecules; render in gallery for visual review but have no routing, no data fetching, no state toggles beyond their own

**Composite vs. screen distinction**: if it has a URL or fetches data, it is a screen (Phase 3). Composites do not.

For each component: name, tier, dependencies, source line ranges.

**State matrix table:**
- Rows = components (grouped by tier with tier headers)
- Columns = every state encountered across all components (union of: default, hover, focus, focus-visible, active, pressed, disabled, loading, empty, error, filled, expanded, collapsed, selected, plus any design-specific states)
- Cell values:
  - `✅` = state explicitly shown in design (cite section/line in footnote column)
  - `🔍` = state inferred — standard for component type but not in design; include rationale in footnote
  - `—` = state does not apply
  - blank = not yet considered — **zero blanks allowed before Gate 1 passes**
- Footnote column links each `✅` cell to source line range

### Document B — Behavior spec

For every component with interactive states:
- **Trigger** (tap, hover, focus, prop change)
- **Source state → target state**
- **Animation**: duration + easing token from `motion.*`, or "instant"
- **Side effects**: optimistic UI, toast triggers, focus shifts, scroll behaviors
- **Accessibility**: focus management, screen-reader announcements, keyboard equivalents

Mark inferred transitions as `🔍 inferred`.

After producing INVENTORY.md, print:
```
Inventory + behavior spec ready. Review before I begin building.
Ambiguities: N
```

**Stop here and wait for the user to review.** Ask: "Do you approve the inventory? Send corrections or type 'approved' to proceed to component build."

## Gate 2 — Component build (only after user approves inventory)

Build components in tier order: atoms → molecules → composites.

For each component:

1. Build component as `component_lib_path/<ComponentName>.{ext}`
2. Build gallery page at `app_routes_path` + `dev_gallery_route` + `<component-name>` rendering **every state** side-by-side with labels
3. For interactive components, include a "behavior demo" subsection where each transition can be triggered
4. Each component must satisfy:
   - All states from the state matrix (`✅` and `🔍` cells)
   - All transitions from the behavior spec
   - Focus-visible state on every focusable element using `a11yTokens.focusRing`
   - Minimum tap target using `a11yTokens.minTapTarget`
   - Semantic role/aria-label from copy module where applicable
   - Uses `runtime_primitives` only — no platform-foreign elements
5. Verify gallery renders without errors
6. Output one-line status after each: `[N/total] ComponentName built — gallery at dev_gallery_route/component-name`

## Completion signal

After all components build:
```
Phase 2 complete. Gallery routes:
- [list each gallery route]
```

Stop. The stop hook will run validators. Once they pass, run `/fde-approve` to record human approval after reviewing gallery routes.
