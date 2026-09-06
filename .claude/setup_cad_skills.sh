#!/usr/bin/env bash
# Environment setup for the text-to-cad skills in .claude/skills (cad, cad-viewer, dxf,
# step-parts, dfam-check, ...). Idempotent; safe to run at every session start.
#
#  1. installs the pinned `cadgen` runtime (build123d kernel + STEP/DXF/mesh doors + viewer)
#     and the mesh libraries the DfAM tool needs;
#  2. makes the pre-installed Playwright Chromium visible under the browser revision the
#     installed Playwright expects, so `cadgen ... snapshot` can render without downloading
#     a browser (the remote sandbox forbids `playwright install`).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"

if ! "$PY" -c "import cadgen" 2>/dev/null; then
  "$PY" -m pip install --quiet -r "$HERE/skills/cad/requirements.txt" 2>&1 | grep -v "WARNING: Running pip" || true
fi
if ! "$PY" -c "import trimesh, rtree, scipy, networkx, lxml" 2>/dev/null; then
  "$PY" -m pip install --quiet -r "$HERE/skills/dfam-check/requirements.txt" 2>&1 | grep -v "WARNING: Running pip" || true
fi

# cadgen pulls in cadquery-ocp-novtk + a proxy package that shadows the full OCP build CadQuery needs
# (cad/*/model.py are CadQuery). Keep the full build in front.
if ! "$PY" -c "import cadquery" 2>/dev/null; then
  "$PY" -m pip uninstall -y -q cadquery-ocp-proxy cadquery-ocp-novtk 2>/dev/null || true
  "$PY" -m pip install --quiet --force-reinstall --no-deps "cadquery-ocp==7.9.3.1.1" 2>&1 | grep -v "WARNING: Running pip" || true
fi

# --- Playwright browser alias -------------------------------------------------------------
PWB="${PLAYWRIGHT_BROWSERS_PATH:-/opt/pw-browsers}"
if [ -d "$PWB" ] && [ -w "$PWB" ]; then
  want="$("$PY" - <<'EOF' 2>/dev/null
import json, pathlib, playwright
p = pathlib.Path(playwright.__file__).parent / "driver" / "package" / "browsers.json"
d = json.loads(p.read_text())
rev = {b["name"]: b["revision"] for b in d["browsers"]}
print(rev.get("chromium-headless-shell", ""), rev.get("chromium", ""))
EOF
)"
  set -- $want
  hs_rev="${1:-}"; ch_rev="${2:-}"
  have_hs="$(ls -d "$PWB"/chromium_headless_shell-[0-9]* 2>/dev/null | grep -v -- "-${hs_rev}\$" | head -1)"
  have_ch="$(ls -d "$PWB"/chromium-[0-9]* 2>/dev/null | grep -v -- "-${ch_rev}\$" | head -1)"
  if [ -n "$hs_rev" ] && [ -n "$have_hs" ] && [ ! -e "$PWB/chromium_headless_shell-$hs_rev" ]; then
    src="$have_hs/chrome-linux"
    dst="$PWB/chromium_headless_shell-$hs_rev/chrome-headless-shell-linux64"
    mkdir -p "$dst"
    [ -e "$src/chrome-headless-shell" ] || ln -sfn "$src/headless_shell" "$src/chrome-headless-shell"
    for f in "$src"/*; do ln -sfn "$f" "$dst/"; done
    touch "$PWB/chromium_headless_shell-$hs_rev/INSTALLATION_COMPLETE"
    echo "[cad-skills] aliased $(basename "$have_hs") as chromium_headless_shell-$hs_rev"
  fi
  if [ -n "$ch_rev" ] && [ -n "$have_ch" ] && [ ! -e "$PWB/chromium-$ch_rev" ]; then
    mkdir -p "$PWB/chromium-$ch_rev"
    ln -sfn "$have_ch/chrome-linux" "$PWB/chromium-$ch_rev/chrome-linux"
    touch "$PWB/chromium-$ch_rev/INSTALLATION_COMPLETE"
    echo "[cad-skills] aliased $(basename "$have_ch") as chromium-$ch_rev"
  fi
fi

command -v cadgen >/dev/null 2>&1 && echo "[cad-skills] $(cadgen --version 2>/dev/null) ready" || echo "[cad-skills] cadgen not on PATH (use: $PY -m cadgen.cli)"

# --- CAD folder synchronization check (see CLAUDE.md) ------------------------------------
# Every component folder under cad/ must match the last `python cad/build.py` run. A failing check
# means a model or cad/common changed without a full rebuild: run the build and commit the result.
if [ -f "$HERE/../cad/build.py" ]; then
  "$PY" "$HERE/../cad/build.py" --check || true
fi
exit 0
