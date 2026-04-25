#!/usr/bin/env bash
# Install FDE skill pack into a target project.
#
# Local:  ./install.sh /path/to/your/project
# Remote: bash <(curl -fsSL https://raw.githubusercontent.com/tarsai/fde-bootstrap/main/install.sh) .

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 /path/to/your/project"
  exit 1
fi

TARGET="$(cd "$1" && pwd)"
REMOTE_BASE="https://raw.githubusercontent.com/tarsai/fde-bootstrap/main"

# Detect whether we are running from a real file or a file descriptor (curl pipe)
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$SOURCE" == /dev/fd* ]] || [ ! -f "$SOURCE/fde/lib/config.py" ]; then
  REMOTE=true
else
  REMOTE=false
fi

if [ ! -d "$TARGET" ]; then
  echo "ERROR: target directory does not exist: $TARGET"
  exit 1
fi

echo "Installing FDE skill pack into: $TARGET"
echo "Mode: $([ "$REMOTE" = true ] && echo "remote (downloading from GitHub)" || echo "local")"
echo

# Helper: copy a file from local source or download from GitHub
install_file() {
  local rel="$1"   # path relative to repo root
  local dst="$2"   # absolute destination path
  if [ "$REMOTE" = true ]; then
    curl -fsSL "$REMOTE_BASE/$rel" -o "$dst"
  else
    cp "$SOURCE/$rel" "$dst"
  fi
}

# 1. .claude directory — commands and hooks
mkdir -p "$TARGET/.claude/commands" "$TARGET/.claude/hooks"

for f in fde-extract.md fde-build.md fde-assemble.md fde-approve.md fde-status.md; do
  if [ -f "$TARGET/.claude/commands/$f" ]; then
    cp "$TARGET/.claude/commands/$f" "$TARGET/.claude/commands/$f.bak.$(date +%s)"
    echo "  backed up existing: .claude/commands/$f"
  fi
  install_file ".claude/commands/$f" "$TARGET/.claude/commands/$f"
done

for f in stop-extract.py stop-build.py stop-assemble.py; do
  if [ -f "$TARGET/.claude/hooks/$f" ]; then
    cp "$TARGET/.claude/hooks/$f" "$TARGET/.claude/hooks/$f.bak.$(date +%s)"
    echo "  backed up existing: .claude/hooks/$f"
  fi
  install_file ".claude/hooks/$f" "$TARGET/.claude/hooks/$f"
  chmod +x "$TARGET/.claude/hooks/$f"
done

# 2. fde directory — validators, lib, templates
mkdir -p "$TARGET/fde/validators" "$TARGET/fde/lib" "$TARGET/fde/templates"

for f in __init__.py validate_tokens.py validate_icons.py validate_copy.py \
         validate_inventory.py validate_components.py validate_screen_plan.py validate_screens.py; do
  install_file "fde/validators/$f" "$TARGET/fde/validators/$f"
done

for f in __init__.py config.py state.py source_parser.py; do
  install_file "fde/lib/$f" "$TARGET/fde/lib/$f"
done

install_file "fde/templates/config.yaml.template" "$TARGET/fde/templates/config.yaml.template"
install_file "fde/settings.json" "$TARGET/fde/settings.json"

# 3. .fde directory — state + config (only if not already present)
mkdir -p "$TARGET/.fde/reports"
if [ ! -f "$TARGET/.fde/config.yaml" ]; then
  cp "$TARGET/fde/templates/config.yaml.template" "$TARGET/.fde/config.yaml"
  echo "  wrote: .fde/config.yaml (EDIT THIS BEFORE RUNNING /fde-extract)"
else
  echo "  preserved existing: .fde/config.yaml"
fi

# 4. hooks settings — wire stop hooks to slash commands via .claude/settings.local.json
#
# Stop hooks are guarded by .fde/active — they are no-ops in normal sessions and only
# run when you explicitly activate them via /fde-extract, /fde-build, or /fde-assemble.
# The hook config also lives in fde/settings.json for reference.
SETTINGS="$TARGET/.claude/settings.local.json"
HOOK_JSON='{
  "hooks": {
    "Stop": [
      {
        "matcher": "fde-extract",
        "hooks": [{ "type": "command", "command": "python3 .claude/hooks/stop-extract.py" }]
      },
      {
        "matcher": "fde-build",
        "hooks": [{ "type": "command", "command": "python3 .claude/hooks/stop-build.py" }]
      },
      {
        "matcher": "fde-assemble",
        "hooks": [{ "type": "command", "command": "python3 .claude/hooks/stop-assemble.py" }]
      }
    ]
  }
}'

if [ ! -f "$SETTINGS" ]; then
  echo "$HOOK_JSON" > "$SETTINGS"
  echo "  wrote: .claude/settings.local.json (hook wiring)"
else
  REFERENCE="$TARGET/.claude/settings.fde-hooks.json"
  echo "$HOOK_JSON" > "$REFERENCE"
  echo "  WARNING: .claude/settings.local.json already exists."
  echo "  Hook config written to: .claude/settings.fde-hooks.json"
  echo "  Merge with: python3 -c \\"
  echo "    \"import json,pathlib; s=json.loads(pathlib.Path('.claude/settings.local.json').read_text()); h=json.loads(pathlib.Path('.claude/settings.fde-hooks.json').read_text()); s.setdefault('hooks',{}).setdefault('Stop',[]).extend(h['hooks']['Stop']); pathlib.Path('.claude/settings.local.json').write_text(json.dumps(s,indent=2))\""
fi

# 5. .gitignore additions
GI="$TARGET/.gitignore"
if [ -f "$GI" ]; then
  if ! grep -q "^\.fde/reports/" "$GI" 2>/dev/null; then
    printf "\n# FDE skill pack — reports are local review artifacts\n.fde/reports/\n" >> "$GI"
    echo "  appended to .gitignore"
  fi
else
  printf "# FDE skill pack — reports are local review artifacts\n.fde/reports/\n" > "$GI"
  echo "  wrote: .gitignore"
fi

# 6. python deps check
echo
echo "Checking Python dependencies..."
MISSING=""
for mod in yaml bs4 cssutils; do
  if ! python3 -c "import $mod" 2>/dev/null; then
    MISSING="$MISSING $mod"
  fi
done

if [ -n "$MISSING" ]; then
  echo "  MISSING:$MISSING"
  echo "  install with: pip install pyyaml beautifulsoup4 cssutils markdown-it-py"
else
  echo "  all present"
fi

echo
echo "Install complete."
echo
echo "Next steps:"
echo "  1. Edit .fde/config.yaml — fill in your project paths and target stack"
echo "  2. In Claude Code: /fde-extract"
echo
