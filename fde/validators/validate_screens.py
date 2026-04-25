"""Validate screen files — only import from approved modules, no new styles, no hardcoded copy.

Exit codes: 0 pass / 1 fail / 2 setup error
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fde.lib.config import load_config  # noqa: E402


HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGBA = re.compile(r"\brgba?\s*\(")
INLINE_SVG = re.compile(r"<svg\b", re.IGNORECASE)
# heuristic for hardcoded user-visible strings — JSX text content of >1 word
JSX_TEXT = re.compile(r">([A-Z][a-z][^<>{}\n]{4,})<")


def main() -> int:
    cfg = load_config()
    failures: list[dict] = []
    warnings: list[dict] = []

    routes_dir = cfg.app_routes_path
    if not routes_dir.exists():
        failures.append({"check": "routes_dir_exists", "path": str(routes_dir)})
        _emit({"phase": "assemble", "validator": "screens", "ok": False, "failures": failures})
        return 1

    # find screen files (exclude dev gallery)
    dev_segment = cfg.dev_gallery_route.strip("/").split("/")[0] if cfg.dev_gallery_route else ""
    screen_files = []
    for f in routes_dir.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix not in {".tsx", ".jsx", ".vue", ".svelte", ".swift"}:
            continue
        if dev_segment and dev_segment in f.parts:
            continue
        screen_files.append(f)

    if not screen_files:
        warnings.append({"check": "screens_found", "note": f"no screen files found in {routes_dir}"})

    for f in screen_files:
        content = f.read_text(errors="ignore")
        no_comments = re.sub(r"//.*?$|/\*.*?\*/", "", content, flags=re.MULTILINE | re.DOTALL)

        # 1. no hardcoded hex colors
        hexes = HEX_COLOR.findall(no_comments)
        if hexes:
            failures.append(
                {
                    "check": "no_hardcoded_hex_in_screens",
                    "file": str(f),
                    "matches": hexes[:5],
                    "fix": "import from tokens module — screens cannot introduce new colors",
                }
            )

        # 2. no rgba
        if RGBA.search(no_comments):
            failures.append(
                {
                    "check": "no_hardcoded_rgba_in_screens",
                    "file": str(f),
                    "fix": "import from tokens module",
                }
            )

        # 3. no inline svg
        if INLINE_SVG.search(no_comments):
            failures.append(
                {
                    "check": "no_inline_svg_in_screens",
                    "file": str(f),
                    "fix": "use approved icon component from icons module",
                }
            )

        # 4. no hardcoded user-visible strings — heuristic
        # only flag if there are many; a label like "Today" might be unavoidable in some frameworks
        text_matches = JSX_TEXT.findall(no_comments)
        # filter noise — punctuation, numbers, common keywords
        suspect = [t.strip() for t in text_matches if len(t.strip().split()) >= 2]
        if len(suspect) > 2:
            warnings.append(
                {
                    "check": "possible_hardcoded_strings",
                    "file": str(f),
                    "samples": suspect[:5],
                    "note": "screens should pull strings from copy module — verify these aren't hardcoded",
                }
            )

    ok = len(failures) == 0
    _emit(
        {
            "phase": "assemble",
            "validator": "screens",
            "ok": ok,
            "failures": failures,
            "warnings": warnings,
            "stats": {"screen_files_scanned": len(screen_files)},
        }
    )
    return 0 if ok else 1


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
