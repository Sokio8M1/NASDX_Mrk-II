@echo off
REM Jarvis Quick Start Script for Windows 11
REM Automatically activates virtual environment and starts Jarvis

title Jarvis AI Assistant

REM Set console colors (Cyan on Black - like JARVIS UI)
color 0

REM Display ASCII banner
echo.
echo     ====================================
echo          J.A.R.V.I.S v1.7
echo       Just A Rather Very Intelligent System
echo     ====================================
echo.

REM Check if virtual environment exists
if exist jarvis_env\Scripts\activate.bat (
    echo [INFO] Activating virtual environment...
    call jarvis_env\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found
    echo [INFO] Using system Python...
)

REM Check if jarvis_main.py exists
if not exist jarvis_main.py (
    echo [ERROR] jarvis_main.py not found!
    echo Please ensure you're in the correct directory.
    pause
    exit /b 1
)

REM Check if config.json exists
if not exist config.json (
    echo [WARNING] config.json not found!
    echo Creating default configuration...
    copy nul config.json >nul
)

echo [INFO] Starting Jarvis...
echo.

REM Start Jarvis with error handling
python jarvis_main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Jarvis encountered an error ^(Exit code: %errorlevel%^)
    echo.
    echo Troubleshooting:
    echo   1. Check if all dependencies are installed: pip install -r requirements.txt
    echo   2. Verify config.json is valid JSON
    echo   3. Check logs folder for error details
    echo.
)

echo.
echo Jarvis has shut down.
pause