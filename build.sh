#!/usr/bin/env bash
# Build a portable (green) distribution of CADENCE.
#
# Runtime = Astral python-build-standalone (PBS): a self-contained CPython that
# ships python.exe + stdlib + pip + dynamic tkinter (Tcl/Tk split out since the
# 2025-08-08 release). We pip-install our runtime deps INTO it and copy src/
# res/ docs/ alongside, then zip. The folder is copy-anywhere portable — no base
# Python needed on the target machine.
#
#   Run from git-bash:  bash build.sh            (uses cached download if present)
#                       DOWNLOAD=1 bash build.sh (force re-download)
#
# Output:  dist/cadence-<version>.zip  and  dist/cadence-<version>/  (unzipped)

set -euo pipefail

# ---------------------------------------------------------------------------
# PBS source. Bump PBS_TAG to a newer python-build-standalone release when you
# want a fresher CPython; PBS_PY must stay a 3.14.x so the cp314 wheels in
# requirements.txt (pillow, etc.) resolve. See:
#   https://github.com/astral-sh/python-build-standalone/releases
# ---------------------------------------------------------------------------
PBS_TAG="20260901"
PBS_PY="3.14.7"          # this tag ships CPython 3.14.7 (venv here is 3.14.5 — same ABI, fine)
PBS_TRIPLE="x86_64-pc-windows-msvc"
PBS_FILE="cpython-${PBS_PY}+${PBS_TAG}-${PBS_TRIPLE}-install_only.tar.gz"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${PBS_FILE}"

# ---------------------------------------------------------------------------
# VLC runtime source. python-vlc is only a ctypes binding — it NEEDS a real
# libvlc.dll + plugins to decode audio. Override VLC_SRC to point at any VLC
# 3.x install (e.g. a portable one); the build copies a GUI-free subset into
# the bundle so the target machine needs NO VLC installed.
#   https://github.com/videolan/vlc
# ---------------------------------------------------------------------------
VLC_SRC="${VLC_SRC:-C:/Program Files/VideoLAN/VLC}"
# Paths INSIDE the bundle where the VLC runtime lives.
VLC_DIR="vlc"
VLC_LIB="${VLC_DIR}/libvlc.dll"       # relative to bundle root (env var target)

# ---------------------------------------------------------------------------
# Project paths (script lives in the repo root).
# ---------------------------------------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VERSION="$(sed -n "s/^version = '\([0-9.]*\)'$/\1/p" src/__init__.py)"
if [[ -z "$VERSION" ]]; then
    echo "ERROR: could not read version from src/__init__.py" >&2
    exit 1
fi

DIST="dist/cadence-${VERSION}"
DOWNLOAD_DIR="downloads"
PBS_ARCHIVE="${DOWNLOAD_DIR}/${PBS_FILE}"
RUNTIME="${DIST}/runtime"
ZIP="${DIST}.zip"

# Absolute form of RUNTIME — the pip/python calls happen after `cd` into other
# dirs, so a relative path here would break (step 7 cd's into $DIST first).
RUNTIME_ABS="${ROOT}/${RUNTIME}"

# ---------------------------------------------------------------------------
# 1. Download PBS (cached unless DOWNLOAD=1).
# ---------------------------------------------------------------------------
mkdir -p "$DOWNLOAD_DIR"
if [[ ! -f "$PBS_ARCHIVE" ]] || [[ "${DOWNLOAD:-0}" == "1" ]]; then
    echo ">> Downloading PBS ${PBS_FILE} ..."
    curl -fL --noproxy '*' -o "$PBS_ARCHIVE" "$PBS_URL"
else
    echo ">> PBS archive cached at ${PBS_ARCHIVE} (pass DOWNLOAD=1 to refresh)"
fi

# ---------------------------------------------------------------------------
# 2. Fresh dist folder.
# ---------------------------------------------------------------------------
rm -rf "$DIST"
mkdir -p "$DIST"

# ---------------------------------------------------------------------------
# 3. Extract PBS into runtime/.
#    PBS install_only is a FULL normal layout (no python314._pth pinning), so
#    nothing extra is needed — unlike the python.org embeddable.
# ---------------------------------------------------------------------------
echo ">> Extracting PBS into ${RUNTIME} ..."
mkdir -p "$RUNTIME"
tar -xzf "$PBS_ARCHIVE" -C "$RUNTIME" --strip-components=1
# ---------------------------------------------------------------------------
# 4. Install runtime deps INTO the PBS runtime.
#    PYTHONNOUSERSITE=1 both here and in the launcher: without it pip can
#    "satisfy" deps from the host machine's roaming user-site and never copy
#    them into our site-packages — the bundle then crashes on any other machine.
#    PBS ships pip, but bootstrap via get-pip.py as a fallback.
# ---------------------------------------------------------------------------
PY="$(find "$RUNTIME_ABS" -maxdepth 1 -name 'python*.exe' | sort | head -1)"
if [[ -z "$PY" ]]; then
    echo "ERROR: no python.exe found under ${RUNTIME_ABS}" >&2
    exit 1
fi

if ! PYTHONNOUSERSITE=1 "$PY" -m pip --version >/dev/null 2>&1; then
    echo ">> PBS has no pip — bootstrapping get-pip.py ..."
    curl -fL --noproxy '*' -o "${DOWNLOAD_DIR}/get-pip.py" \
        https://bootstrap.pypa.io/get-pip.py
    PYTHONNOUSERSITE=1 "$PY" "${DOWNLOAD_DIR}/get-pip.py"
