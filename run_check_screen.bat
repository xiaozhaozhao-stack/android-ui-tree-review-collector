@echo off
title Check Android Screen Text
cd /d "%~dp0"
set "PATH=%USERPROFILE%\Downloads\platform-tools;%PATH%"

echo.
echo ========================================
echo  Check current Android screen text
echo ========================================
echo Keep the phone unlocked and open on the target page.
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found.
    pause
    exit /b 1
)

python -c "import uiautomator2" >nul 2>nul
if errorlevel 1 (
    echo Installing uiautomator2...
    python -m pip install -r requirements.txt
)

python check_screen.py

echo.
echo Finished. Check:
echo output\screen_all_text.txt
echo output\screen_candidate_comments.txt
echo.
pause

