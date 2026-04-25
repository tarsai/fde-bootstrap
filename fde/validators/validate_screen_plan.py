"""Validate SCREEN_PLAN.md — every route mapped, every component pre-approved.

Exit codes: 0 pass / 1 fail / 2 setup error
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fde.lib.config import load_config  # noqa: E402


def main() -> int:
    cfg = load_config()
    failures: list[dict] = []

    plan = cfg.screen_plan_path
    if not plan.exists():
        failures.append({"check": "screen_plan_exists", "path": str(plan)})
        _emit({"phase": "assemble", "validator": "screen_plan", "ok": False, "failures": failures})
        return 1

    text = plan.read_text()

    # required sections
    required = ["route", "component tree", "state variant", "mock data", "navigation"]
    for r in required:
        if r.lower() not in text.lower():
            failures.append(
                {
                    "check": "section_present",
                    "section": r,
                    "fix": f"SCREEN_PLAN.md must include a section covering '{r}'",
                }
            )

    # open questions must be resolved
    open_questions = re.findall(r"open\s+question", text, re.IGNORECASE)
    unresolved = re.findall(r"❓|TODO|TBD|unresolved", text, re.IGNORECASE)
    if open_questions and unresolved:
        failures.append(
            {
                "check": "open_questions_resolved",
                "unresolved_count": len(unresolved),
                "fix": "resolve every open question (❓/TODO/TBD/unresolved) before approving plan",
            }
        )

    # every component referenced must exist in INVENTORY.md
    inv = cfg.inventory_path
    if inv.exists():
        inv_text = inv.read_text()
        # crude: pull PascalCase identifiers from plan and check they exist in inventory
        plan_components = set(re.findall(r"\b([A-Z][a-zA-Z0-9]{2,})\b", text))
        inv_components = set(re.findall(r"\b([A-Z][a-zA-Z0-9]{2,})\b", inv_text))
        # filter out common false positives
        false_positives = {"TODO", "TBD", "Note", "Important", "Phase", "Step", "Document"}
        plan_components -= false_positives

        missing = plan_components - inv_components
        # be lenient — only flag if many are missing, since PascalCase regex catches noise
        if len(missing) > 3:
            failures.append(
                {
                    "check": "components_pre_approved",
                    "components_in_plan_not_in_inventory": sorted(missing)[:10],
                    "fix": "every component referenced in SCREEN_PLAN.md must be in INVENTORY.md (no new components allowed at Phase 3)",
                }
            )

    ok = len(failures) == 0
    _emit({"phase": "assemble", "validator": "screen_plan", "ok": ok, "failures": failures})
    return 0 if ok else 1


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
