You are running /fde-assemble — Phase 3 of the FDE pipeline: screen assembly from approved components. This session has two gates: screen plan approval (mid-session) then screen build.

## Setup

Run `touch .fde/active` to activate FDE stop hooks for this session.

Read `.fde/config.yaml` in full. All paths come from that file.

**Phase gate check**: run this command and stop if it exits non-zero:
```
python3 -c "import sys; sys.path.insert(0,'.'); from fde.lib.state import require_prior_approved; require_prior_approved('assemble')"
```

Phases 1 and 2 are FROZEN. Import only — do not modify any file from `tokens_path`, `icons_path`, `copy_path`, or `component_lib_path`.

## Hard rules — read first, enforced by stop hook

1. **No new styles.** If a screen needs a layout primitive not already a component, STOP and list as delta.
2. **No new tokens.** STOP and list as delta.
3. **No new components.** If you find yourself wrapping a primitive with custom styles, that's a sign you should use an existing component variant.
4. **No new copy.** Every string from the copy module. STOP and list as delta if missing.
5. **Layout-only decisions allowed at screen layer**: flex direction, gap, padding between components, scroll behavior, safe-area handling, navigation wiring. These are the ONLY new decisions permitted.
6. **When in doubt, ask.** Surface five questions up front rather than invent five things.

## Source files to read

- `primary_design_file` (full)
- `component_lib_path/INVENTORY.md`
- `tokens_path`, `icons_path/catalog.md`, `copy_path` (read-only reference)
- All `context_docs`

## Gate 1 — Screen plan (produce first, stop for review)

Read `primary_design_file` and `INVENTORY.md`, then produce `component_lib_path/SCREEN_PLAN.md`:

- Each route in `app_routes_path` and which design sections it composes
- For each route: the component tree (which approved components, in what order, with what props)
- For each route: state variants the screen must support (via dev-only query param or in-screen toggle)
- Mock data shape (typed) and where it lives
- Navigation graph between routes
- Any layout decision you are unsure about — surface as an explicit numbered question

After producing SCREEN_PLAN.md, print:
```
Screen plan ready. Review before I begin assembling.
Open questions: N
```

**Stop here and wait for the user to review.** Ask: "Do you approve the screen plan? Answer open questions or type 'approved' to proceed to screen assembly."

## Gate 2 — Screen assembly (only after user approves plan)

For each route in the approved plan:

1. Build screen file at `app_routes_path/<route>`
2. Wire state-variant toggle (dev-only, removable later) for each variant listed in the plan
3. Verify render
4. Output one-line status: `[N/total] <route> assembled — variants: [list]`

## Completion signal

After all screens build, print:
```
Phase 3 complete.

Deltas — things I wanted to add but couldn't (routes back to correct phase):
- [list or "none"]

Layout decisions I was uncertain about:
- [list or "none"]
```

Stop. The stop hook will run validators. Once they pass, run `/fde-approve` to record human approval after reviewing each route side-by-side against the design source.
