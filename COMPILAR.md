# 📦 Guía de Compilación de FACOT 4.0

## 🔧 Requisitos Previos

### Software Necesario
- Python 3.8 o superior
- pip actualizado
- PyInstaller 6.0+

### Verificar Instalación
```bash
python --version
pip --version
```

## 🚀 Proceso de Compilación

### Paso 1: Preparar Entorno

```bash
# Crear entorno virtual limpio (recomendado)
python -m venv venv_build
venv_build\Scripts\activate

# Instalar dependencias del proyecto
pip install -r requirements.txt

# Instalar herramientas de compilación
pip install -r build_requirements.txt
```

### Paso 2: Compilar

#### Opción A: Usar el script batch (Recomendado)
```bash
build_exe.bat
```

#### Opción B: Usar archivo .spec
```bash
pyinstaller facot.spec
```

#### Opción C: Comando manual
```bash
pyinstaller --onefile --windowed --name="FACOT_4.0" main.py
```

### Paso 3: Probar el Ejecutable

```bash
# Navegar a la carpeta de distribución
cd dist

# Ejecutar
FACOT_4.0.exe
```

## 📁 Estructura Después de Compilar

```
FACOT_4.0/
├── dist/
│   └── FACOT_4.0.exe          ← Ejecutable final
├── build/                      ← Archivos temporales
└── FACOT_4.0.spec             ← Configuración generada
```

## ✅ Checklist Pre-Compilación

- [ ] `requirements.txt` actualizado
- [ ] Todas las dependencias funcionan
- [ ] `main.py` ejecuta correctamente
- [ ] Icono `assets/facot_icon.ico` existe
- [ ] Carpeta `templates/` con plantillas
- [ ] No hay rutas absolutas en el código
- [ ] Probado en entorno limpio

## 🐛 Solución de Problemas

### Error: "PyInstaller no reconocido"
```bash
pip install pyinstaller
```

### Error: "No module named 'PyQt6'"
```bash
pip install -r requirements.txt
```

### Error: "Failed to execute script"
- Compilar con `--debug` para ver detalles
- Verificar que todos los archivos estén incluidos

### Ejecutable muy grande (>200MB)
- Normal para aplicaciones con PyQt6 y Firebase
- Considerar usar `--exclude-module` para módulos no usados

### Antivirus bloquea el .exe
- Agregar excepción en Windows Defender
- Es común en ejecutables sin firma digital

## 📦 Distribución

### Crear ZIP para distribución
```bash
# Comprimir el ejecutable
7z a FACOT_4.0_v4.0.zip dist\FACOT_4.0.exe README_EJECUTABLE.md
```

### Crear Instalador (Opcional)
Usar Inno Setup para crear un instalador profesional.

## 📝 Notas

- El ejecutable incluye todas las dependencias
- Tamaño aproximado: 80-150 MB
- Compatible con Windows 10/11
- No requiere Python instalado
- Primera ejecución puede tardar más

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs en `build/`
2. Reporta en [GitHub Issues](https://github.com/zoeccivil/FACOT_4.0/issues)
