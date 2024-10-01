# 2D-LOS-Sim
pygame 2D LOS Simulator

IF YOU DON'T HAVE OR WANT TO USE PYTHON -> RUN THE LAUNCHER TO BOOT

Can be run with keyboard using fixed rates. Up arrow is throttle, Left and Right are roll.
If a transmitter / controller is plugged in before running, it will detect it and apply betaflight rates.

Requirements to run:
python
pygame				pip install pygame
pygame_gui		pip install pygame_gui

Requirements to build:
'All above' +
pyinstaller

either run main.py as a standalone python file
or run the launcher to download the latest built release from github releases
or build yourself by running build.bat / running 'pyinstaller 2DLOS.spec'

![Alt text](src/Assets/screenshot.JPG?raw=true "screenshot")
