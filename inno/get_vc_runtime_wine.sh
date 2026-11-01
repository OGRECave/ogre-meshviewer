#!/bin/sh

# Wine-specific extraction of the Microsoft VC++ runtime DLLs.
#
# This is called by inno/get_vc_runtime.sh when building on a non-Windows host.
# It installs the official vc_redist.x64.exe into a throw-away Wine prefix and
# copies the DLLs out for app-local deployment.
#
# Usage:
#   ./inno/get_vc_runtime_wine.sh [output-dir]
#
# Environment:
#   WINE           Wine binary to use (default: wine)
#   VCREDIST_URL   override the redistributable download URL

set -e

SCRIPT=$(readlink -f "$0" 2>/dev/null || echo "$0")
cd "$(dirname "$SCRIPT")/.."

if [ "$1" = "--under-xvfb" ]; then
    shift
    UNDER_XVFB=1
fi

TARGET=${1:-winpkg/vcruntime-x64}
DLLS="msvcp140.dll msvcp140_1.dll msvcp140_2.dll msvcp140_atomic_wait.dll
      msvcp140_codecvt_ids.dll vcruntime140.dll vcruntime140_1.dll
      vcruntime140_threads.dll concrt140.dll"

mkdir -p "$TARGET"

VCREDIST_URL=${VCREDIST_URL:-https://aka.ms/vs/17/release/vc_redist.x64.exe}
REDIST=$(pwd)/winpkg/vc_redist.x64.exe
PREFIX=$(pwd)/winpkg/.vcredist-wine

mkdir -p winpkg
[ -f "$REDIST" ] || curl -L "$VCREDIST_URL" -o "$REDIST"

if [ ! -f "$PREFIX/drive_c/windows/system32/msvcp140.dll" ]; then
    WINE=${WINE:-wine}
    if ! command -v "$WINE" >/dev/null 2>&1; then
        echo "$WINE not found; set VCRUNTIME_DIR or install Wine" >&2
        exit 1
    fi

    # Wine needs a display. Re-exec under one Xvfb instance so wineboot and the
    # redistributable installer share the same display.
    if [ -z "$UNDER_XVFB" ] && [ -z "$DISPLAY" ] && command -v xvfb-run >/dev/null 2>&1; then
        exec xvfb-run -a "$SCRIPT" --under-xvfb "$TARGET"
    fi

    echo "Setting up a temporary Wine prefix for the VC++ runtime..." >&2
    WINEPREFIX=$PREFIX WINEDEBUG=-all "$WINE" wineboot -i
    WINEPREFIX=$PREFIX WINEDEBUG=-all "$WINE" "$REDIST" /install /quiet /norestart
fi

SRC=$PREFIX/drive_c/windows/system32
for dll in $DLLS; do
    if [ -f "$SRC/$dll" ]; then
        cp "$SRC/$dll" "$TARGET/"
    fi
done
chmod 644 "$TARGET"/*.dll 2>/dev/null || true

if [ ! -f "$TARGET/msvcp140.dll" ] || [ ! -f "$TARGET/vcruntime140.dll" ]; then
    echo "could not find the VC++ runtime DLLs in '$SRC'" >&2
    exit 1
fi

echo "VC++ runtime DLLs copied to $TARGET"
