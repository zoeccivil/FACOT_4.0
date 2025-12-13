# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('c:\\Users\\ZOEC CIVIL DESK\\AppData\\Local\\Programs\\Python\\Python314\\Lib\\site-packages\\PyQt6\\Qt6\\bin\\QtWebEngineProcess.exe', 'PyQt6\\Qt6\\bin')],
    datas=[('templates', 'templates'), ('themes', 'themes'), ('data', 'data'), ('assets', 'assets'), ('facot_config.py', '.'), ('facot_config.json', '.'), ('c:\\Users\\ZOEC CIVIL DESK\\AppData\\Local\\Programs\\Python\\Python314\\Lib\\site-packages\\PyQt6\\Qt6\\resources', 'PyQt6\\Qt6\\resources'), ('c:\\Users\\ZOEC CIVIL DESK\\AppData\\Local\\Programs\\Python\\Python314\\Lib\\site-packages\\PyQt6\\Qt6\\translations', 'PyQt6\\Qt6\\translations')],
    hiddenimports=['firebase_admin', 'google.cloud.firestore', 'google.cloud.storage', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'openpyxl', 'pandas'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='facot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
