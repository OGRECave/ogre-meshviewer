@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
start "" "%~dp0pythonw.exe" "%~dp0ogre_mesh_viewer.py" "%~1"
