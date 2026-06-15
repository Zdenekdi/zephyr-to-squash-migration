@echo off
:: Windows launcher for Zephyr to Squash TM Migration Tool
chcp 65001 > nul
cd /d "%~dp0"

echo =========================================================
echo    Spouštím Zephyr ➔ Squash TM Migration Tool (GUI)
echo =========================================================

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Chyba: Python není nainstalován v systému nebo není v PATH.
    echo Stáhněte si jej prosím z https://www.python.org/downloads/
    echo (Nezapomeňte při instalaci zaškrtnout "Add Python to PATH")
    echo.
    pause
    exit /b 1
)

:: 2. Setup virtual environment
if not exist .venv (
    echo Vytvářím virtuální prostředí Python (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo Chyba při vytváření virtuálního prostředí.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: 3. Install/upgrade requirements
echo Instaluji a aktualizuji knihovny (může chvíli trvat)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Chyba při instalaci závislostí z requirements.txt.
    pause
    exit /b 1
)

:: 4. Start GUI
echo Spouštím grafické rozhraní...
python gui.py

if %errorlevel% neq 0 (
    echo.
    echo Aplikace skončila s chybou.
    pause
)
