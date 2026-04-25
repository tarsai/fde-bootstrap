"""Validate that every visible text string in source has a copy module entry.

Exit codes: 0 pass / 1 fail / 2 setup error
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fde.lib.config import load_config  # noqa: E402
from fde.lib.source_parser import parse_source  # noqa: E402


def main() -> int:
    cfg = load_config()
    failures: list[dict] = []

    if not cfg.copy_path.exists():
        failures.append({"check": "copy_file_exists", "path": str(cfg.copy_path)})
    if not cfg.copy_diff_path.exists():
        failures.append({"check": "copy_diff_exists", "path": str(cfg.copy_diff_path)})

    if failures:
        _emit({"phase": "extract", "validator": "copy", "ok": False, "failures": failures})
        return 1

    src = parse_source(cfg.primary_design_file)
    copy_text = cfg.copy_path.read_text()
    diff_text = cfg.copy_diff_path.read_text()

    # every text string must appear in the copy module — either verbatim or as ICU template
    # we normalize whitespace and check for substring match
    for ts in src.text_strings:
        if _text_appears(ts.text, copy_text):
            continue
        # allow ICU placeholders — strip digits and try again (e.g. "7 new" -> "{count} new")
        if _text_with_placeholders_appears(ts.text, copy_text):
            continue
        failures.append(
            {
                "check": "string_in_copy_module",
                "string": ts.text,
                "source_line": ts.line,
                "context": ts.context,
                "fix": f"add copy entry containing '{ts.text}' (or with ICU placeholder if it has dynamic values)",
            }
        )

    # diff doc must list strings
    if re.search(r"⚠️\s*AMBIGUITY", diff_text, re.IGNORECASE):
        failures.append(
            {
                "check": "no_unresolved_ambiguities",
                "fix": "resolve every ⚠️ AMBIGUITY entry in copy.diff.md before approving",
            }
        )

    # check for no missing rows
    if re.search(r"❌\s*missing", diff_text, re.IGNORECASE):
        failures.append(
            {
                "check": "no_missing_rows_in_diff",
                "fix": "resolve every ❌ missing row in copy.diff.md",
            }
        )

    ok = len(failures) == 0
    # cap reported failures to first 30 to keep output readable
    truncated = failures[:30]
    extra = len(failures) - len(truncated)
    _emit(
        {
            "phase": "extract",
            "validator": "copy",
            "ok": ok,
            "failures": truncated,
            "additional_failures_truncated": extra,
            "stats": {"strings_in_source": len(src.text_strings)},
        }
    )
    return 0 if ok else 1


def _text_appears(needle: str, haystack: str) -> bool:
    """Match needle inside haystack tolerating common formatting variations.

    Tolerates:
    - delimiter quotes around the value in the source file ('foo' / "foo" / `foo`)
    - whitespace collapse
    Does NOT strip embedded punctuation that would change meaning (e.g. apostrophes).
    """
    n = needle.strip()
    if n in haystack:
        return True
    # try with collapsed whitespace
    norm_n = re.sub(r"\s+", " ", n)
    norm_h = re.sub(r"\s+", " ", haystack)
    if norm_n in norm_h:
        return True
    # try escaped (TS source files escape apostrophes when wrapping in single quotes)
    if n.replace("'", "\\'") in haystack:
        return True
    if n.replace('"', '\\"') in haystack:
        return True
    return False


def _text_with_placeholders_appears(needle: str, haystack: str) -> bool:
    """Try matching with digit groups replaced by ICU-style placeholders.

    e.g. '7 new posts' may appear in copy module as '{count} new posts'.
    """
    # replace digit runs with placeholder marker BEFORE escaping
    abstracted = re.sub(r"\d+", "__PLACEHOLDER__", needle)
    pattern = re.escape(abstracted)
    # restore the placeholder as a regex matching {anyName}
    pattern = pattern.replace("__PLACEHOLDER__", r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")
    try:
        return bool(re.search(pattern, haystack))
    except re.error:
        return False


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
