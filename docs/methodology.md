# Claude Design Handoff → Pixel-Perfect Code: Prompt Pack

> Three-prompt sequence for converting any Claude Design handoff into pixel-perfect code via Claude Code, with explicit human-validation gates between phases. Each prompt is self-contained — paste into a fresh Claude Code session and fill in the `{{placeholders}}`.

---

## How to use this pack

- Unzip the Claude Design handoff. Identify the primary HTML file (the one called out in the bundle's README, usually the file you had open when you triggered the handoff)
- Read it once yourself — skim section structure, count distinct screens/states, note the stack target
- Fill in the **Project Setup** block below
- Run prompts in order. Do not skip gates. Do not let Claude run multiple phases in one session

---

## Project Setup (fill in once)

- `{{PRIMARY_DESIGN_FILE}}` — relative path to the main HTML wireframe (e.g. `design/wireframes.html`)
- `{{CONTEXT_DOCS}}` — comma-separated paths to handoff/spec/system-design markdown docs that ground the work
- `{{TARGET_STACK}}` — e.g. `Next.js + Tailwind + shadcn/ui`, `Expo Router + NativeWind`, `Vue 3 + UnoCSS`, `SwiftUI`
- `{{COMPONENT_LIB_PATH}}` — where shared components live (e.g. `packages/ui/src/`, `src/components/`)
- `{{TOKENS_PATH}}` — where the typed tokens module will live (e.g. `packages/design-tokens/src/tokens.ts`, `src/styles/tokens.ts`)
- `{{ICONS_PATH}}` — where the icon catalog and components live (e.g. `packages/ui/src/icons/`, `src/icons/`)
- `{{COPY_PATH}}` — where UI copy strings live (e.g. `packages/copy/src/strings.ts`, `src/i18n/en.ts`)
- `{{DEV_GALLERY_ROUTE}}` — base route for the per-component dev gallery (e.g. `/(dev)/components/`, `/dev/`, `/__storybook/`)
- `{{APP_ROUTES_PATH}}` — where screen/page files live (e.g. `app/`, `src/pages/`, `src/views/`)
- `{{RUNTIME_PRIMITIVES}}` — the framework's base UI primitives (e.g. `View, Text, Pressable` for RN; `div, span, button` for web; `VStack, Text, Button` for SwiftUI)
- `{{THEME_MODE}}` — `single`, `light+dark`, or `multi-theme` (decides whether tokens are flat or keyed by theme)

---

## Workflow shape

- **Three sessions, three deliverables, three gates** — never let Claude run all three at once
- **Order:** Tokens (+ icons + copy) → Components → Screens
- **Validation surface:** in-repo gallery routes that render every component with every state side-by-side
- **Gate criteria:** each gate has an explicit checklist (see "Definition of approved" sections) — approval is binary, no partial passes
- **Anti-pattern blocklist** (state in every prompt):
  - No invented colors, sizes, spacing, copy, or icons
  - No "approximately like" or "similar shade"
  - No new styles introduced at composite layer
  - No screens before components are signed off
  - No components before tokens are signed off
  - No silently resolving design ambiguities — surface them as questions

---

## Prompt 1 — Tokens, icons, and copy extraction

**Goal:** every design value, icon, and copy string from the source lands in three typed modules, verbatim. Nothing else.

**Paste into a fresh Claude Code session:**

```
You are extracting design tokens, icons, and copy strings from a wireframe HTML file into typed modules for a {{TARGET_STACK}} project. This is Phase 1 of 3. Do NOT build components. Do NOT scaffold screens. Extraction only.

## Source files
Read in full:
- Primary design: `{{PRIMARY_DESIGN_FILE}}`
- Context: {{CONTEXT_DOCS}}

The `:root` block (or equivalent — CSS custom properties, theme objects, or token comments at the top of the stylesheet) contains foundational tokens. The CSS body contains every typography, spacing, radius, border, shadow, and animation value used. Inline `<svg>` blocks contain icons. Visible text inside design markup contains copy strings.

## What to produce

Three modules plus diff docs. Every value VERBATIM from source — no rounding, no approximation.

### 1. `{{TOKENS_PATH}}` — design tokens

#### Theme mode: `{{THEME_MODE}}`
- If `single`: tokens are flat objects
- If `light+dark` or `multi-theme`: structure as `{ light: {...}, dark: {...} }` keyed objects. If source only shows one theme, build that theme and stub the others with `// TODO: theme not in source` placeholders — do NOT invent values
- Wrap output behind a `useTheme()` hook or equivalent token-resolver pattern appropriate to {{TARGET_STACK}}

#### Token categories — scan exhaustively
1. **`colors`** — every named color including alpha variants. Preserve exact rgba/hsla. CamelCase keys.
2. **`semanticColors`** — color aliases mapping to roles (content-type indicators, status, brand, surface levels). Identify by repeated use tied to meaning.
3. **`a11yTokens`** — accessibility-specific tokens: focus-ring color, focus-ring width/offset, minimum-tap-target size, contrast-pair flags. If source doesn't define explicitly, derive from existing tokens AND flag in tokens.diff.md as "derived, needs review."
4. **`fonts`** — every font family stack. Mark annotation/handwriting fonts as "dev-only — skip for production screens."
5. **`typography`** — every distinct combination of font-size + line-height + letter-spacing + font-weight + font-family. Each gets a named entry. Don't collapse near-duplicates.
6. **`spacing`** — every padding/gap/margin value. Group by context.
7. **`radii`** — every border-radius.
8. **`borders`** — every border-width + style + color combination, plus dashed/dotted variants.
9. **`shadows`** — every box-shadow.
10. **`motion`** — every transition duration, easing curve, and animation duration.
11. **`breakpoints`** — every responsive breakpoint.
12. **`zIndex`** — every z-index used (if more than one).
13. **`assetSpecs`** — non-obvious geometric values driving specific elements (rail widths, dot sizes, icon stroke weights). Comment each.

### 2. `{{ICONS_PATH}}/catalog.md` + `{{ICONS_PATH}}/<n>.{ext}` — icon catalog

For every distinct inline SVG in source:
- Extract path data verbatim — do not redraw, do not optimize
- Name semantically (e.g. `informative`, `bookmark`, not `icon-1`)
- One file per icon, exporting a typed component with `size` and `color` props (color via `currentColor`)
- `catalog.md` lists every icon with: name, source line range, default viewBox, default stroke-width if applicable, all sizes/colors used in design

### 3. `{{COPY_PATH}}` — UI copy strings

Every visible text string from design (headings, body copy, button labels, empty-state messages, toast text, placeholder text, meta strings):
- Extract into namespaced object keyed by location/purpose (e.g. `feed.empty.caughtUp.title`, `feed.actions.informative`)
- Preserve exact wording including punctuation, em-dashes, ellipses
- Mark dev-only strings (annotations, designer notes) with comment — do not export those for production
- Pluralization or interpolation gets ICU-style placeholders: `"{count} new · tap to refresh"`
- Structure compatible with future i18n — even if not adding i18n yet, this isolates strings cleanly

### 4. Diff docs

- `tokens.diff.md` — markdown TABLE: rows = each source token (CSS variable or repeated literal), columns = source line, target export path, status (`✅ mapped` / `⚠️ derived` / `❌ missing`). Goal: scannable verification.
- `icons.diff.md` — table mapping every source `<svg>` to its catalog entry
- `copy.diff.md` — table mapping every visible string to its key path. Flag strings appearing in design but not extracted (commonly missed: aria-labels, alt text, tooltip text)

## Ambiguity protocol

If source contains contradictions (same color used with two different hex values, same component drawn two ways across sections, conflicting CSS specificity), do NOT silently resolve. Add `⚠️ AMBIGUITY` section to each diff doc listing every conflict with source line citations. I will resolve before you proceed.

## Validation gate

Stop after producing all artifacts. Print: "Phase 1 complete. Artifacts ready for review:" followed by file list. Print count of `⚠️ AMBIGUITY` entries.

I will review and either approve or send deltas. Do NOT begin Phase 2.
```

**Definition of approved — Phase 1:**

- ✅ Every CSS variable in source maps to a token (verify via `tokens.diff.md` table)
- ✅ Zero `❌ missing` rows in any diff doc
- ✅ Every `⚠️ derived` row reviewed and either accepted or moved to source-explicit values
- ✅ Every `⚠️ AMBIGUITY` resolved with explicit instruction
- ✅ Alpha values not rounded
- ✅ Every visible string has a key (including aria-labels and alt text)
- ✅ Every inline SVG has a catalog entry
- ✅ If `{{THEME_MODE}}` is multi-theme and source only shows one, other themes are stubbed not invented

---

## Prompt 2 — Component build with state matrix and behavior spec

**Goal:** every leaf component built in isolation, with every state and every transition, rendered in a dev-route gallery for review. Zero screen assembly.

**Prerequisites:**

- Phase 1 tokens, icons, copy approved and committed
- Project scaffold exists for `{{TARGET_STACK}}`

**Paste into a fresh Claude Code session:**

```
You are building leaf components for a {{TARGET_STACK}} app. This is Phase 2 of 3. Phase 1 artifacts are FROZEN: tokens at `{{TOKENS_PATH}}`, icons at `{{ICONS_PATH}}`, copy at `{{COPY_PATH}}`. Import only — do not modify.

## Source files
- Design source: `{{PRIMARY_DESIGN_FILE}}`
- Tokens (read-only): `{{TOKENS_PATH}}`
- Icons (read-only): `{{ICONS_PATH}}`
- Copy (read-only): `{{COPY_PATH}}`
- Stack/spec context: {{CONTEXT_DOCS}}

## Stack constraints
- Use {{RUNTIME_PRIMITIVES}} only — no platform-foreign elements
- Every style value comes from tokens. If you need a value not in tokens, STOP and report.
- Every icon comes from the icon catalog. No inline SVG in components.
- Every visible string comes from the copy module. No hardcoded strings.

## Step 1 — Produce inventory + behavior spec FIRST (do not start coding)

Read `{{PRIMARY_DESIGN_FILE}}` end-to-end and produce `{{COMPONENT_LIB_PATH}}/INVENTORY.md` containing TWO documents:

### Document A — Component inventory

- **Three tiers**: atoms (no dependencies), molecules (compose atoms), composites (compose molecules — render in gallery for visual review but are NOT screens; component clusters that always appear together)
- **Composite vs. screen distinction**: composites have no routing, no data fetching, no state-variant toggles beyond their own. If it has a URL or fetches data, it's a screen (Phase 3).
- **Component list**: for each, list name, tier, dependencies, source-file line ranges
- **State matrix table**:
  - **Rows** = components (grouped by tier with tier headers)
  - **Columns** = every state encountered across all components (union of: default, hover, focus, focus-visible, active, pressed, disabled, loading, empty, error, filled, expanded, collapsed, selected, plus design-specific states)
  - **Cell values**:
    - `✅` = state explicitly shown in design (cite section/line in footnote column)
    - `🔍` = state inferred (not in design but standard for component type) — must include rationale in footnote
    - `—` = state does not apply
    - blank = state not yet considered (must be resolved before Step 2)
  - Footnote column links each `✅` cell to source line range
  - Goal: scannable left-to-right per row to see coverage and gaps

### Document B — Behavior spec

For every component with interactive states, document transitions:
- **Trigger** (tap, hover, focus, prop change)
- **Source state → target state**
- **Animation**: duration + easing token from `motion.*`, or "instant" if none
- **Side effects**: optimistic UI updates, toast triggers, focus shifts, scroll behaviors
- **Accessibility behavior**: focus management, screen-reader announcements, keyboard equivalents (Space/Enter activates, Esc dismisses, etc.)

If design doesn't show transitions explicitly, propose them and mark `🔍 inferred`. Do not silently invent.

## Ambiguity protocol

Same as Phase 1. If same component is drawn differently across design sections, list under `⚠️ AMBIGUITY` with line citations. Do not silently pick one.

Stop after producing INVENTORY.md and print: "Inventory + behavior spec ready. Review before I begin building. Ambiguities: N."

I will review, send corrections, and explicitly approve before you start.

## Step 2 — Build components in tier order (only after inventory approval)

For each component (atoms → molecules → composites):

1. Build component as `{{COMPONENT_LIB_PATH}}/<ComponentName>.{ext}`
2. Build gallery page at `{{APP_ROUTES_PATH}}{{DEV_GALLERY_ROUTE}}<component-name>` rendering EVERY state side-by-side with labels
3. For interactive components, gallery includes "behavior demo" subsection where each transition can be triggered and observed
4. Each component must satisfy:
   - All states from INVENTORY state matrix (✅ and 🔍 cells)
   - All transitions from INVENTORY behavior spec
   - Focus-visible state implemented for every focusable element using `a11yTokens.focusRing`
   - Minimum tap target met using `a11yTokens.minTapTarget`
   - Semantic role/aria-label from copy module where applicable
5. Verify gallery renders without errors
6. Output one-line status: `[N/total] <n> built — gallery at {{DEV_GALLERY_ROUTE}}<component-name>`
7. Move to next component

## Hard rules

- Every value MUST come from frozen Phase 1 artifacts. If you need something not exported, STOP.
- No screen-level files. Do not touch any non-dev route.
- No invented states. State matrix is the contract — if design shows a state I missed, flag it; do not silently add or omit.
- Where source uses inline `style` attributes, translate to tokens — do not copy raw px values.
- Components are pure presentational — no data fetching, no global state, no side effects beyond explicit prop callbacks.
- For multi-theme: every component reads tokens through theme resolver, never hardcodes a theme branch.

## Validation gate

After all components build, output: "Phase 2 complete. Gallery routes:" followed by full list.

I will visit each route and review against design. Wait for explicit approval before Phase 3. If I send deltas, fix only the specific component called out — do not refactor unrelated components.
```

**Definition of approved — Phase 2 inventory:**

- ✅ Every section of design source has at least one component mapped (no orphan design areas)
- ✅ State matrix has zero blank cells (every cell is `✅`, `🔍`, or `—`)
- ✅ Every `🔍` cell has rationale in footnote
- ✅ Behavior spec covers every interactive component
- ✅ Every `⚠️ AMBIGUITY` resolved
- ✅ Composite/screen distinction is clear — no screens hiding in composite tier

**Definition of approved — Phase 2 components:**

- ✅ Every gallery route renders without errors
- ✅ Each gallery shows every state from matrix, labeled
- ✅ Each interactive component shows transitions in behavior demo
- ✅ Focus-visible visible on every focusable element when tabbed
- ✅ Visual diff against design source: no color, spacing, or typography mismatches at 100% zoom
- ✅ Zero hardcoded strings, zero hardcoded colors, zero inline SVG
- ✅ If multi-theme: components render correctly in every theme without code branches

---

## Prompt 3 — Screen assembly from approved components

**Goal:** compose screens using only approved Phase 2 components. Zero new styling. Any required styling decision blocks the prompt and surfaces as a delta question.

**Prerequisites:**

- Phase 2 components, INVENTORY.md, and behavior spec approved
- Mock data shape decided (consult spec/system-design docs)

**Paste into a fresh Claude Code session:**

```
You are assembling screens from pre-approved components. This is Phase 3 of 3. Phases 1 and 2 are FROZEN. Import only — do not modify.

## Source files
- Design source: `{{PRIMARY_DESIGN_FILE}}`
- Tokens (read-only): `{{TOKENS_PATH}}`
- Icons (read-only): `{{ICONS_PATH}}`
- Copy (read-only): `{{COPY_PATH}}`
- Components (read-only): `{{COMPONENT_LIB_PATH}}`
- Component inventory + behavior spec: `{{COMPONENT_LIB_PATH}}/INVENTORY.md`
- Stack/spec context: {{CONTEXT_DOCS}}

## Hard rules (read first, repeat at end)

1. **No new styles.** If a screen needs a layout primitive that isn't already a component, STOP and list as delta. Do not inline a new container with style props.
2. **No new tokens.** STOP and list as delta.
3. **No new components.** If you find yourself wrapping a primitive with custom styles, that's a sign you should be using an existing component variant.
4. **No new copy.** Every string from the copy module. STOP and list as delta if missing.
5. **Layout-only deltas allowed at this phase**: screen-level flex direction, gap, padding between components, scroll behavior, safe-area handling, navigation wiring. These are the ONLY decisions allowed.
6. **If in doubt, ask.** Better to surface 5 questions up front than invent 5 things.

## Step 1 — Produce screen plan FIRST (do not start coding)

Read `{{PRIMARY_DESIGN_FILE}}` and INVENTORY.md, then produce `SCREEN_PLAN.md`:

- Each route in target app and which design sections/screens it composes
- For each route, the component tree (which approved components, in what order, with what props)
- For each route, list of state variants the screen must support (drive via dev-only query param or in-screen toggle)
- Mock data shape (typed) and where it lives
- Navigation graph between routes
- Any layout decision you're unsure about — surface as explicit question

Stop after producing SCREEN_PLAN.md and print: "Plan ready. Review before I begin assembling. Open questions: N."

I will review and explicitly approve before you start.

## Step 2 — Assemble screens (only after plan approval)

For each route:
1. Build screen file
2. Wire state-variant toggle (dev-only, removable later)
3. Verify render
4. After each screen, output: `[N/total] <route> assembled — variants: [list]`

## Validation gate

After all screens build, output: "Phase 3 complete." plus:
- Bulleted list of every place you wanted to add a style/value/component/copy but didn't (deltas list)
- Bulleted list of layout decisions you weren't sure about

Empty deltas list = strong signal of good work. Long list = bugs in earlier phases that need backfilling, not patching at screen layer.

I will review each route and either approve or send deltas. Do NOT iterate on deltas yourself — wait for me.
```

**Definition of approved — Phase 3 plan:**

- ✅ Every design section is mapped to a route
- ✅ Every route's component tree uses only approved components
- ✅ Mock data shape matches spec/system-design docs
- ✅ Every "open question" resolved before code starts

**Definition of approved — Phase 3 screens:**

- ✅ Every route renders every state variant cleanly
- ✅ Navigation between routes works
- ✅ Responsive behavior matches design (test breakpoint transitions)
- ✅ Deltas list either empty or all items routed back to correct phase
- ✅ Side-by-side visual diff against design source: no mismatches at 100% zoom

---

## Pixel-parity pass (post-Phase 3)

- Open design source HTML and running app side-by-side at the same effective viewport
- For each screen variant, perform this checklist:
  - **Color check**: pixel-pick 3-5 surfaces per screen, verify against tokens
  - **Type check**: select text in browser devtools, verify computed font-size, line-height, letter-spacing match tokens
  - **Spacing check**: measure padding/gap on key elements with browser ruler against tokens
  - **State check**: trigger every interactive state, verify transition timing matches motion tokens
  - **A11y check**: tab through screen with keyboard, verify focus order and focus-visible rings; run axe or equivalent
  - **Theme check** (if multi-theme): toggle theme, verify no broken contrast
- For any mismatch:
  - Identify which layer owns the bug: token, icon, copy, component, or screen
  - Route fix to correct phase — never patch downstream of where bug lives
  - Re-run the relevant phase's "definition of approved" checklist after fix
- A token-level bug fixed in a screen file becomes permanent tech debt; resist this

---

## Definition of done — entire pack

- ✅ All three phase gates passed
- ✅ Pixel-parity pass complete with zero mismatches
- ✅ All `(dev)` gallery routes either deleted or moved behind a build flag
- ✅ State-variant toggles in screens removed (or wired to feature flags if useful in QA)
- ✅ Tokens, icons, copy modules tagged or version-frozen — future changes require explicit token/component PRs, not screen-level edits
- ✅ INVENTORY.md and SCREEN_PLAN.md archived in repo (e.g. moved to `docs/design-implementation/`) — they're the living spec for future iterations
- ✅ One-pager checked in: `docs/design-implementation/README.md` summarizing the pack used and any project-specific deviations

---

## Why this works

- **Each prompt has one job.** Token extraction can't accidentally invent a component. Component build can't accidentally assemble a screen.
- **Each phase has frozen artifacts downstream.** Phase 2 imports tokens/icons/copy but cannot edit them. Phase 3 imports components but cannot edit them. Forces bugs to surface at the layer they belong to.
- **Inventory + behavior spec + plan precede code.** Cheapest place to catch missing states/transitions/screens is on a markdown checklist, not in a half-built component.
- **The validation surface is the gallery.** Reviewing N components on one page each is faster and more reliable than reviewing a finished app.
- **Deltas are encouraged.** Phase 3 explicitly asks the model to surface things it wanted to invent. Converts silent inventions into explicit questions.
- **Definition of approved is binary.** Each gate is a checklist with no partial passes — prevents drift.
- **Ambiguity protocol forces explicit resolution.** Source contradictions get caught and decided by human, not silently picked by Claude.

---

## Adapting to non-HTML handoffs

If the handoff isn't HTML/CSS (e.g. Figma file via MCP, SwiftUI preview, screenshots only):

- **Phase 1** still produces tokens/icons/copy, but extraction source changes — point Claude at the Figma MCP, the Swift theme file, or for screenshots-only, run a vision pass to extract colors and a derivation pass for typography
- **Phase 2** unchanged — gallery is the validation surface regardless of input format
- **Phase 3** unchanged — components are frozen, screens compose only

The methodology is medium-agnostic. The only thing that changes is the source-of-truth pointer in Phase 1.
