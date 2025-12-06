@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Build script for FACOT desktop app (Windows)
REM Produces a single executable: facot.exe
REM Requirements:
REM  - Python 3.12 (or your installed version)
REM  - pip installed packages (see requirements.txt)
REM  - PyInstaller
REM  - Run this .bat from the project root (where main.py lives)
REM ============================================================

REM Detect Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Please install Python or add it to PATH.
    pause
    exit /b 1
)

REM Optional: create venv for clean build
set VENV_DIR=.venv
if not exist "%VENV_DIR%" (
    echo [INFO] Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [WARN] Could not activate venv. Continuing with system Python...
)

REM Install required packages
if exist requirements.txt (
    echo [INFO] Installing requirements...
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo [INFO] requirements.txt not found. Installing minimum build dependencies...
    pip install --upgrade pip
    pip install pyinstaller PyQt6 PyQt6-WebEngine google-cloud-firestore google-cloud-storage requests
)

REM Clean previous build artifacts
echo [INFO] Cleaning dist/ and build/...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist facot.spec del /q facot.spec

REM Optional: set app icon if you have one (ICO file)
set APP_ICON=assets\facot.ico
if not exist "%APP_ICON%" (
    REM Fallback: no icon
    set ICON_FLAG=
) else (
    set ICON_FLAG=--icon "%APP_ICON%"
)

REM Optional: add data files needed at runtime (adjust paths as needed)
REM Example: include templates, data, resources
set DATA_FLAGS=
if exist templates (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "templates;templates"
)
if exist data (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "data;data"
)
if exist assets (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "assets;assets"
)

REM PyQt6 WebEngine runtime resources (QtWebEngineProcess, translations, resources)
REM PyInstaller usually detects these, but we add explicit flags for reliability.
REM Note: paths vary by environment; the following works for most pip installs.
for /f "delims=" %%I in ('python -c "import PyQt6, sys, os; print(os.path.dirname(PyQt6.__file__))"') do set PYQT6_DIR=%%I
if exist "%PYQT6_DIR%\Qt6\bin\QtWebEngineProcess.exe" (
    set DATA_FLAGS=!DATA_FLAGS! --add-binary "%PYQT6_DIR%\Qt6\bin\QtWebEngineProcess.exe;PyQt6\Qt6\bin"
)
if exist "%PYQT6_DIR%\Qt6\resources" (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "%PYQT6_DIR%\Qt6\resources;PyQt6\Qt6\resources"
)
if exist "%PYQT6_DIR%\Qt6\translations" (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "%PYQT6_DIR%\Qt6\translations;PyQt6\Qt6\translations"
)

REM Firebase credentials or config files (if used at runtime)
if exist firebase_credentials.json (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "firebase_credentials.json;."
)
if exist facot_config.py (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "facot_config.py;."
)

REM Build with PyInstaller
echo [INFO] Building facot.exe...
pyinstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name facot ^
    %ICON_FLAG% ^
    %DATA_FLAGS% ^
    main.py

if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

REM Move/rename output if needed
if exist dist\facot.exe (
    echo [SUCCESS] Build complete: dist\facot.exe
) else (
    echo [WARN] facot.exe not found in dist. Check build logs.
)

echo [INFO] Deactivating venv...
call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul

echo [DONE] You can distribute dist\facot.exe
pause