#!/bin/sh

# This should work on Windows (MinGW) and Linux
# for MinGW use e.g. https://gitforwindows.org/

curl -L https://dl.cloudsmith.io/public/ogrecave/ogre/raw/files/ogre-sdk-v13.2.0-msvc141-x64.zip -o ogre-sdk.zip
curl -LO https://www.python.org/ftp/python/3.7.9/python-3.7.9-embed-amd64.zip
unzip python-3.7.9-embed-amd64.zip -d package
unzip ogre-sdk.zip

# main
cp ogre*py ogre*bat LICENSE README.md package/

# copy ogre parts
cp -R lib/python3.7/dist-packages/Ogre package
# components
cp bin/OgreMain.dll bin/OgreBites.dll bin/OgreOverlay.dll bin/OgreRTShaderSystem.dll bin/OgreTerrain.dll bin/OgrePaging.dll package
# plugins
cp bin/Codec*dll bin/RenderSystem*dll bin/Plugin_DotScene.dll package
# deps
cp bin/SDL2.dll bin/zlib.dll package

# write plugins.cfg
head -10 bin/plugins.cfg > package/plugins.cfg
echo Plugin=Codec_STBI >> package/plugins.cfg
echo Plugin=Codec_Assimp >> package/plugins.cfg
echo Plugin=Plugin_DotScene >> package/plugins.cfg

# resources
cp win_resources.cfg package/resources.cfg
cp -R Media/RTShaderLib Media/Main package/
cp -R Media/packs/SdkTrays.zip package/

mv package ogre-meshviewer_21.10-win64
