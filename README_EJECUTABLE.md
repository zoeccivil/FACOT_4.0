# FACOT 4.0 - Ejecutable para Windows

## 📦 Acerca de este Ejecutable

**FACOT 4.0** es un sistema completo de facturación electrónica con soporte para NCF dominicano y sincronización con Firebase.

- ✅ No requiere instalación de Python
- ✅ Incluye todas las dependencias
- ✅ Compatible con Windows 10/11
- ✅ Conexión directa a Firebase/Firestore

## 🚀 Instalación Rápida

1. **Descargar** `FACOT_4.0.exe`
2. **Ejecutar** el archivo (doble clic)
3. **Configurar** en el primer inicio

⚠️ **Nota**: Windows Defender puede mostrar advertencia. Esto es normal para ejecutables sin firma digital. Haz clic en "Más información" → "Ejecutar de todas formas".

## ⚙️ Configuración Inicial

### Primera Ejecución

Al iniciar por primera vez, el programa solicitará:

1. **Credenciales de Firebase**
   - Archivo JSON de credenciales
   - Se puede obtener desde Firebase Console

2. **Configuración de Empresa**
   - Nombre de la empresa
   - RNC
   - Dirección

3. **Rutas de Trabajo**
   - Carpeta para plantillas
   - Carpeta para facturas generadas
   - Carpeta para anexos

## 📋 Funcionalidades

- ✅ Emisión de facturas con NCF automático
- ✅ Gestión de cotizaciones
- ✅ Catálogo de productos/servicios
- ✅ Directorio de clientes
- ✅ Reportes mensuales (PDF y Excel)
- ✅ Cálculo de retenciones
- ✅ Sincronización en la nube (Firebase)
- ✅ Backup automático
- ✅ Soporte multi-empresa
- ✅ Multi-moneda (RD$, USD, EUR)

## 🔧 Solución de Problemas

### El programa no inicia

1. **Ejecutar como administrador** (clic derecho → "Ejecutar como administrador")
2. Verificar que no haya otra instancia abierta
3. Revisar el log en `%APPDATA%\FACOT\`

### Error de Firebase

- Verificar conexión a internet
- Confirmar que el archivo de credenciales sea válido
- Revisar permisos en Firebase Console

### Antivirus bloquea el ejecutable

1. Agregar excepción en Windows Defender:
   - Configuración → Virus y amenazas
   - Administrar configuración
   - Exclusiones → Agregar exclusión
   - Seleccionar `FACOT_4.0.exe`

### Pantalla en blanco o congelada

- Reiniciar el programa
- Limpiar caché: eliminar carpeta `%APPDATA%\FACOT\cache\`

## 💾 Ubicación de Archivos

El programa guarda sus datos en:

```
C:\Users\[TuUsuario]\AppData\Roaming\FACOT\
├── config.json              # Configuración general
├── logs\                    # Registros del programa
├── backups\                 # Backups automáticos
└── cache\                   # Archivos temporales
```

## 🔄 Actualización

Para actualizar a una nueva versión:
1. Descargar el nuevo `FACOT_4.0.exe`
2. Reemplazar el archivo anterior
3. La configuración se mantiene automáticamente

## 📞 Soporte y Contacto

- **Issues**: [GitHub Issues](https://github.com/zoeccivil/FACOT_4.0/issues)
- **Documentación**: [Guía Completa](https://github.com/zoeccivil/FACOT_4.0)

## 📄 Licencia

Copyright © 2025 - FACOT 4.0
