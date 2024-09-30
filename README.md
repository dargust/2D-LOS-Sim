# 2D-LOS-Sim By Dan Argust 30/09/2024
pygame 2D LOS Simulator

Can be run with keyboard using fixed rates.
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
