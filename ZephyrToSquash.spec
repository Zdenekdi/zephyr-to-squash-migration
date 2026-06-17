# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for ZephyrToSquash Migration Tool

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env.example', '.'),   # přibalíme šablonu konfigurace
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'dotenv',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'requests',
        'urllib3',
        'charset_normalizer',
        'certifi',
        'idna',
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
