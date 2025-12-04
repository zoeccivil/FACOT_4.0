# FACOT - Sistema de Gestión de Facturas y Cotizaciones

![Versión](https://img.shields.io/badge/versión-2.4-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Licencia](https://img.shields.io/badge/licencia-MIT-orange.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

## 📋 Descripción

FACOT es un sistema completo de gestión de facturas y cotizaciones diseñado para empresas en República Dominicana. El sistema ofrece una solución robusta para la administración de documentos fiscales, cumpliendo con las normativas de la DGII (Dirección General de Impuestos Internos).

### 🚀 Novedades v2.4 - Dashboard Moderno y Backend Firebase-Only

✨ **Dashboard Mejorado con Visualización de Datos**
- Interfaz moderna tipo Tailwind CSS con diseño card-based
- Gráfico interactivo de ingresos mensuales usando pyqtgraph
- 4 tarjetas de resumen: Ingresos Totales, Facturas Pendientes, Cotizaciones, Clientes
- Filtrado estricto de datos: solo ingresos (tipo "emitida"), excluye gastos
- Actualización automática al crear/editar facturas

✨ **Sistema de Auditoría Robusto**
- Log centralizado de TODAS las operaciones CRUD con timestamps
- Formato: `[timestamp] [level] Action | Details: {JSON}`
- Ubicación: `~/.facot/logs/facot_audit.log`
- Ejemplos de logs: 
  - `[2025-12-04 10:00:00] [INFO] CREATE Invoice ID: 105 | Details: {"type": "EMITIDA", "total": "5000.00"}`
  - `[2025-12-04 10:05:00] [WARNING] DELETE Invoice ID: 105`
- Ver documentación completa en [AUDIT_LOGGING.md](AUDIT_LOGGING.md)

✨ **Firebase-Only Backend (OBLIGATORIO)**
- La aplicación ahora REQUIERE Firebase para funcionar
- SQLite solo para herramientas de migración (no para runtime)
- Configuración guiada al primer inicio
- Prompt automático si Firebase no está configurado
- Ver guía completa en [FIREBASE_BACKEND.md](FIREBASE_BACKEND.md)

✨ **Constantes de Tipo de Factura**
- `INGRESO_TYPES = ["emitida"]` - Facturas de ingreso/ventas
- `EXPENSE_TYPES = ["gasto"]` - Facturas de gasto
- Filtrado consistente en todo el sistema

### 🆕 Novedades v2.3 - UI Mejorada

✨ **Menú Apariencias (Temas)**
- 5 temas disponibles: Claro, Oscuro, Medianoche, Coral, Alto Contraste
- Cambio de tema en vivo sin reiniciar
- Persistencia automática del tema seleccionado
- Soporte de accesibilidad (alto contraste)

✨ **Configurar Firebase desde Menú**
- Acceso directo: Herramientas → Configurar Firebase (Ctrl+Shift+F)
- Permite cambiar credenciales sin reiniciar completamente
- Validación de credenciales antes de guardar

✨ **Reportes de Ventas y Clientes**
- Reporte de ventas por período (agrupable por día, mes o producto)
- Reporte por cliente con totales y última factura
- Exportación a CSV y HTML
- Filtros por rango de fechas

✨ **Historial Solo Ingresos**
- El historial de facturas ahora muestra solo facturas de ingreso (ventas)
- Filtrado automático por tipo o prefijo NCF

✨ **Logos en Firebase Storage**
- Logos de plantillas se almacenan en Firebase Storage
- Cache local automático con fallback a logo local
- Sincronización transparente

### 🆕 Novedades v2.2 - Firestore-First

✨ **Runtime 100% Firestore**
- Todo el runtime usa Firestore (Firebase) exclusivamente
- SQLite solo para migraciones existentes y backups locales
- Sin uso de Realtime Database

✨ **NCF Transaccional con Firestore**
- Transacciones Firestore con reintentos automáticos
- NCFs únicos garantizados bajo concurrencia
- Corrector de secuencias automático

✨ **Backups Automáticos Diarios**
- Exportación diaria de colecciones a JSON local
- Retención configurable (30 días por defecto)
- Botones en UI para backup manual

✨ **Diálogo de Configuración Firebase**
- Configuración guiada al primer inicio
- Autocompletado de bucket desde credenciales
- Validación de credenciales antes de guardar

### 🆕 Novedades v2.1

✨ **Sistema de Auditoría Completo**
- Registro automático de todas las operaciones críticas
- Historial completo de cambios en facturas
- Trazabilidad total de NCF asignados

✨ **NCF Sin Duplicados**
- Transacciones Firestore (v2.2) / BEGIN EXCLUSIVE SQLite (v2.1)
- Validado con tests de concurrencia
- Imposible generar NCF duplicados

✨ **Sistema de Email Profesional**
- Envío de facturas por email con adjuntos
- Soporte SMTP/TLS y SendGrid
- Registro de todos los envíos
- Vista previa de emails

✨ **79 Tests Automatizados**
- Cobertura completa del backend
- Tests de integración
- Tests de concurrencia
- CI/CD con GitHub Actions

### Características Principales

✅ **Gestión de Facturas**
- Facturas emitidas (ingresos)
- Facturas de gastos
- Soporte para múltiples monedas (RD$, USD, EUR)
- Cálculo automático de ITBIS (18%)
- Conversión automática a pesos dominicanos
- **🆕 NCF automático con transacciones Firestore**
- **🆕 Auditoría automática de cambios**

✅ **Gestión de Cotizaciones**
- Creación de cotizaciones profesionales
- Conversión de cotizaciones a facturas
- Plantillas personalizables

✅ **Comprobantes Fiscales (NCF)**
- B01 - Crédito Fiscal
- B02 - Consumidor Final
- B04 - Nota de Crédito
- B14 - Régimen Especial
- B15 - Gubernamental
- **🆕 Secuencias almacenadas en Firestore (ncf_sequence_configs)**
- **🆕 Corrector automático de inconsistencias**

✅ **Arquitectura Firebase-First (v2.2)**
- **Firestore**: Base de datos principal para runtime
- **SQLite**: Solo para migraciones y backups locales
- **Backups automáticos**: JSON diarios con retención 30 días

✅ **Reportes y Análisis**
- Reportes mensuales en PDF y Excel
- Cálculo de retenciones e impuestos
- Análisis por terceros (clientes/proveedores)
- Estadísticas del dashboard en tiempo real

✅ **Gestión de Anexos**
- Carga y organización automática de comprobantes
- Editor de imágenes integrado
- Visualización de PDFs
- Estructura de carpetas automatizada

✅ **Interfaz de Usuario Mejorada**
- Indicador de conexión visual
- Atajos de teclado (Ctrl+N, Ctrl+D, Supr, F2)
- Importación desde Excel/CSV
- Drag-and-drop para reordenar items
- Descuentos por línea

## 🚀 Inicio Rápido

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Sistema operativo: Windows, Linux o macOS
- Cuenta de Firebase (para Firestore)

### Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/zoeccivil/FACOT_2.0.git
cd FACOT_2.0
```

2. **Crear entorno virtual (recomendado)**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar Firebase**

   Al iniciar la aplicación por primera vez, aparecerá un diálogo para configurar Firebase:
   
   - Selecciona el archivo JSON de credenciales (Service Account)
   - El bucket de storage se autocompleta
   - Click en "Guardar y conectar"
   
   Alternativamente, configura variables de entorno (ver `.env.example`):
   ```bash
   cp .env.example .env
   # Editar .env con tus valores
   ```

5. **Ejecutar la aplicación**
```bash
python main.py
```

### Configuración de Firebase

Ver [FIREBASE_SETUP.md](FIREBASE_SETUP.md) para instrucciones detalladas sobre:
- Crear proyecto Firebase
- Obtener credenciales
- Configurar Firestore y Storage

### 🚀 Inicio Rápido - Demo del Backend

Prueba las nuevas funcionalidades de auditoría y NCF:

```bash
# Ver demo completo del backend
python demo_backend.py
```

**Salida esperada:**
```
✅ 5 facturas creadas con NCF automático
✅ Sin duplicados: True
✅ 12 registros de auditoría
✅ TODO FUNCIONANDO CORRECTAMENTE
```

## 📚 Documentación

### Documentación Principal

- **[FIREBASE_SETUP.md](FIREBASE_SETUP.md)** - Configuración completa de Firebase
- **[NCF_SEQUENCE.md](NCF_SEQUENCE.md)** - Sistema de secuencias NCF con Firestore
- **[BACKUPS.md](BACKUPS.md)** - Sistema de backups automáticos
- **[CONFIG_DIALOG.md](CONFIG_DIALOG.md)** - Diálogo de configuración de Firebase
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitectura del sistema
- **[.env.example](.env.example)** - Variables de entorno disponibles

### Guías Adicionales

- **[INSTALL.md](INSTALL.md)** - Guía de instalación detallada
- **[USER_GUIDE.md](USER_GUIDE.md)** - Manual de usuario
- **[FAQ.md](FAQ.md)** - Preguntas frecuentes
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Guía para contribuir

## 🏗️ Arquitectura del Sistema

```
FACOT/
├── main.py                    # Punto de entrada principal
├── logic.py                   # Lógica de negocio y BD
├── ui_mainwindow.py          # Interfaz principal
├── config_facot.py           # Configuración
├── services/                  # Servicios del sistema
│   ├── company_profile_service.py
│   ├── unit_resolver.py
│   └── ...
├── data_access/              # Capa de acceso a datos
│   ├── sqlite_data_access.py
│   ├── firebase_data_access.py
│   └── data_access_factory.py
├── dialogs/                  # Ventanas de diálogo
│   ├── invoice_preview_dialog.py
│   ├── quotation_preview_dialog.py
│   └── ...
├── widgets/                  # Componentes UI personalizados
│   └── connection_status_bar.py
├── templates/                # Plantillas HTML para documentos
│   ├── invoice_template.html
│   └── quotation_template.html
└── firebase/                 # Configuración Firebase
    ├── firebase-credentials.json
    └── firestore.rules
```

## 💻 Uso del Sistema

### Configuración Inicial

1. **Seleccionar Base de Datos**
   - Al iniciar, el sistema pedirá seleccionar un archivo `.db`
   - Puede crear una nueva base de datos o usar una existente

2. **Configurar Empresa**
   - Ir a `Configuración` → `Gestión de Empresas`
   - Agregar información de la empresa (nombre, RNC, dirección)
   - Configurar rutas de plantillas y carpetas de salida

3. **Configurar Firebase (Opcional)**
   - Para trabajo en la nube, configurar credenciales Firebase
   - Ver [README_PR6.md](README_PR6.md) para detalles

### Operaciones Comunes

#### Crear una Factura

1. Seleccionar la empresa activa
2. Clic en `Nueva Factura` o presionar `Ctrl+N`
3. Seleccionar tipo de factura (Emitida o Gasto)
4. Llenar datos del cliente
5. Agregar items/detalles
6. Guardar

#### Generar Reportes

1. Ir a `Reportes` → `Reporte Mensual`
2. Seleccionar mes y año
3. Elegir formato (PDF o Excel)
4. Generar y guardar

#### Calcular Retenciones

1. Ir a `Herramientas` → `Calculadora de Retenciones`
2. Seleccionar período
3. Marcar facturas a incluir
4. Calcular y generar reporte

### Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+N` | Nueva factura/ítem |
| `Ctrl+S` | Guardar |
| `Ctrl+D` | Duplicar ítem |
| `Ctrl+V` | Pegar desde Excel |
| `Supr` | Eliminar ítem |
| `F2` | Editar ítem |
| `F5` | Actualizar dashboard |

## 🔄 Mejoras Pendientes

Según el archivo [SUGERENCIAS.txt](SUGERENCIAS.txt), las siguientes características están planificadas:

### Gestión de Categorías
- [ ] Colores/etiquetas por categoría
- [ ] Impuesto por categoría (ITBIS configurable)
- [ ] Márgenes por categoría (cálculo automático de precio de venta)
- [ ] Unidades favoritas por categoría

### Sistema de Precios
- [ ] Múltiples listas de precios (price1, price2, price3)
- [ ] Selección de lista de precios por cliente
- [ ] Selección de lista de precios por documento

### Importación/Exportación
- [x] Exportación a Excel (implementado)
- [x] Exportación a PDF (implementado)
- [ ] Importación masiva desde CSV
- [ ] Importación de items desde Excel

### Auditoría
- [ ] Campos `created_at` en todas las entidades
- [ ] Campos `updated_at` en todas las entidades
- [ ] Campo `created_by` para multi-usuario
- [ ] Historial de cambios

### Validaciones Mejoradas
- [x] Validación de cliente y RNC (implementado)
- [x] Validación de items (implementado)
- [x] Validación de importes (implementado)
- [x] Cálculo automático de montos (implementado)

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

### Estándares de Código

- Seguir PEP 8 para Python
- Documentar funciones y clases
- Agregar pruebas para nuevas características
- Mantener la documentación actualizada

## 📊 Estadísticas del Proyecto

```
Total de Entregas:     4 fases completadas
Total de Commits:      19+ commits
Total de Archivos:     32+ archivos

Código de Producción:  2,664+ líneas
Documentación:         2,502+ líneas
Gran Total:            5,166+ líneas

Seguridad:             0 vulnerabilidades (CodeQL)
Compatibilidad:        100% hacia atrás
Idioma:                100% español
```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Contacto

**Proyecto FACOT**
- GitHub: [@zoeccivil](https://github.com/zoeccivil)
- Repositorio: [FACOT_GIT](https://github.com/zoeccivil/FACOT_GIT)

## 🙏 Agradecimientos

- Comunidad de desarrolladores Python
- Usuarios y testers del sistema FACOT
- Contribuidores del proyecto

---

**Última Actualización:** 2025-11-09
**Versión:** 2.0
**Estado:** ✅ ACTIVO Y EN DESARROLLO
