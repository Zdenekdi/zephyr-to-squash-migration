#!/usr/bin/env bash
# macOS launcher for Zephyr to Squash TM Migration Tool

# Change directory to the folder containing this script
cd "$(dirname "$0")"

echo "========================================================="
echo "   Spouštím Zephyr ➔ Squash TM Migration Tool (GUI)"
echo "========================================================="

# 1. Check Python installation
if ! command -v python3 &>/dev/null; then
    echo "Chyba: Python 3 není nainstalován v systému."
    echo "Stáhněte si jej prosím z https://www.python.org/downloads/"
    echo "Stisknutím klávesy Enter zavřete okno..."
    read
    exit 1
fi

# 2. Setup virtual environment
if [ ! -d ".venv" ]; then
    echo "Vytvářím virtuální prostředí Python (.venv)..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Chyba při vytváření virtuálního prostředí."
        echo "Stisknutím klávesy Enter zavřete okno..."
        read
        exit 1
    fi
fi

# Activate virtual environment
source .venv/bin/activate

# 3. Install/upgrade requirements
echo "Instaluji a aktualizuji knihovny (může chvíli trvat)..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Chyba při instalaci závislostí z requirements.txt."
    echo "Stisknutím klávesy Enter zavřete okno..."
    read
    exit 1
fi

# 4. Start GUI
echo "Spouštím grafické rozhraní..."
python3 gui.py

# Keep terminal open if GUI exits with an error
if [ $? -ne 0 ]; then
    echo "Aplikace skončila s chybou."
    echo "Stisknutím klávesy Enter zavřete okno..."
    read
fi
