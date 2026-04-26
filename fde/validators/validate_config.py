"""Validate that target_stack in config.yaml matches actual project dependencies.

Exit codes:
  0 = pass
  1 = fail (with structured JSON report on stdout)
  2 = config / setup error
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fde.lib.config import load_config, validate_stack_vs_deps  # noqa: E402


def main() -> int:
    cfg = load_config()
    mismatches = validate_stack_vs_deps(cfg)

    ok = len(mismatches) == 0
    failures = [
        {
            "check": "target_stack_vs_package_json",
            "keyword": m["keyword"],
            "fix": m["fix"],
        }
        for m in mismatches
    ]

    _emit(
        {
            "phase": "extract",
            "validator": "config",
            "ok": ok,
            "failures": failures,
            "stats": {
                "stack_keywords_checked": len(mismatches) + (0 if mismatches else 0),
                "mismatches": len(mismatches),
            },
        }
    )
    return 0 if ok else 1


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
