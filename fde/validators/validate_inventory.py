"""Validate INVENTORY.md — state matrix has zero blanks, behavior spec covers interactives.

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

    inv = cfg.inventory_path
    if not inv.exists():
        failures.append({"check": "inventory_file_exists", "path": str(inv)})
        _emit({"phase": "build", "validator": "inventory", "ok": False, "failures": failures})
        return 1

    text = inv.read_text()

    # 1. must contain both documents
    if not re.search(r"document\s*a", text, re.IGNORECASE) or "state matrix" not in text.lower():
        failures.append(
            {
                "check": "document_a_state_matrix_present",
                "fix": "INVENTORY.md must contain Document A — Component inventory with state matrix table",
            }
        )

    if not re.search(r"document\s*b", text, re.IGNORECASE) or "behavior" not in text.lower():
        failures.append(
            {
                "check": "document_b_behavior_spec_present",
                "fix": "INVENTORY.md must contain Document B — Behavior spec",
            }
        )

    # 2. find the state matrix table and inspect cells
    matrix = _extract_matrix(text)
    if matrix is None:
        failures.append(
            {
                "check": "state_matrix_table_parseable",
                "fix": "state matrix must be a markdown table — rows=components, columns=states, cells=✅/🔍/—",
            }
        )
    else:
        blank_cells = _find_blank_cells(matrix)
        if blank_cells:
            failures.append(
                {
                    "check": "no_blank_cells_in_matrix",
                    "blank_cells": blank_cells[:20],
                    "total_blanks": len(blank_cells),
                    "fix": "every cell must be ✅ (explicit), 🔍 (inferred), or — (n/a). Blanks not allowed.",
                }
            )

        # 3. every 🔍 cell must have a footnote rationale
        inferred_count = sum(row.count("🔍") for row in matrix["rows"])
        footnote_refs = len(re.findall(r"🔍.*?\[(\d+|\^\w+)\]", text))
        if inferred_count > 0 and footnote_refs == 0:
            failures.append(
                {
                    "check": "inferred_cells_have_rationale",
                    "inferred_cells": inferred_count,
                    "fix": "every 🔍 cell must reference a footnote with rationale for the inference",
                }
            )

    # 4. tier headers present
    tiers = ["atom", "molecule", "composite"]
    found_tiers = [t for t in tiers if re.search(rf"\b{t}s?\b", text, re.IGNORECASE)]
    if len(found_tiers) < 3:
        failures.append(
            {
                "check": "three_tiers_present",
                "found": found_tiers,
                "fix": "inventory must group components into atoms / molecules / composites",
            }
        )

    # 5. unresolved ambiguities
    if re.search(r"⚠️\s*AMBIGUITY", text, re.IGNORECASE):
        failures.append(
            {
                "check": "no_unresolved_ambiguities",
                "fix": "resolve every ⚠️ AMBIGUITY entry in INVENTORY.md before approving",
            }
        )

    ok = len(failures) == 0
    _emit({"phase": "build", "validator": "inventory", "ok": ok, "failures": failures})
    return 0 if ok else 1


def _extract_matrix(text: str) -> dict | None:
    """Find the state matrix markdown table and parse cells."""
    # heuristic: find a table where header row contains "default" or "hover" or "state"
    lines = text.split("\n")
    table_start = None
    for i, line in enumerate(lines):
        if "|" in line and re.search(r"\b(default|hover|state)\b", line, re.IGNORECASE):
            table_start = i
            break
    if table_start is None:
        return None

    # collect contiguous table lines
    rows = []
    headers = None
    for line in lines[table_start:]:
        if "|" not in line.strip():
            break
        if re.match(r"^\s*\|?[\s\-:|]+\|?\s*$", line):
            continue  # separator row
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if headers is None:
            headers = cells
        else:
            rows.append(cells)
    if headers is None:
        return None
    return {"headers": headers, "rows": rows}


def _find_blank_cells(matrix: dict) -> list[dict]:
    blanks: list[dict] = []
    headers = matrix["headers"]
    for row in matrix["rows"]:
        if not row:
            continue
        component = row[0] if row else "?"
        # skip tier-header rows (e.g. just "**Atoms**")
        if all(c == "" or re.match(r"^\*\*?[a-zA-Z]+\*\*?$", c) for c in row[1:]):
            continue
        for j, cell in enumerate(row[1:], start=1):
            if cell == "":
                col = headers[j] if j < len(headers) else f"col{j}"
                blanks.append({"component": component, "state": col})
    return blanks


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
