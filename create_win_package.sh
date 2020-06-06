#!/bin/sh

# This should work on Windows (MinGW) and Linux
# for MinGW use e.g. https://gitforwindows.org/

curl -L https://bintray.com/ogrecave/ogre/download_file?file_path=ogre-sdk-master2-vc15-x64.zip -o ogre-sdk.zip
curl -LO https://www.python.org/ftp/python/3.7.7/python-3.7.7-embed-amd64.zip
unzip python-3.7.7-embed-amd64.zip -d package
unzip ogre-sdk.zip

# main
cp ogre*py ogre*bat LICENSE README.md package/

# copy ogre parts
cp -R lib/python3.7/dist-packages/Ogre package
# components
cp bin/OgreMain.dll bin/OgreBites.dll bin/OgreOverlay.dll bin/OgreRTShaderSystem.dll package
# plugins
cp bin/Codec*dll bin/RenderSystem*dll package
# deps
cp bin/SDL2.dll bin/zlib.dll package

# write plugins.cfg
head -10 bin/plugins.cfg > package/plugins.cfg
echo Plugin=Codec_STBI >> package/plugins.cfg

# resources
cp win_resources.cfg package/resources.cfg
cp -R Media/RTShaderLib Media/ShadowVolume package/
cp -R Media/packs/SdkTrays.zip package/

mv package ogre-meshviewer_20.06-win64
