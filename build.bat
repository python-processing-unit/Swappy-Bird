@echo off
REM Automatically detect the root directory of the batch file
set "ROOTDIR=%~dp0"
REM Remove trailing backslash if present
if "%ROOTDIR:~-1%"=="\" set "ROOTDIR=%ROOTDIR:~0,-1%"
pip install pygame-ce
pip install pywin32
pip install pyinstaller
REM Change to EXE directory
cd "%ROOTDIR%"

REM Build with pyinstaller, dynamically referencing the root directory
pyinstaller --onefile --windowed --icon "%ROOTDIR%\assets\sprites\logo.png" ^
  --add-data "%ROOTDIR%\assets;assets" ^
  "%ROOTDIR%\Swappy Bird.py"

REM Clean up build artifacts
rmdir /s /q "%ROOTDIR%\build"
del /q "%ROOTDIR%\Swappy Bird.spec"
move /y "%ROOTDIR%\dist\Swappy Bird.exe" "%ROOTDIR%\"
rmdir /s /q "%ROOTDIR%\dist"