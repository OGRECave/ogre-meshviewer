#!/bin/sh

# Fetch the Microsoft Visual C++ x64 runtime DLLs for app-local deployment.
#
# On Windows the already installed runtime is used, or VCRUNTIME_DIR can point
# at a directory containing the DLLs. On non-Windows hosts the Wine-specific
# extraction is delegated to inno/get_vc_runtime_wine.sh.
#
# Usage:
#   ./inno/get_vc_runtime.sh [output-dir]
#
# Environment:
#   VCRUNTIME_DIR  directory containing the runtime DLLs (skips Wine)

set -e

SCRIPT=$(readlink -f "$0" 2>/dev/null || echo "$0")
cd "$(dirname "$SCRIPT")/.."

case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) HOST_WINDOWS=1 ;;
    *) HOST_WINDOWS= ;;
esac
if [ "${OS:-}" = "Windows_NT" ] || [ -n "${WSL_DISTRO_NAME:-}" ]; then
    HOST_WINDOWS=1
fi

if [ -z "$WINDIR" ] && [ -n "${WSL_DISTRO_NAME:-}" ] && [ -d /mnt/c/Windows/System32 ]; then
    WINDIR=/mnt/c/Windows
fi

TARGET=${1:-winpkg/vcruntime-x64}
DLLS="msvcp140.dll msvcp140_1.dll msvcp140_2.dll msvcp140_atomic_wait.dll
      msvcp140_codecvt_ids.dll vcruntime140.dll vcruntime140_1.dll
      vcruntime140_threads.dll concrt140.dll"

mkdir -p "$TARGET"

if [ -n "$VCRUNTIME_DIR" ]; then
    SRC=$VCRUNTIME_DIR
elif [ -n "$WINDIR" ]; then
    SRC=$WINDIR/System32
else
    SRC=
fi

if [ -n "$SRC" ] && command -v cygpath >/dev/null 2>&1; then
    SRC=$(cygpath -u "$SRC")
fi

if [ -z "$SRC" ]; then
    exec sh "$(pwd)/inno/get_vc_runtime_wine.sh" "$TARGET"
elif [ ! -d "$SRC" ]; then
    if [ -n "$HOST_WINDOWS" ]; then
        echo "'$SRC' not found; install the VC++ redistributable or set VCRUNTIME_DIR" >&2
        exit 1
    fi
    exec sh "$(pwd)/inno/get_vc_runtime_wine.sh" "$TARGET"
fi

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
