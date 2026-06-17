# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for ZephyrToSquash Migration Tool

block_cipher = None

# Locate tkinterdnd2 package data (TkDND native library)
import os, sys
try:
    import tkinterdnd2
    tkdnd_path = os.path.dirname(tkinterdnd2.__file__)
    tkdnd_datas = [(tkdnd_path, 'tkinterdnd2')]
except ImportError:
    tkdnd_datas = []

a = Analysis(
    ['gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('.env.example', '.'),      # šablona konfigurace
    ] + tkdnd_datas,                # tkinterdnd2 nativní knihovny
    hiddenimports=[
        # tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        # drag & drop
        'tkinterdnd2',
        # dotenv
        'dotenv',
        # Excel
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        # HTTP
        'requests',
        'urllib3',
        'charset_normalizer',
        'certifi',
        'idna',
        # Naše vlastní moduly (volané přímo v .exe režimu)
        'convert',
        'main',
        'config',
        'api_clients',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        'gi',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ZephyrToSquash',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # žádné černé konzolové okno na pozadí
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',   # odkomentovat pokud přidáte icon.ico do projektu
)
