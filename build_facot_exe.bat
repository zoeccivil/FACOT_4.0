@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Build script for FACOT desktop app (Windows)
REM Produces a single executable: facot.exe
REM Requirements:
REM  - Python 3.12+ (or your installed version)
REM  - pip installed packages (see requirements.txt)
REM  - PyInstaller
REM  - Run this .bat from the project root (where main.py lives)
REM ============================================================

echo.
echo ========================================
echo  FACOT Build Script
echo ========================================
echo.

REM Detect Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Please install Python or add it to PATH.
    pause
    exit /b 1
)

echo [INFO] Python found: 
python --version
echo.

REM Optional: create venv for clean build
set VENV_DIR=.venv_build
if not exist "%VENV_DIR%" (
    echo [INFO] Creating virtual environment for build...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [WARN] Could not activate venv. Continuing with system Python...
    set VENV_DIR=
)

REM Install/update required packages
if exist requirements.txt (
    echo [INFO] Installing/updating requirements...
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements
        if not "%VENV_DIR%"=="" call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul
        pause
        exit /b 1
    )
) else (
    echo [INFO] requirements.txt not found. Installing minimum build dependencies...
    pip install --upgrade pip setuptools wheel
    pip install pyinstaller PyQt6 PyQt6-WebEngine google-cloud-firestore google-cloud-storage requests openpyxl pandas pyqtgraph
)

REM Ensure PyInstaller is available
pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo [INFO] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist facot.spec del /q facot.spec

REM Set app icon if available
set APP_ICON=
if exist "assets\facot.ico" (
    set APP_ICON=--icon "assets\facot.ico"
    echo [INFO] Using icon: assets\facot.ico
) else if exist "assets\icon.ico" (
    set APP_ICON=--icon "assets\icon.ico"
    echo [INFO] Using icon: assets\icon.ico
) else (
    echo [INFO] No icon file found, building without icon
)

REM Build data file flags
set DATA_FLAGS=

REM Include templates directory
if exist templates (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "templates;templates"
    echo [INFO] Including templates/
)

REM Include themes directory
if exist themes (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "themes;themes"
    echo [INFO] Including themes/
)

REM Include data directory
if exist data (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "data;data"
    echo [INFO] Including data/
)

REM Include assets directory
if exist assets (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "assets;assets"
    echo [INFO] Including assets/
)

REM Include Firebase credentials if present
if exist firebase_credentials.json (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "firebase_credentials.json;."
    echo [INFO] Including firebase_credentials.json
)

REM Include facot_config.py if present (as data file, not source)
if exist facot_config.py (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "facot_config.py;."
    echo [INFO] Including facot_config.py
)

REM Include facot_config.json if present
if exist facot_config.json (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "facot_config.json;."
    echo [INFO] Including facot_config.json
)

REM PyQt6 WebEngine runtime resources
REM Get PyQt6 installation directory
set PYQT6_DIR=
for /f "delims=" %%I in ('python -c "import PyQt6, os; print(os.path.dirname(PyQt6.__file__))" 2^>nul') do set PYQT6_DIR=%%I

if "%PYQT6_DIR%"=="" (
    echo [WARN] Could not detect PyQt6 directory. WebEngine resources may not be included.
    echo [WARN] Ensure PyQt6 is installed: pip install PyQt6 PyQt6-WebEngine
) else (
    echo [INFO] PyQt6 directory: %PYQT6_DIR%
)

REM Add QtWebEngineProcess.exe
if exist "%PYQT6_DIR%\Qt6\bin\QtWebEngineProcess.exe" (
    set DATA_FLAGS=!DATA_FLAGS! --add-binary "%PYQT6_DIR%\Qt6\bin\QtWebEngineProcess.exe;PyQt6\Qt6\bin"
    echo [INFO] Including QtWebEngineProcess.exe
) else (
    echo [WARN] QtWebEngineProcess.exe not found - WebEngine may not work in packaged app
)

REM Add WebEngine resources directory
if exist "%PYQT6_DIR%\Qt6\resources" (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "%PYQT6_DIR%\Qt6\resources;PyQt6\Qt6\resources"
    echo [INFO] Including Qt6/resources/
) else (
    echo [WARN] Qt6/resources directory not found
)

REM Add Qt translations
if exist "%PYQT6_DIR%\Qt6\translations" (
    set DATA_FLAGS=!DATA_FLAGS! --add-data "%PYQT6_DIR%\Qt6\translations;PyQt6\Qt6\translations"
    echo [INFO] Including Qt6/translations/
) else (
    echo [WARN] Qt6/translations directory not found
)

REM Hidden imports for Firebase and other modules
set HIDDEN_IMPORTS=--hidden-import firebase_admin --hidden-import google.cloud.firestore --hidden-import google.cloud.storage --hidden-import PyQt6.QtWebEngineWidgets --hidden-import PyQt6.QtWebEngineCore --hidden-import openpyxl --hidden-import pandas

echo.
echo [INFO] Building facot.exe with PyInstaller...
echo [INFO] This may take several minutes...
echo.

pyinstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name facot ^
    %APP_ICON% ^
    %DATA_FLAGS% ^
    %HIDDEN_IMPORTS% ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check the output above for details.
    if not "%VENV_DIR%"=="" call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul
    pause
    exit /b 1
)

REM Check if exe was created
if exist dist\facot.exe (
    echo.
    echo ========================================
    echo  BUILD SUCCESS!
    echo ========================================
    echo.
    echo [SUCCESS] facot.exe created: dist\facot.exe
    echo.
    dir dist\facot.exe
    echo.
) else (
    echo.
    echo [ERROR] facot.exe not found in dist\ directory
    echo Check build logs above for errors
    if not "%VENV_DIR%"=="" call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul
    pause
    exit /b 1
)

REM Deactivate venv
if not "%VENV_DIR%"=="" (
    echo [INFO] Deactivating virtual environment...
    call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul
)

echo.
echo ========================================
echo  Distribution Ready
echo ========================================
echo.
echo You can now distribute dist\facot.exe
echo.
echo The executable includes:
echo  - All Python dependencies
echo  - PyQt6 WebEngine runtime
echo  - Templates and themes
echo  - Assets and data files
echo  - Firebase configuration (if present)
echo.
echo To run: double-click dist\facot.exe
echo.

pause
