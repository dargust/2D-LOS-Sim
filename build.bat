@echo off
echo Running pyinstaller build..
pyinstaller launcher.spec
echo Build finished, moving built exe to main dir..
move .\dist\launcher.exe launcher.exe