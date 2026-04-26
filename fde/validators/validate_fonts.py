"""Validate font loading completeness against the design source.

Compares the Google Fonts URL in the design file against the project's font CSS file
and checks that every family, variable axis, and weight is present.

Exit codes:
  0 = pass
  1 = fail (with structured JSON report on stdout)
  2 = config / setup error (font_css_path not configured or files missing)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fde.lib.config import load_config  # noqa: E402


@dataclass
class FontSpec:
    family: str
    axes: set[str] = field(default_factory=set)
    discrete_weights: set[int] = field(default_factory=set)
    weight_ranges: list[tuple[int, int]] = field(default_factory=list)

    def covers_weight(self, w: int) -> bool:
        return w in self.discrete_weights or any(lo <= w <= hi for lo, hi in self.weight_ranges)

    def covers_range(self, lo: int, hi: int) -> bool:
        return any(plo <= lo and phi >= hi for plo, phi in self.weight_ranges)


_GFONTS_RE = re.compile(
    r'https://fonts\.googleapis\.com/css2\?[^\s\'"<>)\]]+',
    re.IGNORECASE,
)


def find_font_urls(text: str) -> list[str]:
    return _GFONTS_RE.findall(text)


def parse_google_fonts_url(url: str) -> tuple[list[FontSpec], bool]:
    """Return (list of FontSpec, has_display_swap)."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    has_swap = qs.get("display", [""])[0].lower() in {"swap", "optional", "fallback"}
    specs: list[FontSpec] = []
    for param in qs.get("family", []):
        specs.append(_parse_family_param(param))
    return specs, has_swap


def _parse_family_param(param: str) -> FontSpec:
    if ":" not in param:
        return FontSpec(family=param.replace("+", " "))

    family_raw, spec_part = param.split(":", 1)
    family = family_raw.replace("+", " ")

    if "@" not in spec_part:
        return FontSpec(family=family, axes=set(spec_part.split(",")) if spec_part else set())

    axes_str, values_str = spec_part.split("@", 1)
    axes = [a for a in axes_str.split(",") if a]
    spec = FontSpec(family=family, axes=set(axes))

    if not axes:
        return spec

    value_tuples = values_str.split(";")

    if len(axes) == 1:
        axis = axes[0]
        for val in value_tuples:
            _absorb_value(spec, axis, val.strip())
    else:
        for tuple_str in value_tuples:
            vals = tuple_str.split(",")
            for i, axis in enumerate(axes):
                if i < len(vals):
                    _absorb_value(spec, axis, vals[i].strip())

    return spec


def _absorb_value(spec: FontSpec, axis: str, val: str) -> None:
    """Record a weight value or range for the wght axis (other axes tracked by presence only)."""
    if axis != "wght":
        return
    if ".." in val:
        parts = val.split("..", 1)
        try:
            spec.weight_ranges.append((int(parts[0]), int(parts[1])))
        except ValueError:
            pass
    else:
        try:
            spec.discrete_weights.add(int(val))
        except ValueError:
            pass


def _find_spec(family: str, specs: list[FontSpec]) -> FontSpec | None:
    for s in specs:
        if s.family.lower() == family.lower():
            return s
    return None


def main() -> int:
    cfg = load_config()

    if not cfg.font_css_path:
        print(
            json.dumps({
                "phase": "extract",
                "validator": "fonts",
                "ok": True,
                "skipped": True,
                "reason": "font_css_path not set in config — add it to enable font validation",
            }, indent=2)
        )
        return 2  # config/setup gap — not a hard failure

    if not cfg.primary_design_file.exists():
        _emit({"phase": "extract", "validator": "fonts", "ok": False,
               "failures": [{"check": "design_file_exists",
                              "path": str(cfg.primary_design_file)}]})
        return 2

    if not cfg.font_css_path.exists():
        _emit({"phase": "extract", "validator": "fonts", "ok": False,
               "failures": [{"check": "font_css_path_exists",
                              "path": str(cfg.font_css_path),
                              "fix": f"create {cfg.font_css_path} containing your Google Fonts @import"}]})
        return 1

    design_text = cfg.primary_design_file.read_text(encoding="utf-8")
    project_text = cfg.font_css_path.read_text(encoding="utf-8")

    design_urls = find_font_urls(design_text)
    if not design_urls:
        _emit({"phase": "extract", "validator": "fonts", "ok": True,
               "skipped": True,
               "reason": "no Google Fonts URL found in design source — nothing to validate against"})
        return 0

    project_urls = find_font_urls(project_text)

    # parse design
    design_specs: list[FontSpec] = []
    design_has_swap = False
    for url in design_urls:
        specs, swap = parse_google_fonts_url(url)
        design_specs.extend(specs)
        design_has_swap = design_has_swap or swap

    # parse project
    project_specs: list[FontSpec] = []
    project_has_swap = False
    for url in project_urls:
        specs, swap = parse_google_fonts_url(url)
        project_specs.extend(specs)
        project_has_swap = project_has_swap or swap

    failures: list[dict] = []

    # display=swap check
    if design_has_swap and not project_has_swap:
        failures.append({
            "check": "display_swap_missing",
            "fix": "add display=swap (or display=optional) to the Google Fonts URL in "
                   f"{cfg.font_css_path}",
        })

    for ds in design_specs:
        ps = _find_spec(ds.family, project_specs)

        if ps is None:
            failures.append({
                "check": "family_missing",
                "family": ds.family,
                "fix": f"add font family '{ds.family}' to {cfg.font_css_path}",
            })
            continue

        # axes check
        missing_axes = ds.axes - ps.axes
        if missing_axes:
            failures.append({
                "check": "axes_missing",
                "family": ds.family,
                "missing_axes": sorted(missing_axes),
                "design_axes": sorted(ds.axes),
                "project_axes": sorted(ps.axes),
                "fix": (
                    f"'{ds.family}': add variable axes {sorted(missing_axes)} "
                    f"to the font URL in {cfg.font_css_path}"
                ),
            })

        # discrete weight checks
        for w in sorted(ds.discrete_weights):
            if not ps.covers_weight(w):
                failures.append({
                    "check": "weight_missing",
                    "family": ds.family,
                    "weight": w,
                    "fix": (
                        f"'{ds.family}': weight {w} is in the design but not loaded "
                        f"in {cfg.font_css_path}"
                    ),
                })

        # range checks
        for lo, hi in ds.weight_ranges:
            if not ps.covers_range(lo, hi):
                failures.append({
                    "check": "weight_range_too_narrow",
                    "family": ds.family,
                    "design_range": [lo, hi],
                    "project_ranges": [list(r) for r in ps.weight_ranges],
                    "fix": (
                        f"'{ds.family}': design loads wght {lo}..{hi} but project "
                        f"does not fully cover this range in {cfg.font_css_path}"
                    ),
                })

    ok = len(failures) == 0
    _emit({
        "phase": "extract",
        "validator": "fonts",
        "ok": ok,
        "failures": failures,
        "stats": {
            "design_families": len(design_specs),
            "project_families": len(project_specs),
            "design_urls_found": len(design_urls),
        },
    })
    return 0 if ok else 1


def _emit(report: dict) -> None:
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
