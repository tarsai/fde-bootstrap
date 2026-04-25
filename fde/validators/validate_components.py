"""Validate component build — every inventory component has a gallery route, no hardcoded values.

Exit codes: 0 pass / 1 fail / 2 setup error
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fde.lib.config import load_config  # noqa: E402


# patterns that indicate hardcoded design values
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGBA = re.compile(r"\brgba?\s*\(")
PX_VALUE = re.compile(r"\b\d+px\b")
INLINE_SVG_TAG = re.compile(r"<svg\b", re.IGNORECASE)


def main() -> int:
    cfg = load_config()
    failures: list[dict] = []
    warnings: list[dict] = []

    inv = cfg.inventory_path
    if not inv.exists():
        failures.append({"check": "inventory_exists", "path": str(inv)})
        _emit({"phase": "build", "validator": "components", "ok": False, "failures": failures})
        return 1

    inv_text = inv.read_text()
    component_names = _extract_component_names(inv_text)
    if not component_names:
        failures.append(
            {
                "check": "components_listed_in_inventory",
                "fix": "could not parse component names from INVENTORY.md — ensure tier sections list components",
            }
        )
        _emit({"phase": "build", "validator": "components", "ok": False, "failures": failures})
        return 1

    # check each component has a file in component_lib_path
    if not cfg.component_lib_path.exists():
        failures.append({"check": "component_lib_dir_exists", "path": str(cfg.component_lib_path)})
        _emit({"phase": "build", "validator": "components", "ok": False, "failures": failures})
        return 1

    component_files = list(cfg.component_lib_path.rglob("*"))
    component_filenames = {f.stem for f in component_files if f.is_file()}

    for name in component_names:
        if name not in component_filenames:
            failures.append(
                {
                    "check": "component_file_exists",
                    "component": name,
                    "expected_in": str(cfg.component_lib_path),
                    "fix": f"create {name} component file under {cfg.component_lib_path}",
                }
            )

    # check each component has a gallery route file
    gallery_dir = cfg.app_routes_path / cfg.dev_gallery_route.strip("/")
    # try alternate normalization
    if not gallery_dir.exists():
        # dev_gallery_route may include parens like (dev) — try direct join
        gallery_dir = Path(str(cfg.app_routes_path).rstrip("/") + "/" + cfg.dev_gallery_route.strip("/"))

    gallery_files = []
    if gallery_dir.exists():
        gallery_files = [f.stem for f in gallery_dir.rglob("*") if f.is_file()]

    for name in component_names:
        # gallery files often kebab-case
        kebab = _kebab(name)
        if name not in gallery_files and kebab not in gallery_files:
            failures.append(
                {
                    "check": "gallery_route_exists",
                    "component": name,
                    "expected_at": f"{gallery_dir}/{kebab}",
                    "fix": f"create gallery page rendering all states of {name}",
                }
            )

    # scan component files for hardcoded values
    for f in component_files:
        if not f.is_file() or f.suffix not in {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".swift"}:
            continue
        # skip the icon files — they're allowed to have inline svg path data
        try:
            rel = f.relative_to(Path.cwd())
            if cfg.icons_path in rel.parents or rel == cfg.icons_path:
                continue
        except ValueError:
            pass

        content = f.read_text(errors="ignore")
        # strip comments roughly
        content_no_comments = re.sub(r"//.*?$|/\*.*?\*/", "", content, flags=re.MULTILINE | re.DOTALL)

        hex_matches = HEX_COLOR.findall(content_no_comments)
        if hex_matches:
            failures.append(
                {
                    "check": "no_hardcoded_hex_colors",
                    "file": str(f),
                    "matches": hex_matches[:5],
                    "fix": "import from tokens module instead of hardcoding hex values",
                }
            )
        if RGBA.search(content_no_comments):
            failures.append(
                {
                    "check": "no_hardcoded_rgba",
                    "file": str(f),
                    "fix": "import from tokens module instead of hardcoding rgba()",
                }
            )

        # px values are common in style props — warn instead of fail
        px_matches = PX_VALUE.findall(content_no_comments)
        if len(px_matches) > 3:
            warnings.append(
                {
                    "check": "px_values_count",
                    "file": str(f),
                    "count": len(px_matches),
                    "note": "many literal px values — verify they come from spacing/radii tokens, not invented",
                }
            )

        # inline svg in non-icon files
        if INLINE_SVG_TAG.search(content_no_comments):
            failures.append(
                {
                    "check": "no_inline_svg_in_components",
                    "file": str(f),
                    "fix": "use icon catalog component instead of inline <svg>",
                }
            )

    ok = len(failures) == 0
    _emit(
        {
            "phase": "build",
            "validator": "components",
            "ok": ok,
            "failures": failures,
            "warnings": warnings,
            "stats": {"components_in_inventory": len(component_names)},
        }
    )
    return 0 if ok else 1


_COMPONENT_NAME_RE = re.compile(r"^\s*[-*]\s*\*?\*?([A-Z][a-zA-Z0-9]+)\*?\*?", re.MULTILINE)


def _extract_component_names(inv_text: str) -> list[str]:
    """Pull PascalCase identifiers from inventory bullets."""
    candidates = set()
    for m in _COMPONENT_NAME_RE.finditer(inv_text):
        candidates.add(m.group(1))
    # also pick up names from inside a state matrix table (first column)
    for line in inv_text.split("\n"):
        if "|" not in line:
            continue
        first_cell = line.strip().strip("|").split("|")[0].strip().strip("*")
        if re.match(r"^[A-Z][a-zA-Z0-9]+$", first_cell):
            candidates.add(first_cell)
    return sorted(candidates)


def _kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
