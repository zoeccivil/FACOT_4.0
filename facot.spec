# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for FACOT
# This spec includes all necessary data files and WebEngine resources

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get PyQt6 directory for WebEngine resources
import PyQt6
pyqt6_dir = os.path.dirname(PyQt6.__file__)

# Collect data files
datas = []

# Add project data directories
for dirname in ['templates', 'themes', 'data', 'assets']:
    if os.path.exists(dirname):
        datas.append((dirname, dirname))

# Add config files if present
for config_file in ['firebase_credentials.json', 'facot_config.py', 'facot_config.json']:
    if os.path.exists(config_file):
        datas.append((config_file, '.'))

# Add PyQt6 WebEngine resources
qt6_resources = os.path.join(pyqt6_dir, 'Qt6', 'resources')
if os.path.exists(qt6_resources):
    datas.append((qt6_resources, 'PyQt6/Qt6/resources'))

qt6_translations = os.path.join(pyqt6_dir, 'Qt6', 'translations')
if os.path.exists(qt6_translations):
    datas.append((qt6_translations, 'PyQt6/Qt6/translations'))

# Collect binaries for WebEngine
binaries = []
qt_webengine_process = os.path.join(pyqt6_dir, 'Qt6', 'bin', 'QtWebEngineProcess.exe')
if os.path.exists(qt_webengine_process):
    binaries.append((qt_webengine_process, 'PyQt6/Qt6/bin'))

# Hidden imports
hiddenimports = [
    'firebase_admin',
    'google.cloud.firestore',
    'google.cloud.storage',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineCore',
    'openpyxl',
    'pandas',
    'pyqtgraph',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    icon='assets/facot.ico' if os.path.exists('assets/facot.ico') else None,
)

