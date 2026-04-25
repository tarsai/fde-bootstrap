"""Config loading + path resolution. Used by validators and hooks."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import yaml


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

    return FdeConfig(
        primary_design_file=Path(raw["primary_design_file"]),
        context_docs=[Path(p) for p in raw.get("context_docs", [])],
        target_stack=raw["target_stack"],
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
    )
