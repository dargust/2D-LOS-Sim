@echo off
echo Running pyinstaller build for launcher..
pyinstaller launcher.spec
echo Build finished, moving built exe to main dir..
move .\dist\launcher.exe launcher.exe
echo Running pyinstaller build for main executable..
pyinstaller 2DLOS.spec
echo DONE!!
pause