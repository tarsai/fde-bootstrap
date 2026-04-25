You are running /fde-status — read-only pipeline status. Do not modify any files.

## Step 1 — Read state and config

Read `.fde/state.json` (if absent, no phase has run). Read `.fde/config.yaml`.

## Step 2 — Show pipeline status

Print a status table like this:

```
FDE Pipeline Status
───────────────────────────────────────────────────────
Phase       Validators      Approved        Commit
───────────────────────────────────────────────────────
extract     ✅ 2025-01-15   ✅ 2025-01-15   abc1234
build       ✅ 2025-01-16   ⏳ pending      —
assemble    ⬜ not run      ⬜ not run      —
───────────────────────────────────────────────────────
```

Use:
- `✅ <date>` if the field is set
- `⏳ pending` if validators passed but approval not yet recorded
- `⬜ not run` if neither has happened
- `—` for commit if none

## Step 3 — Show next action

Print what the user should do next:
- If extract not yet run: "Next: `/fde-extract`"
- If extract ran but validators not passed: "Next: fix validator failures, then `/fde-extract` will re-run stop hook"
- If extract validators passed but not approved: "Next: `/fde-approve`"
- If extract approved but build not run: "Next: `/fde-build`"
- (continue the pattern for build → assemble)
- If all approved: "Pipeline complete. Run the pixel-parity pass from `docs/methodology.md`."

## Step 4 — Drift warnings

Check for files that exist but shouldn't, or expected files missing:

- If `tokens_path` doesn't exist but extract is marked approved: warn "⚠️ tokens file missing — state may be stale"
- If `component_lib_path/INVENTORY.md` doesn't exist but build is marked approved: warn "⚠️ INVENTORY.md missing"
- If `component_lib_path/SCREEN_PLAN.md` doesn't exist but assemble is marked approved: warn "⚠️ SCREEN_PLAN.md missing"
- If `.fde/active` exists but no phase is pending: "ℹ️ .fde/active is set (stop hooks active) — remove with `rm .fde/active` when not running FDE commands"
- If `.fde/active` does not exist but a phase is pending approval: "ℹ️ .fde/active not set — stop hooks are inactive. Run `touch .fde/active` before the next phase command."

Print each warning on its own line. If none, print "No drift detected."
