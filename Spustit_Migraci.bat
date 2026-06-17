@echo off
:: Windows launcher for Zephyr to Squash TM Migration Tool
chcp 65001 >nul
cd /d "%~dp0"

echo =========================================================
echo    Spoustim Zephyr - Squash TM Migration Tool (GUI)
echo =========================================================
echo.

:: 1. Kontrola instalace Pythonu
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo CHYBA: Python neni nainstalovan nebo neni v PATH.
    echo Stahnete jej z https://www.python.org/downloads/
    echo Przy instalaci zatrhnete "Add Python to PATH"!
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo Nalezeno: %%i
echo.

:: 2. Nastaveni virtualniho prostredi
if not exist .venv (
    echo Vytvarim virtualni prostredi (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo CHYBA: Nepodarilo se vytvorit virtualni prostredi.
        pause
        exit /b 1
    )
    echo OK.
    echo.
)

:: Aktivace virtualniho prostredi
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo CHYBA: Aktivace virtualniho prostredi selhala.
    pause
    exit /b 1
)

:: 3. Instalace zavislosti
echo Aktualizuji pip a instaluji knihovny...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo CHYBA: Nepodarilo se nainstalovat zavislosti z requirements.txt.
    pause
    exit /b 1
)
echo OK.
echo.

:: 4. Spusteni GUI
echo Spoustim graficke rozhrani...
echo.
python -X utf8 gui.py
set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo.
    echo =========================================================
    echo   CHYBA: Aplikace skoncila s kodem %EXIT_CODE%
    echo =========================================================
    if exist gui_error.log (
        echo.
        echo --- Detaily chyby z gui_error.log ---
        type gui_error.log
    )
    echo.
    pause
    exit /b %EXIT_CODE%
)

exit /b 0
