@echo off
echo ========================================
echo  Compilando FACOT 4.0 a ejecutable
echo ========================================

REM Limpiar builds anteriores
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "FACOT_4.0.spec" del /q FACOT_4.0.spec

echo Limpiando archivos temporales...

REM Compilar con PyInstaller
echo Iniciando compilacion con PyInstaller...
pyinstaller --clean ^
    --name="FACOT_4.0" ^
    --onefile ^
    --windowed ^
    --icon=assets/facot_icon.ico ^
    --add-data "templates;templates" ^
    --add-data "assets;assets" ^
    --hidden-import=PyQt6 ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=PyQt6.QtWebEngineWidgets ^
    --hidden-import=firebase_admin ^
    --hidden-import=google.cloud.firestore ^
    --hidden-import=google.cloud.firestore_v1 ^
    --hidden-import=fpdf ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=PIL ^
    --hidden-import=certifi ^
    --collect-all firebase_admin ^
    --collect-all google-cloud-firestore ^
    main.py

if %ERRORLEVEL% EQU 0 (
    echo ========================================
    echo  Compilacion completada exitosamente!
    echo  Ejecutable en: dist\FACOT_4.0.exe
    echo ========================================
) else (
    echo ========================================
    echo  ERROR: La compilacion fallo
    echo ========================================
)

pause