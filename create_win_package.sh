#!/bin/sh

# This should work on Windows (MinGW) and Linux
# for MinGW use e.g. https://gitforwindows.org/
# on Linux install msitools for msiextract

VERSION=$(sed -n 's/^version: "\(.*\)"/\1/p' snapcraft.yaml)

mkdir -p winpkg
cd winpkg

PYVER=3.10.10

[ -f ogre-sdk.zip ] || curl -L https://dl.cloudsmith.io/public/ogrecave/ogre/raw/versions/v14.6.3/ogre-sdk-v14.6.3-msvc142-x64.zip -o ogre-sdk.zip
[ -f python-${PYVER}-embed-amd64.zip ] || curl -LO https://www.python.org/ftp/python/${PYVER}/python-${PYVER}-embed-amd64.zip
[ -f tcltk-${PYVER}-amd64.msi ] || curl -L -o tcltk-${PYVER}-amd64.msi https://www.python.org/ftp/python/${PYVER}/amd64/tcltk.msi
rm -rf package
unzip -oq python-${PYVER}-embed-amd64.zip -d package

# the embeddable package has no tkinter; add it from the official Python MSI.
# on Linux use msitools (msiextract); under Git for Windows use msiexec.
rm -rf tcltk
if command -v msiextract >/dev/null 2>&1; then
    msiextract -C tcltk tcltk-${PYVER}-amd64.msi
else
    command -v cmd >/dev/null 2>&1 || { echo "need msitools (msiextract) or Git for Windows" >&2; exit 1; }
    mkdir -p tcltk
    cmd //c "start /wait msiexec /a \"$(cygpath -w "$PWD/tcltk-${PYVER}-amd64.msi")\" /qn TARGETDIR=\"$(cygpath -w "$PWD/tcltk")\""
    [ -f tcltk/DLLs/_tkinter.pyd ] || { echo "failed to extract tcltk-${PYVER}-amd64.msi" >&2; exit 1; }
fi

cp -R tcltk/Lib/tkinter package/
cp -R tcltk/tcl package/
cp tcltk/DLLs/_tkinter.pyd tcltk/DLLs/tcl86t.dll tcltk/DLLs/tk86t.dll package/

unzip -oq ogre-sdk.zip

# main
cp ../ogre*py ../ogre*bat ../LICENSE ../README.md package/

# copy ogre parts
cp -R lib/python3.10/dist-packages/Ogre package
# components
cp bin/OgreMain.dll bin/OgreBites.dll bin/OgreOverlay.dll bin/OgreRTShaderSystem.dll bin/OgreTerrain.dll bin/OgrePaging.dll package
# plugins
cp bin/Codec*dll bin/RenderSystem*dll bin/Plugin_DotScene.dll bin/Plugin_GLSLangProgramManager.dll package
# deps
cp bin/SDL2.dll package
if [ -f bin/z.dll ]; then
    cp bin/z.dll package
else
    cp bin/zlib.dll package
fi

# write plugins.cfg
head -10 bin/plugins.cfg > package/plugins.cfg
echo Plugin=Codec_RsImage >> package/plugins.cfg
echo Plugin=Codec_Assimp >> package/plugins.cfg
echo Plugin=Plugin_DotScene >> package/plugins.cfg
echo Plugin=RenderSystem_Vulkan >> package/plugins.cfg
echo Plugin=Plugin_GLSLangProgramManager >> package/plugins.cfg

# resources
cp ../win_resources.cfg package/resources.cfg
cp -R Media/RTShaderLib Media/Main package/
cp -R ../fonts package/
cp ../inno/ogre-meshviewer.ico package/

rm -rf ogre-meshviewer_${VERSION}-win64
mv package ogre-meshviewer_${VERSION}-win64
