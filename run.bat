@echo off
REM =====================================================================
REM run.bat
REM -----------------------------------------------------------------
REM One-click launcher for C Compiler Error Explainer on Windows 11.
REM   - Creates backend\venv on first run (skips if it already exists)
REM   - Installs backend\requirements.txt on first run
REM   - Starts the Flask backend on http://127.0.0.1:5000
REM
REM No API key, no .env file, no internet connection needed anywhere --
REM this project contains no AI and works entirely offline.
REM
REM After this window shows "Listening on: http://127.0.0.1:5000",
REM open frontend\index.html in your browser.
REM
REM Usage: double-click this file, OR run it from a terminal opened
REM in the project root:
REM     run.bat
REM =====================================================================

cd /d "%~dp0backend"

if not exist venv (
    echo Creating virtual environment ^(first run only^)...
    python -m venv venv
    if errorlevel 1 goto :nopython
)

call venv\Scripts\activate.bat

echo Checking dependencies...
pip install -r requirements.txt --quiet

echo.
echo ============================================================
echo  Starting C Compiler Error Explainer backend...
echo  No AI, no API key, no internet required.
echo  Once you see "Listening on: http://127.0.0.1:5000" below,
echo  open frontend\index.html in your browser.
echo ============================================================
echo.

python app.py
goto :eof

:nopython
echo.
echo ERROR: Python was not found. Install it from https://www.python.org/downloads/
echo and make sure to check "Add python.exe to PATH" during setup.
echo See README.md -^> Windows 11 Setup, Step 2.
pause
exit /b 1
