@echo off
:: Windows launcher for Zephyr to Squash TM Migration Tool
chcp 65001 > nul
cd /d "%~dp0"

echo =========================================================
echo    Spoustim Zephyr - Squash TM Migration Tool (GUI)
echo =========================================================

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Chyba: Python neni nainstalovan v systemu nebo neni v PATH.
    echo Stahnete si jej prosim z https://www.python.org/downloads/
    echo (Nezapomente pri instalaci zaskrtnout "Add Python to PATH")
    echo.
    pause
    exit /b 1
)

:: 2. Setup virtual environment
if not exist .venv (
    echo Vytvarim virtualni prostredi Python (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo Chyba pri vytvareni virtualniho prostredi.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: 3. Install/upgrade requirements
echo Instaluji a aktualizuji knihovny (muze chvili trvat)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Chyba pri instalaci zavislosti z requirements.txt.
    pause
    exit /b 1
)

:: 4. Start GUI
echo Spoustim graficke rozhrani...
python gui.py

if %errorlevel% neq 0 (
    echo.
    echo Aplikace skoncila s chybou.
    pause
)
