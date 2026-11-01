#!/bin/sh

# Build the Windows installer from the staged portable package.
#
# Run ./create_win_package.sh from the repository root first. On Windows,
# install Inno Setup and either put iscc in PATH or set ISCC to ISCC.exe.
# The app-local VC++ runtime is added to the package before compilation.
#
# On Linux, Inno Setup's ISCC.exe can be run through Wine:
#
#   innoextract -d /tmp/inno innosetup-6.2.2.exe
#   WINE=/opt/wine-stable/bin/wine ISCC=/tmp/inno/app/ISCC.exe ./inno/create_win_installer.sh
#
# WINE can be used to select a specific Wine build. The generated setup
# executable can usually be installed under a working Wine setup; testing on
# Windows is still recommended.

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

VERSION=${VERSION:-$(sed -n 's/^version: "\(.*\)"/\1/p' snapcraft.yaml)}
SOURCE_DIR="winpkg/ogre-meshviewer_${VERSION}-win64"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "missing '$SOURCE_DIR'; run ./create_win_package.sh first" >&2
    exit 1
fi

# Add the app-local VC++ runtime to the installer payload. On Linux this is
# the only part of the installer build that needs Wine-specific extraction.
sh ./inno/get_vc_runtime.sh winpkg/vcruntime-x64
cp winpkg/vcruntime-x64/*.dll "$SOURCE_DIR/"

if [ -z "$ISCC" ]; then
    if command -v iscc >/dev/null 2>&1; then
        ISCC=$(command -v iscc)
    elif [ -n "$HOST_WINDOWS" ]; then
        for p in "/c/Program Files/Inno Setup 7/ISCC.exe" \
                 "/c/Program Files (x86)/Inno Setup 7/ISCC.exe" \
                 "/c/Program Files/Inno Setup 6/ISCC.exe" \
                 "/c/Program Files (x86)/Inno Setup 6/ISCC.exe"; do
            if [ -f "$p" ]; then
                ISCC=$p
                break
            fi
        done
        if [ -z "$ISCC" ] && [ -n "${LOCALAPPDATA:-}" ]; then
            localappdata=$LOCALAPPDATA
            if command -v cygpath >/dev/null 2>&1; then
                localappdata=$(cygpath -u "$localappdata")
            fi
            for p in "$localappdata/Programs/Inno Setup 7/ISCC.exe" \
                     "$localappdata/Programs/Inno Setup 6/ISCC.exe"; do
                if [ -f "$p" ]; then
                    ISCC=$p
                    break
                fi
            done
        fi
    else
        for p in "${WINEPREFIX:-$HOME/.wine}/drive_c/Program Files (x86)/Inno Setup 7/ISCC.exe" \
                 "${WINEPREFIX:-$HOME/.wine}/drive_c/Program Files/Inno Setup 7/ISCC.exe" \
                 "${WINEPREFIX:-$HOME/.wine}/drive_c/Program Files (x86)/Inno Setup 6/ISCC.exe" \
                 "${WINEPREFIX:-$HOME/.wine}/drive_c/Program Files/Inno Setup 6/ISCC.exe"; do
            if [ -f "$p" ]; then
                ISCC=$p
                break
            fi
        done
    fi
fi

if [ -z "$ISCC" ]; then
    echo "Inno Setup compiler (ISCC) not found" >&2
    echo "set ISCC to ISCC.exe or add iscc to PATH" >&2
    exit 1
fi

if [ -n "$HOST_WINDOWS" ]; then
    "$ISCC" /Q /DMyAppVersion="$VERSION" inno/installer.iss
else
    case "$ISCC" in
        *.exe|*.EXE)
            WINE=${WINE:-wine}
            if ! command -v "$WINE" >/dev/null 2>&1; then
                echo "'$ISCC' is a Windows executable but '$WINE' was not found" >&2
                exit 1
            fi
            WINEDEBUG=${WINEDEBUG:--all} "$WINE" "$ISCC" /Q /DMyAppVersion="$VERSION" inno/installer.iss
            ;;
        *)
            "$ISCC" /Q /DMyAppVersion="$VERSION" inno/installer.iss
            ;;
    esac
fi

echo "built winpkg/ogre-meshviewer_${VERSION}-win64-setup.exe"
