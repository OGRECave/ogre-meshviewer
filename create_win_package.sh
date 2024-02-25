#!/bin/sh

# This should work on Windows (MinGW) and Linux
# for MinGW use e.g. https://gitforwindows.org/

mkdir winpkg
cd winpkg

curl -L https://dl.cloudsmith.io/public/ogrecave/ogre/raw/versions/v14.0.0/ogre-sdk-v14.0.0-msvc141-x64.zip -o ogre-sdk.zip
curl -LO https://www.python.org/ftp/python/3.10.10/python-3.10.10-embed-amd64.zip
curl -LO https://github.com/OGRECave/ogre-meshviewer/releases/download/24.02/tkinter_3.10.10-amd64.zip
unzip python-3.10.10-embed-amd64.zip -d package
unzip tkinter_3.10.10-amd64.zip -d package
unzip ogre-sdk.zip

# main
cp ../ogre*py ../ogre*bat ../LICENSE ../README.md package/

# copy ogre parts
cp -R lib/python3.10/dist-packages/Ogre package
# components
cp bin/OgreMain.dll bin/OgreBites.dll bin/OgreOverlay.dll bin/OgreRTShaderSystem.dll bin/OgreTerrain.dll bin/OgrePaging.dll package
# plugins
cp bin/Codec*dll bin/RenderSystem*dll bin/Plugin_DotScene.dll bin/Plugin_GLSLangProgramManager.dll package
# deps
cp bin/SDL2.dll bin/zlib.dll package

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

mv package ogre-meshviewer_24.02-win64
