You are running /fde-approve — record human approval for the current pending FDE phase.

## Step 1 — Identify the pending phase

Run:
```
python3 -c "
import sys, json
sys.path.insert(0, '.')
from fde.lib.state import current_unapproved_phase, load_state
phase = current_unapproved_phase()
if phase:
    print(phase)
else:
    s = load_state()
    approved = [p for p in ('extract','build','assemble') if getattr(s,p).approved_at]
    if len(approved) == 3:
        print('ALL_APPROVED')
    else:
        print('NONE_PENDING')
"
```

- If output is `ALL_APPROVED`: print "All three phases are approved. Pipeline complete." and stop.
- If output is `NONE_PENDING`: print "No phase has passed validators yet. Run the phase command first, then /fde-approve." and stop.
- Otherwise the output is the phase name (extract / build / assemble). Proceed with that phase.

## Step 2 — Re-run validators

Run the validators for the pending phase to confirm they still pass (artifacts may have changed since the stop hook last ran):

**For extract:**
```
python3 fde/validators/validate_tokens.py && python3 fde/validators/validate_icons.py && python3 fde/validators/validate_copy.py
```

**For build:**
```
python3 fde/validators/validate_inventory.py && python3 fde/validators/validate_components.py
```

**For assemble:**
```
python3 fde/validators/validate_screen_plan.py && python3 fde/validators/validate_screens.py
```

If any validator exits non-zero, show the failures and stop. Do not record approval. Tell the user what needs fixing.

## Step 3 — Present the human-review checklist

Show the checklist for the pending phase and ask the user to verify each item before approving:

**Phase: extract**
- [ ] Every token value matches design source at 100% zoom (spot-check 5+ values in tokens module vs source `:root`)
- [ ] No alpha values were rounded (e.g. 0.65 stayed 0.65)
- [ ] Icon SVG path data is verbatim — not redrawn or optimized
- [ ] Copy strings are exact — no paraphrasing, punctuation preserved
- [ ] `tokens.diff.md` has zero `❌ missing` rows
- [ ] All `⚠️ AMBIGUITY` entries are resolved
- [ ] If multi-theme: missing themes are stubbed, not invented

**Phase: build**
- [ ] Every gallery route renders without errors
- [ ] Each gallery shows every state from the matrix, labeled
- [ ] Interactive components show transitions in the behavior demo section
- [ ] Focus-visible ring is visible on every focusable element when tabbed
- [ ] Visual diff against design source: no color, spacing, or typography mismatches at 100% zoom
- [ ] Zero hardcoded strings, zero hardcoded colors, zero inline SVG in component files
- [ ] If multi-theme: components render correctly in every theme

**Phase: assemble**
- [ ] Every route renders every state variant cleanly
- [ ] Navigation between routes works
- [ ] Responsive behavior matches design (test breakpoint transitions)
- [ ] Deltas list is empty OR every delta is routed back to the correct phase
- [ ] Side-by-side visual diff against design source: no mismatches at 100% zoom

Ask: "Have you verified the checklist above? Type 'approved' to record approval, or describe what needs fixing."

## Step 4 — Record approval (only after user types 'approved')

Run:
```
python3 -c "
import sys, subprocess, datetime
sys.path.insert(0, '.')
from fde.lib.state import mark_approved
from fde.lib.config import load_config

phase = '$PHASE'  # replace with the actual phase name from Step 1
cfg = load_config()

# optionally get git sha
sha = None
try:
    r = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
    if r.returncode == 0:
        sha = r.stdout.strip()
except Exception:
    pass

# write report
import pathlib, json
report_path = f'.fde/reports/{phase}-{datetime.datetime.utcnow().strftime(\"%Y%m%dT%H%M%S\")}.md'
pathlib.Path('.fde/reports').mkdir(parents=True, exist_ok=True)
pathlib.Path(report_path).write_text(f'# Phase {phase} approval\nApproved at: {datetime.datetime.utcnow().isoformat()}Z\nCommit: {sha or \"not in git\"}\n')

mark_approved(phase, sha, report_path)
print(f'Approval recorded. Report: {report_path}')
"
```

Replace `'$PHASE'` with the actual phase name from Step 1.

## Step 5 — Optional git commit

Read `git_commit_on_approve` from `.fde/config.yaml`. If true, run:
```
git add -A && git commit -m "fde: phase <name> approved"
```

## Step 6 — Deactivate FDE hooks if pipeline complete

After recording approval, check if all three phases are now approved:
```
python3 -c "
import sys; sys.path.insert(0,'.')
from fde.lib.state import load_state
s = load_state()
if all(getattr(s,p).approved_at for p in ('extract','build','assemble')):
    print('PIPELINE_COMPLETE')
"
```

If output is `PIPELINE_COMPLETE`:
- Run `rm -f .fde/active` to deactivate stop hooks for future sessions
- Print: "Pipeline complete. Stop hooks deactivated. See docs/methodology.md for the pixel-parity pass checklist."
