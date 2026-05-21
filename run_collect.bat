@echo off
title Android UI Tree Review Collector
cd /d "%~dp0"
set "PATH=%USERPROFILE%\Downloads\platform-tools;%PATH%"

echo.
echo ========================================
echo  Android UI Tree Review Collector
echo ========================================
echo.
echo Before running:
echo 1. Connect your Android phone with USB.
echo 2. Enable USB debugging and allow this computer.
echo 3. Open any app review page on the phone.
echo 4. Scroll until real review text is visible.
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found.
    echo Install Python and enable Add python.exe to PATH.
    echo.
    pause
    exit /b 1
)

python -c "import uiautomator2" >nul 2>nul
if errorlevel 1 (
    echo Installing uiautomator2...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: package install failed.
        echo Try manually: python -m pip install uiautomator2
        echo.
        pause
        exit /b 1
    )
)

python direct_collect.py

echo.
echo Finished. Check output\comments.txt
echo.
pause

