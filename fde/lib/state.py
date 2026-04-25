"""Phase approval state ledger. Tracks which phases have passed validators + human approval."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
from typing import Literal

STATE_PATH = Path(".fde/state.json")

Phase = Literal["extract", "build", "assemble"]
PHASES: tuple[Phase, ...] = ("extract", "build", "assemble")


@dataclass
class PhaseRecord:
    phase: Phase
    validators_passed_at: str | None = None
    approved_at: str | None = None
    commit_sha: str | None = None
    report_path: str | None = None


@dataclass
class State:
    extract: PhaseRecord
    build: PhaseRecord
    assemble: PhaseRecord

    @classmethod
    def empty(cls) -> "State":
        return cls(
            extract=PhaseRecord(phase="extract"),
            build=PhaseRecord(phase="build"),
            assemble=PhaseRecord(phase="assemble"),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state(root: Path | None = None) -> State:
    root = root or Path.cwd()
    f = root / STATE_PATH
    if not f.exists():
        return State.empty()

    raw = json.loads(f.read_text())
    return State(
        extract=PhaseRecord(**raw.get("extract", {"phase": "extract"})),
        build=PhaseRecord(**raw.get("build", {"phase": "build"})),
        assemble=PhaseRecord(**raw.get("assemble", {"phase": "assemble"})),
    )


def save_state(state: State, root: Path | None = None) -> None:
    root = root or Path.cwd()
    f = root / STATE_PATH
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(asdict(state), indent=2, sort_keys=True))


def mark_validators_passed(phase: Phase) -> None:
    s = load_state()
    rec: PhaseRecord = getattr(s, phase)
    rec.validators_passed_at = _now()
    save_state(s)


def mark_approved(phase: Phase, commit_sha: str | None, report_path: str | None) -> None:
    s = load_state()
    rec: PhaseRecord = getattr(s, phase)
    rec.approved_at = _now()
    rec.commit_sha = commit_sha
    rec.report_path = report_path
    save_state(s)


def require_prior_approved(current: Phase) -> None:
    """Exit non-zero if any prior phase isn't approved. Used at the start of each phase command."""
    s = load_state()
    idx = PHASES.index(current)
    for prior in PHASES[:idx]:
        rec: PhaseRecord = getattr(s, prior)
        if not rec.approved_at:
            print(
                f"ERROR: cannot run /fde-{current} — prior phase /fde-{prior} not approved.\n"
                f"Run /fde-{prior} first, then /fde-approve.",
                file=sys.stderr,
            )
            sys.exit(3)


def current_unapproved_phase() -> Phase | None:
    """Returns the next phase that needs approval, or None if all approved."""
    s = load_state()
    for p in PHASES:
        rec: PhaseRecord = getattr(s, p)
        if rec.validators_passed_at and not rec.approved_at:
            return p
    return None
