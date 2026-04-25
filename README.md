# FDE Skill Pack

> Front-end Design Engineer agent for Claude Code. Converts a Claude Design handoff (or any HTML/CSS design source) into pixel-perfect code through three mechanically-gated phases.

## What this is

A project-scoped skill pack that adds four slash commands and a set of Python validators to your repo. The agent extracts design tokens, builds components, and assembles screens — but cannot advance between phases without passing automated validators **and** explicit human approval.

The methodology behind this is documented in [`docs/methodology.md`](docs/methodology.md). The skill pack is the executable form.

## Why mechanical gates

Without enforcement, an LLM coding agent will:

- invent colors that "look close enough"
- skip states the design didn't show
- inline styles in screen files instead of fixing components
- silently resolve design ambiguities

Stop hooks + validators turn the methodology's "definition of approved" prose into executable checks. Claude literally cannot exit Phase 1 with a missing token row in `tokens.diff.md`.

## Install

```bash
gh repo clone <your-fork>/fde-skill-pack
cd fde-skill-pack
./install.sh /path/to/your/project
cd /path/to/your/project
```

This copies `.claude/commands/`, `.claude/hooks/`, and `fde/` into your project. It does NOT modify your existing code.

## Configure

After install, edit `.fde/config.yaml`:

```yaml
primary_design_file: design/wireframes.html
context_docs:
  - docs/handoff.md
  - docs/system-design.md
target_stack: Expo Router + NativeWind
component_lib_path: packages/ui/src
tokens_path: packages/design-tokens/src/tokens.ts
icons_path: packages/ui/src/icons
copy_path: packages/copy/src/strings.ts
dev_gallery_route: /(dev)/components/
app_routes_path: app/
runtime_primitives: View, Text, Pressable
theme_mode: single  # single | light+dark | multi-theme
```

## Use

```
/fde-extract     # Phase 1: tokens + icons + copy
/fde-approve     # validates + commits + records approval
/fde-build       # Phase 2: components with state matrix
/fde-approve
/fde-assemble    # Phase 3: screen assembly
/fde-approve

/fde-status      # read-only — show pipeline state, next action, drift warnings
```

Each `/fde-*` command refuses to run if the previous phase isn't approved. Approval requires validators to pass.

`/fde-status` is safe to run anytime — useful when context-switching between projects or returning after a break.

## What "validator pass" means vs "human approval"

Validators are diff-based and mechanical:

- every CSS variable in source is mapped in tokens module
- every `<svg>` in source has an icon catalog entry
- INVENTORY.md state matrix has zero blank cells
- screen files contain zero hardcoded colors or string literals

Things validators CANNOT check (and where you come in):

- visual fidelity at 100% zoom
- typography rendering on actual fonts
- transition timing feels right
- accessibility flow with keyboard

Each `/fde-approve` run produces a structured human-checklist for the parts machines can't verify. You either approve via the command or paste deltas.

## Repo structure

```
fde-skill-pack/
├── .claude/
│   ├── commands/         # slash command definitions
│   │   ├── fde-extract.md
│   │   ├── fde-build.md
│   │   ├── fde-assemble.md
│   │   ├── fde-approve.md
│   │   └── fde-status.md
│   └── hooks/            # stop hooks per phase
│       ├── stop-extract.py
│       ├── stop-build.py
│       └── stop-assemble.py
├── fde/
│   ├── validators/       # python diff-based validators
│   │   ├── validate_tokens.py
│   │   ├── validate_icons.py
│   │   ├── validate_copy.py
│   │   ├── validate_inventory.py
│   │   ├── validate_components.py
│   │   ├── validate_screen_plan.py
│   │   └── validate_screens.py
│   ├── templates/
│   │   └── config.yaml.template
│   └── lib/              # shared utilities
│       ├── config.py
│       ├── state.py
│       └── source_parser.py
├── docs/
│   └── methodology.md
├── install.sh
└── README.md
```

After install, your project gets:

```
your-project/
├── .claude/              # commands + hooks
├── fde/                  # validators + lib
└── .fde/
    ├── config.yaml       # filled in by you
    ├── state.json        # phase approval ledger
    └── reports/          # phase reports for review
```

## Requirements

- Python 3.10+
- `pip install beautifulsoup4 cssutils pyyaml markdown-it-py`
- `git` (for commit-on-approve)
- Claude Code with slash commands and hooks support

## Status

v0.1 — usable but expect rough edges. Validators are intentionally strict; loosen by editing the validator files in your project, not by working around them.
