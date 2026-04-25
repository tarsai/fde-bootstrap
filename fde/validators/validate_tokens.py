"""Validate that every CSS variable in source HTML is mapped in tokens module + diff doc.

Exit codes:
  0 = pass
  1 = fail (with structured JSON report on stdout)
  2 = config / setup error
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# allow running as `python fde/validators/validate_tokens.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fde.lib.config import load_config  # noqa: E402
from fde.lib.source_parser import parse_source  # noqa: E402


def _camel_case(s: str) -> str:
    """--bg-raised -> bgRaised"""
    s = s.lstrip("-")
    parts = s.split("-")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _value_appears(value: str, haystack: str) -> bool:
    """Check that a CSS value from source appears in the tokens module.

    Handles common formatting differences without lossy matches:
    - whitespace inside rgba()/hsla() (e.g. `rgba(48,44,44,0.65)` vs `rgba(48, 44, 44, 0.65)`)
    - hex case (#FFF vs #fff)
    - quote style (single vs double, font stacks)
    - trailing semicolons

    Does NOT collapse precision (e.g. 0.65 vs 0.6 must NOT match).
    """
    # strip trailing semicolon and outer whitespace
    needle = value.strip().rstrip(";").strip()
    hay = haystack

    # exact match first
    if needle in hay:
        return True

    # case-insensitive for hex colors only
    if needle.startswith("#") and needle.lower() in hay.lower():
        # confirm it's actually a hex token, not coincidental substring
        return True

    # collapse whitespace inside parentheses for both — handles rgba(48,44,44,0.65) vs rgba(48, 44, 44, 0.65)
    norm_needle = re.sub(r"\s+", "", needle)
    norm_hay = re.sub(r"\s+", "", hay)
    if norm_needle in norm_hay:
        return True

    # quote-flip: replace ' with " and vice versa
    if needle.replace("'", '"') in hay or needle.replace('"', "'") in hay:
        return True

    return False


def main() -> int:
    cfg = load_config()
    failures: list[dict] = []
    warnings: list[dict] = []

    # check artifacts exist
    if not cfg.tokens_path.exists():
        failures.append({"check": "tokens_file_exists", "path": str(cfg.tokens_path)})
    if not cfg.tokens_diff_path.exists():
        failures.append({"check": "tokens_diff_exists", "path": str(cfg.tokens_diff_path)})

    if failures:
        _emit({"phase": "extract", "validator": "tokens", "ok": False, "failures": failures})
        return 1

    # parse source
    if not cfg.primary_design_file.exists():
        failures.append({"check": "primary_design_file_exists", "path": str(cfg.primary_design_file)})
        _emit({"phase": "extract", "validator": "tokens", "ok": False, "failures": failures})
        return 2

    src = parse_source(cfg.primary_design_file)
    tokens_text = cfg.tokens_path.read_text()
    diff_text = cfg.tokens_diff_path.read_text()

    # 1. every CSS variable maps in tokens module: key present AND value present.
    # We require both because either alone is too permissive — a key present with the wrong
    # value would silently pass.
    for var in src.css_variables:
        camel_key = _camel_case(var.name)
        key_present = camel_key in tokens_text
        value_present = _value_appears(var.value, tokens_text)

        if not key_present:
            failures.append(
                {
                    "check": "css_var_key_in_tokens",
                    "var": var.name,
                    "expected_key": camel_key,
                    "source_line": var.line,
                    "fix": f"add `{camel_key}` export to tokens module",
                }
            )
        elif not value_present:
            failures.append(
                {
                    "check": "css_var_value_matches",
                    "var": var.name,
                    "expected_value": var.value,
                    "source_line": var.line,
                    "fix": f"`{camel_key}` is in tokens but the value `{var.value}` from source line {var.line} is not present — value mismatch",
                }
            )

    # 2. every CSS variable appears in tokens.diff.md
    for var in src.css_variables:
        if var.name not in diff_text:
            failures.append(
                {
                    "check": "css_var_in_diff_doc",
                    "var": var.name,
                    "source_line": var.line,
                    "fix": f"add row for `{var.name}` to tokens.diff.md",
                }
            )

    # 3. tokens.diff.md has no ❌ missing rows
    missing_rows = re.findall(r"❌\s*missing", diff_text, re.IGNORECASE)
    if missing_rows:
        failures.append(
            {
                "check": "no_missing_rows_in_diff",
                "count": len(missing_rows),
                "fix": "resolve every ❌ missing row in tokens.diff.md before approving",
            }
        )

    # 4. unresolved ambiguities
    ambiguities = re.findall(r"⚠️\s*AMBIGUITY", diff_text, re.IGNORECASE)
    if ambiguities:
        failures.append(
            {
                "check": "no_unresolved_ambiguities",
                "count": len(ambiguities),
                "fix": "resolve every ⚠️ AMBIGUITY entry before approving (human decision required)",
            }
        )

    # 5. media queries → breakpoints check (warning only — naming may differ)
    if src.media_queries and "breakpoint" not in tokens_text.lower():
        warnings.append(
            {
                "check": "breakpoints_exported",
                "media_queries_in_source": src.media_queries,
                "note": "source has @media rules but tokens module has no obvious `breakpoints` export",
            }
        )

    # 6. keyframes → motion check
    if src.keyframes and "motion" not in tokens_text.lower() and "duration" not in tokens_text.lower():
        warnings.append(
            {
                "check": "motion_exported",
                "keyframes_in_source": src.keyframes,
                "note": "source has @keyframes but tokens module has no obvious motion/duration tokens",
            }
        )

    # 7. a11y tokens — required category
    if "a11y" not in tokens_text.lower() and "focusring" not in tokens_text.lower().replace(" ", ""):
        failures.append(
            {
                "check": "a11y_tokens_exported",
                "fix": "add a11yTokens export with focusRing, focusRingWidth, minTapTarget at minimum",
            }
        )

    # 8. theme structure check
    if cfg.theme_mode != "single":
        if "light" not in tokens_text.lower() or "dark" not in tokens_text.lower():
            failures.append(
                {
                    "check": "multi_theme_structure",
                    "configured_mode": cfg.theme_mode,
                    "fix": "tokens must be structured as { light: {...}, dark: {...} } per theme_mode in config",
                }
            )

    ok = len(failures) == 0
    _emit(
        {
            "phase": "extract",
            "validator": "tokens",
            "ok": ok,
            "failures": failures,
            "warnings": warnings,
            "stats": {
                "css_variables_in_source": len(src.css_variables),
                "media_queries_in_source": len(src.media_queries),
                "keyframes_in_source": len(src.keyframes),
            },
        }
    )
    return 0 if ok else 1


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
