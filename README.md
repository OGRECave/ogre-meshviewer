# ogre-meshviewer

<a href="https://www.patreon.com/ogre1" target="_blank" ><img src="https://www.ogre3d.org/wp-content/uploads/2018/10/become_a_patron_button.png" width=135px></a>

Viewer for `.mesh` model files as consumed by OGRE as well as any format [supported by assimp](https://github.com/assimp/assimp/blob/master/doc/Fileformats.md) like `.obj`, `.ply` or `.fbx`.

![](screenshot.jpg)

# features
* display mesh properties (bounds, referenced materials)
* highlight submeshes in 3D view
* preview linked animations (skeleton and vertex)
* easy to use UI

# usage
Double click on `.mesh` in file browser or use the CLI as

```
ogre-meshviewer [-h] [-c RESCFG] meshfile
```
where `meshfile` can be either an absolute path or a resource name referenced in RESCFG.

# dependencies
* ogre 1.12.7+
* python3

# download
[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/ogre-meshviewer)

[Portable Windows Package](https://github.com/OGRECave/ogre-meshviewer/releases)