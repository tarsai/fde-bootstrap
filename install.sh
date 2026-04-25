#!/usr/bin/env bash
# Install FDE skill pack into a target project.
# Usage: ./install.sh /path/to/your/project

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 /path/to/your/project"
  exit 1
fi

TARGET="$1"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$TARGET" ]; then
  echo "ERROR: target directory does not exist: $TARGET"
  exit 1
fi

echo "Installing FDE skill pack into: $TARGET"
echo "Source: $SOURCE"
echo

# 1. .claude directory — commands and hooks
mkdir -p "$TARGET/.claude/commands" "$TARGET/.claude/hooks"

# back up existing commands if they have name collisions
for f in fde-extract.md fde-build.md fde-assemble.md fde-approve.md; do
  if [ -f "$TARGET/.claude/commands/$f" ]; then
    cp "$TARGET/.claude/commands/$f" "$TARGET/.claude/commands/$f.bak.$(date +%s)"
    echo "  backed up existing: .claude/commands/$f"
  fi
  cp "$SOURCE/.claude/commands/$f" "$TARGET/.claude/commands/$f"
done

for f in stop-extract.py stop-build.py stop-assemble.py; do
  if [ -f "$TARGET/.claude/hooks/$f" ]; then
    cp "$TARGET/.claude/hooks/$f" "$TARGET/.claude/hooks/$f.bak.$(date +%s)"
    echo "  backed up existing: .claude/hooks/$f"
  fi
  cp "$SOURCE/.claude/hooks/$f" "$TARGET/.claude/hooks/$f"
  chmod +x "$TARGET/.claude/hooks/$f"
done

# 2. fde directory — validators and lib
mkdir -p "$TARGET/fde/validators" "$TARGET/fde/lib" "$TARGET/fde/templates"
cp "$SOURCE/fde/validators/"*.py "$TARGET/fde/validators/"
cp "$SOURCE/fde/lib/"*.py "$TARGET/fde/lib/"
cp "$SOURCE/fde/templates/"* "$TARGET/fde/templates/"

# 3. .fde directory — state + config (only if not already present)
mkdir -p "$TARGET/.fde/reports"
if [ ! -f "$TARGET/.fde/config.yaml" ]; then
  cp "$SOURCE/fde/templates/config.yaml.template" "$TARGET/.fde/config.yaml"
  echo "  wrote: .fde/config.yaml (EDIT THIS BEFORE RUNNING /fde-extract)"
else
  echo "  preserved existing: .fde/config.yaml"
fi

# 4. hooks settings — wire stop hooks to slash commands via .claude/settings.local.json
#
# Stop hooks are guarded by .fde/active — they are no-ops in normal sessions and only
# run when you explicitly activate them via /fde-extract, /fde-build, or /fde-assemble.
# The hook config lives in fde/settings.json for reference.
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
  # Write the hook config as a reference file next to the existing settings
  REFERENCE="$TARGET/.claude/settings.fde-hooks.json"
  echo "$HOOK_JSON" > "$REFERENCE"
  echo "  WARNING: .claude/settings.local.json already exists."
  echo "  Hook config written to: .claude/settings.fde-hooks.json"
  echo "  Merge the 'hooks.Stop' entries from that file into your settings.local.json."
  echo "  Or run: python3 -c \""
  echo "    import json, pathlib"
  echo "    s = json.loads(pathlib.Path('.claude/settings.local.json').read_text())"
  echo "    h = json.loads(pathlib.Path('.claude/settings.fde-hooks.json').read_text())"
  echo "    s.setdefault('hooks', {}).setdefault('Stop', []).extend(h['hooks']['Stop'])"
  echo "    pathlib.Path('.claude/settings.local.json').write_text(json.dumps(s, indent=2))"
  echo "  \""
fi

# 5. .gitignore additions
GI="$TARGET/.gitignore"
if [ -f "$GI" ]; then
  if ! grep -q "^\.fde/reports/" "$GI" 2>/dev/null; then
    echo "" >> "$GI"
    echo "# FDE skill pack — reports are local review artifacts" >> "$GI"
    echo ".fde/reports/" >> "$GI"
    echo "  appended to .gitignore"
  fi
else
  cat > "$GI" <<'EOF'
# FDE skill pack — reports are local review artifacts
.fde/reports/
EOF
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
echo "  1. cd $TARGET"
echo "  2. Edit .fde/config.yaml — fill in your project paths and target stack"
echo "  3. In Claude Code: /fde-extract"
echo
