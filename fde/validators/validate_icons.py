"""Validate that every inline <svg> in source has an icon catalog entry + component file.

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

    if not cfg.icons_path.exists():
        failures.append({"check": "icons_dir_exists", "path": str(cfg.icons_path)})
        _emit({"phase": "extract", "validator": "icons", "ok": False, "failures": failures})
        return 1

    if not cfg.icons_catalog_path.exists():
        failures.append({"check": "icons_catalog_exists", "path": str(cfg.icons_catalog_path)})
    if not cfg.icons_diff_path.exists():
        failures.append({"check": "icons_diff_exists", "path": str(cfg.icons_diff_path)})

    if failures:
        _emit({"phase": "extract", "validator": "icons", "ok": False, "failures": failures})
        return 1

    src = parse_source(cfg.primary_design_file)
    catalog_text = cfg.icons_catalog_path.read_text()
    diff_text = cfg.icons_diff_path.read_text()

    # collect path data fragments — these uniquely identify an icon
    # an icon is "covered" if at least one of its path `d` strings appears in either the catalog
    # or any file in the icons dir
    icon_files_text = ""
    for f in cfg.icons_path.rglob("*"):
        if f.is_file() and f.suffix in {".tsx", ".ts", ".jsx", ".js", ".vue", ".svelte", ".swift"}:
            icon_files_text += f.read_text(errors="ignore")

    for i, svg in enumerate(src.inline_svgs):
        if not svg.paths:
            # path-less icon (rect/circle only) — check that its raw appears in catalog
            if svg.raw[:80] not in catalog_text and svg.raw[:80] not in icon_files_text:
                failures.append(
                    {
                        "check": "svg_has_component_or_catalog_entry",
                        "source_line": svg.line,
                        "fix": "add this svg to icons catalog + component file (path-less icons need raw match)",
                    }
                )
            continue

        # check each path fragment is reproduced somewhere
        first_path = svg.paths[0]
        # use a distinctive substring of the path data
        sig = first_path[:40] if len(first_path) > 40 else first_path
        if sig not in catalog_text and sig not in icon_files_text:
            failures.append(
                {
                    "check": "svg_path_reproduced",
                    "source_line": svg.line,
                    "path_signature": sig,
                    "fix": "create icon component file that contains this exact path data (verbatim, not redrawn)",
                }
            )

    # diff doc must list every svg
    expected_rows = len(src.inline_svgs)
    # rough check — count rows with line: or source line citation
    actual_rows = len(re.findall(r"line\s*\d+", diff_text, re.IGNORECASE))
    if actual_rows < expected_rows:
        failures.append(
            {
                "check": "icons_diff_completeness",
                "expected_min_rows": expected_rows,
                "actual_rows_with_line_refs": actual_rows,
                "fix": "icons.diff.md must have a row per source svg with a line reference",
            }
        )

    # ambiguities
    if re.search(r"⚠️\s*AMBIGUITY", diff_text, re.IGNORECASE):
        failures.append(
            {
                "check": "no_unresolved_ambiguities",
                "fix": "resolve every ⚠️ AMBIGUITY entry in icons.diff.md before approving",
            }
        )

    ok = len(failures) == 0
    _emit(
        {
            "phase": "extract",
            "validator": "icons",
            "ok": ok,
            "failures": failures,
            "stats": {"svgs_in_source": len(src.inline_svgs)},
        }
    )
    return 0 if ok else 1


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