fi

echo ">> Installing runtime dependencies into runtime/ ..."
PYTHONNOUSERSITE=1 "$PY" -m pip install --no-warn-script-location \
    -r requirements.txt

# ---------------------------------------------------------------------------
# 5. Copy src/, res/ and user docs into the bundle root; prune __pycache__.
# ---------------------------------------------------------------------------
echo ">> Copying src/, res/, docs into bundle root ..."
cp -r src "$DIST/src"
cp -r res "$DIST/res"
cp README.md CHANGELOG.md LICENSE TODO.md "$DIST/" 2>/dev/null || true
find "$DIST/src" "$DIST/res" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ---------------------------------------------------------------------------
# 5b. Bundle the VLC runtime (GUI-free subset) so the target needs no VLC.
#     python-vlc loads libvlc.dll via PYTHON_VLC_LIB_PATH; libvlc finds its
#     plugins via VLC_PLUGIN_PATH. Only libvlc.dll + libvlccore.dll + plugins/
#     are needed for audio — no vlc.exe, and the gui/ plugin dir (VLC's own
#     interface, ~19MB) is dropped. libvlccore.dll is pulled in automatically
#     because libvlc.dll depends on it and Windows resolves same-dir DLLs.
#     VLC plugins reverse-depend on DLLs in VLC's root, so copy them all to the
#     bundle's vlc/ root too (plugins find their deps via their own dir).
#     VERIFIED 2026-09-04: this exact set plays audio (State.Playing).
# ---------------------------------------------------------------------------
if [[ -f "${VLC_SRC}/libvlc.dll" ]]; then
    echo ">> Bundling VLC runtime from ${VLC_SRC} ..."
    mkdir -p "${DIST}/${VLC_DIR}"
    cp "${VLC_SRC}/libvlc.dll" "${VLC_SRC}/libvlccore.dll" "${DIST}/${VLC_DIR}/"
    cp -r "${VLC_SRC}/plugins" "${DIST}/${VLC_DIR}/"
    rm -rf "${DIST}/${VLC_DIR}/plugins/gui"        # VLC's own GUI — not needed
    # copy any root DLLs the plugins may depend on (all *.dll except the two
    # already copied and the browser plugins axvlc/npvlc)
    for dll in "${VLC_SRC}"/*.dll; do
        name="$(basename "$dll")"
        case "$name" in
            libvlc.dll|libvlccore.dll|axvlc.dll|npvlc.dll) ;;  # skip
            *) cp "$dll" "${DIST}/${VLC_DIR}/" ;;
        esac
    done
else
    echo "WARNING: ${VLC_SRC}/libvlc.dll not found — bundle will have NO VLC" >&2
    echo "         runtime and CANNOT play audio. Set VLC_SRC to a VLC 3.x install." >&2
fi

# ---------------------------------------------------------------------------
# 6. Launcher. `python -m src` reaches cli.py main (src/__main__.py); the
#    backend/hotkey/tray/lyric/dash spawns resolve via sys.executable inside the
#    bundle, so everything stays self-contained. Force CRLF for cmd.
# ---------------------------------------------------------------------------
echo ">> Writing launcher cadence.cmd ..."
cat > "$DIST/cadence.cmd" <<'EOF'
@echo off
cd /d "%~dp0"
set PYTHONNOUSERSITE=1
rem Point python-vlc at the bundled VLC runtime (see build.sh step 5b).
rem PYTHON_VLC_LIB_PATH -> libvlc.dll, so vlc.py's find_lib() succeeds.
rem VLC_PLUGIN_PATH      -> plugins dir, so libvlc can decode. Set directly
rem                        (not via PYTHON_VLC_MODULE_PATH) because the
rem                        setdefault in vlc.py only fires when plugin_path
rem                        was auto-detected — with LIB_PATH it is None.
set "PYTHON_VLC_LIB_PATH=%~dp0vlc\libvlc.dll"
set "VLC_PLUGIN_PATH=%~dp0vlc\plugins"
"%~dp0runtime\python.exe" -m src %*
EOF
sed -i 's/$/\r/' "$DIST/cadence.cmd"

# ---------------------------------------------------------------------------
# 7. Zip it. git-bash has no `zip`; use Python stdlib (zipfile) — present in
#    the bundle runtime AND any system python. Skips __pycache__ while packing.
# ---------------------------------------------------------------------------
echo ">> Zipping ${ZIP} ..."
(cd "$DIST" && PYTHONNOUSERSITE=1 "$(dirname "$PY")/python.exe" - <<'EOF'
import os
import zipfile

root = os.getcwd()
out = os.path.join(os.path.dirname(root), os.path.basename(root) + '.zip')

with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for name in filenames:
            full = os.path.join(dirpath, name)
            arc = os.path.relpath(full, os.path.dirname(root))
            zf.write(full, arc)
print(out)
EOF
)
cd "$ROOT"

echo ""
echo "Done."
echo "  unpacked: ${DIST}"
echo "  zip:      ${ZIP}"
du -sh "$DIST" 2>/dev/null | awk '{print "  size:    "$1}'
echo ""
echo "NOTE: the bundle ships its own VLC runtime (vlc/), so the target needs no"
echo "VLC installed. It still needs the Microsoft Visual C++ 2015+ Redistributable"
echo "(vcruntime140.dll) — neither PBS nor VLC bundle it. Most Windows boxes have it."
