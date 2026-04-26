#!/usr/bin/env python3
"""Stop hook for /fde-assemble — runs Phase 3 validators.

Only fires when .fde/active exists (created by /fde-assemble at session start).
Exit 0 = allow Claude to stop.
Exit 1 = validators failed, block stop and show failures to Claude.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

VALIDATORS = [
    ("screen_plan", ROOT / "fde/validators/validate_screen_plan.py"),
    ("screens",     ROOT / "fde/validators/validate_screens.py"),
]


def _watched_paths() -> list[Path]:
    try:
        sys.path.insert(0, str(ROOT))
        from fde.lib.config import load_config
        cfg = load_config()
        return [cfg.app_routes_path]
    except SystemExit:
        return []


def main() -> int:
    if not (ROOT / ".fde/active").exists():
        return 0

    if not (ROOT / ".fde/config.yaml").exists():
        return 0

    sys.path.insert(0, str(ROOT))
    from fde.lib.state import should_skip_validators, record_validator_run

    watched = _watched_paths()
    if should_skip_validators("assemble", watched):
        return 0

    failures: list[tuple[str, str]] = []

    for name, script in VALIDATORS:
        if not script.exists():
            print(f"STOP HOOK ERROR: validator not found: {script}", file=sys.stderr)
            return 2

        r = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )

        if r.returncode == 2:
            print(f"STOP HOOK WARNING ({name}): setup error — {r.stdout.strip() or r.stderr.strip()}", file=sys.stderr)
            continue

        if r.returncode != 0:
            output = r.stdout.strip() or r.stderr.strip()
            try:
                report = json.loads(output)
                formatted = _format_report(name, report)
            except (json.JSONDecodeError, KeyError):
                formatted = output
            failures.append((name, formatted))

    record_validator_run("assemble", watched)

    if failures:
        print("─── Phase 3 stop hook: VALIDATORS FAILED ───\n")
        for name, msg in failures:
            print(f"[ {name} ]\n{msg}\n")
        print("Fix the issues above, then I will try to stop again.")
        return 1

    try:
        from fde.lib.state import mark_validators_passed
        mark_validators_passed("assemble")
    except Exception as e:
        print(f"STOP HOOK WARNING: validators passed but could not update state: {e}", file=sys.stderr)

    (ROOT / ".fde/active").unlink(missing_ok=True)
    print("✓ Phase 3 validators passed. Run /fde-approve to record human approval after reviewing each screen route.")
    return 0


def _format_report(name: str, report: dict) -> str:
    lines = []
    for f in report.get("failures", []):
        check = f.get("check", "?")
        fix = f.get("fix", "")
        detail = f.get("route") or f.get("file") or f.get("path") or ""
        line = f"  ✗ {check}"
        if detail:
            line += f" ({detail})"
        if fix:
            line += f"\n    → {fix}"
        lines.append(line)
    stats = report.get("stats", {})
    if stats:
        lines.append("  stats: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    return "\n".join(lines) if lines else str(report)


if __name__ == "__main__":
    sys.exit(main())
