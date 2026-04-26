"""Config loading + path resolution. Used by validators and hooks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sys

import yaml

# Maps lowercase substrings in target_stack to npm package names that must exist.
# Only frameworks/libraries we can unambiguously detect are listed here.
_STACK_KEYWORD_PACKAGES: list[tuple[str, list[str]]] = [
    ("next.js", ["next"]),
    ("next",    ["next"]),
    ("expo",    ["expo"]),
    ("react native", ["react-native"]),
    ("react-native", ["react-native"]),
    ("nativewind",   ["nativewind"]),
    ("tailwind",     ["tailwindcss"]),
    ("shadcn",       ["@radix-ui/react-slot"]),
    ("vite",         ["vite"]),
    ("remix",        ["@remix-run/react"]),
    ("gatsby",       ["gatsby"]),
    ("svelte",       ["svelte"]),
    ("nuxt",         ["nuxt"]),
    ("vue",          ["vue"]),
    ("angular",      ["@angular/core"]),
]


CONFIG_PATH = Path(".fde/config.yaml")


@dataclass
class FdeConfig:
    primary_design_file: Path
    context_docs: list[Path]
    target_stack: str
    component_lib_path: Path
    tokens_path: Path
    icons_path: Path
    copy_path: Path
    dev_gallery_route: str
    app_routes_path: Path
    runtime_primitives: str
    theme_mode: str  # single | light+dark | multi-theme
    git_commit_on_approve: bool
    git_branch_per_phase: bool
    font_css_path: Path | None = None

    @property
    def tokens_diff_path(self) -> Path:
        return self.tokens_path.parent / "tokens.diff.md"

    @property
    def icons_diff_path(self) -> Path:
        return self.icons_path / "icons.diff.md"

    @property
    def copy_diff_path(self) -> Path:
        return self.copy_path.parent / "copy.diff.md"

    @property
    def icons_catalog_path(self) -> Path:
        return self.icons_path / "catalog.md"

    @property
    def inventory_path(self) -> Path:
        return self.component_lib_path / "INVENTORY.md"

    @property
    def screen_plan_path(self) -> Path:
        return self.component_lib_path / "SCREEN_PLAN.md"


def load_config(root: Path | None = None) -> FdeConfig:
    root = root or Path.cwd()
    cfg_file = root / CONFIG_PATH
    if not cfg_file.exists():
        print(
            f"ERROR: {cfg_file} not found. Did you run install.sh and edit config.yaml?",
            file=sys.stderr,
        )
        sys.exit(2)

    with cfg_file.open() as f:
        raw = yaml.safe_load(f)

    target_stack = raw.get("target_stack", "").strip()
    if not target_stack:
        print(
            "ERROR: target_stack is not set in .fde/config.yaml.\n"
            "  Describe your project's actual stack before running /fde-extract.\n"
            "  Example: target_stack: Expo Router + NativeWind",
            file=sys.stderr,
        )
        sys.exit(2)

    return FdeConfig(
        primary_design_file=Path(raw["primary_design_file"]),
        context_docs=[Path(p) for p in raw.get("context_docs", [])],
        target_stack=target_stack,
        component_lib_path=Path(raw["component_lib_path"]),
        tokens_path=Path(raw["tokens_path"]),
        icons_path=Path(raw["icons_path"]),
        copy_path=Path(raw["copy_path"]),
        dev_gallery_route=raw["dev_gallery_route"],
        app_routes_path=Path(raw["app_routes_path"]),
        runtime_primitives=raw["runtime_primitives"],
        theme_mode=raw["theme_mode"],
        git_commit_on_approve=raw.get("git_commit_on_approve", True),
        git_branch_per_phase=raw.get("git_branch_per_phase", False),
        font_css_path=Path(raw["font_css_path"]) if raw.get("font_css_path") else None,
    )


def validate_stack_vs_deps(config: FdeConfig, root: Path | None = None) -> list[dict]:
    """Cross-check target_stack keywords against package.json.

    Returns a list of mismatch dicts (empty = all clear).
    Each dict has keys: keyword, expected_packages, fix.
    """
    root = root or Path.cwd()
    pkg_path = root / "package.json"

    if not pkg_path.exists():
        return []  # no package.json — non-JS project, skip check

    try:
        pkg = json.loads(pkg_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    all_deps: set[str] = set()
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        all_deps.update(pkg.get(section, {}).keys())

    stack_lower = config.target_stack.lower()
    mismatches: list[dict] = []

    for keyword, expected_packages in _STACK_KEYWORD_PACKAGES:
        if keyword not in stack_lower:
            continue
        if not any(p in all_deps for p in expected_packages):
            mismatches.append(
                {
                    "keyword": keyword,
                    "expected_packages": expected_packages,
                    "fix": (
                        f"target_stack mentions '{keyword}' but none of "
                        f"{expected_packages} found in package.json. "
                        "Update target_stack in .fde/config.yaml to match your actual stack."
                    ),
                }
            )

    return mismatches
