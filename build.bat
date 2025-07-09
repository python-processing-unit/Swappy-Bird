@echo off
REM Automatically detect the root directory of the batch file
set "ROOTDIR=%~dp0"
REM Remove trailing backslash if present
if "%ROOTDIR:~-1%"=="\" set "ROOTDIR=%ROOTDIR:~0,-1%"
pip install pygame
REM Change to EXE directory
cd "%ROOTDIR%\exe"

REM Build with pyinstaller, dynamically referencing the root directory
pyinstaller --onefile --icon "%ROOTDIR%\src\battle_system\sprites\logo\icon.png" ^
  --add-data "%ROOTDIR%\assets;assets" ^
  --add-data "%ROOTDIR%\save;save" ^
  --hidden-import pygame "%ROOTDIR%\Swappy Bird.py"

REM Clean up build artifacts
rmdir /s /q "%ROOTDIR%\exe\build"
del /q "%ROOTDIR%\exe\init.spec"
move /y "%ROOTDIR%\exe\dist\init.exe" "%ROOTDIR%\exe\"
rmdir /s /q "%ROOTDIR%\exe\dist"