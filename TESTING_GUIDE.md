# Guía de Pruebas - Dashboard y Subida de PDFs

## Resumen
Esta guía proporciona pasos detallados para probar la funcionalidad implementada del Dashboard y la subida automática de PDFs a Firebase Storage.

## Pre-requisitos

1. **Configuración de Firebase**:
   - Archivo de credenciales Firebase configurado
   - Storage bucket configurado en Firebase
   - Permisos de lectura/escritura en Storage

2. **Dependencias**:
   ```bash
   pip install pyqtgraph PyQt6 PyQt6-WebEngine firebase-admin
   ```

3. **Datos de prueba**:
   - Al menos una empresa configurada
   - Facturas 'emitida' del mes actual
   - Cotizaciones del mes actual

## Pruebas del Dashboard

### 1. Verificar Ingresos Totales

**Objetivo**: Confirmar que solo se cuentan facturas 'emitida' del mes actual

**Pasos**:
1. Abrir la aplicación y seleccionar una empresa
2. Navegar a la pestaña Dashboard
3. Verificar el valor mostrado en "Ingresos Totales"

**Validación**:
- Buscar en consola: `[DASHBOARD] Ingresos Totales (mes actual): $X.XX de N facturas`
- Verificar que N coincide con el número de facturas 'emitida' del mes
- Confirmar que facturas tipo 'gasto' o 'compra' no se incluyen

### 2. Verificar Facturas Pendientes

**Objetivo**: Confirmar conteo de facturas no pagadas

**Pasos**:
1. Verificar facturas con status != 'paid'
2. Revisar valor en "Facturas Pendientes"

**Validación**:
- Log: `[DASHBOARD] Facturas Pendientes: $X.XX de N facturas`
- Confirmar que solo incluye facturas 'emitida' del mes actual no pagadas

### 3. Verificar Clientes Activos

**Objetivo**: Confirmar conteo único de clientes

**Pasos**:
1. Revisar facturas del mes actual
2. Contar clientes únicos manualmente (por RNC o nombre)
3. Comparar con valor mostrado

**Validación**:
- Log: `[DASHBOARD] Clientes Activos (mes actual): N`
- N debe ser igual al número de clientes distintos (RNC/nombre)
- Nombres duplicados con mismo RNC deben contar como 1

### 4. Verificar Cotizaciones

**Objetivo**: Confirmar conteo de cotizaciones del mes

**Pasos**:
1. Contar cotizaciones creadas este mes
2. Comparar con valor mostrado

**Validación**:
- Log: `[DASHBOARD] Cotizaciones (mes actual): N`
- N debe coincidir con cotizaciones del mes actual

### 5. Verificar Actividad Reciente

**Objetivo**: Confirmar eventos reales y tiempos relativos

**Pasos**:
1. Crear una nueva factura
2. Esperar 1 minuto
3. Crear una cotización
4. Refrescar Dashboard

**Validación**:
- Debe mostrar hasta 10 eventos
- Eventos ordenados por fecha (más reciente primero)
- Tiempos relativos correctos:
  - "Hace un momento" para < 1 minuto
  - "Hace X minuto(s)" para < 1 hora
  - "Hace X hora(s)" para < 1 día
  - "Hace X día(s)" para < 1 semana
- Log: `[DASHBOARD] Actividad Reciente: N eventos mostrados`

### 6. Verificar Gráfico Mensual

**Objetivo**: Confirmar datos del año actual

**Pasos**:
1. Si pyqtgraph está instalado:
   - Verificar que el gráfico muestra 12 meses
   - Confirmar barras para meses con ventas
2. Si pyqtgraph NO está instalado:
   - Debe mostrar placeholder con instrucción de instalación

**Validación**:
- Datos solo de facturas 'emitida'
- Solo datos del año actual
- Barras proporcionales a ventas por mes

## Pruebas de Subida de PDFs

### 1. Subida de PDF de Factura

**Objetivo**: Verificar subida a Storage y metadatos en Firestore

**Pasos**:
1. Crear nueva factura con al menos un ítem
2. Hacer clic en "Vista Previa / PDF"
3. En el diálogo de vista previa, hacer clic en "Exportar a PDF"
4. Guardar el PDF con un nombre

**Validación - Logs**:
```
[PDF-UPLOAD] Subiendo /ruta/local.pdf a factura/Empresa_Nombre/2025/12/B0100000001.pdf...
[PDF-UPLOAD] storage_path=factura/Empresa_Nombre/2025/12/B0100000001.pdf, url=https://... (público)
[PDF-UPLOAD] Metadatos guardados en invoice X: path=factura/Empresa_Nombre/2025/12/B0100000001.pdf
```

**Validación - Firebase Console**:
1. Abrir Firebase Console → Storage
2. Navegar a `factura/Empresa_Nombre/2025/12/`
3. Confirmar que existe el archivo PDF
4. Verificar que se puede descargar

**Validación - Firestore**:
1. Abrir Firebase Console → Firestore
2. Navegar a `invoices/{invoice_id}`
3. Verificar campos:
   - `pdf_storage_path`: `factura/Empresa_Nombre/2025/12/B0100000001.pdf`
   - `pdf_url`: URL completa
   - `updated_at`: timestamp reciente
   - `updated_by`: usuario actual

### 2. Subida de PDF de Cotización

**Objetivo**: Similar a factura pero para cotizaciones

**Pasos**:
1. Crear nueva cotización
2. Exportar a PDF desde vista previa
3. Guardar

**Validación - Logs**:
```
[PDF-UPLOAD] Subiendo /ruta/local.pdf a cotizacion/Empresa_Nombre/2025/12/COT-EMP-000001.pdf...
[PDF-UPLOAD] storage_path=cotizacion/Empresa_Nombre/2025/12/COT-EMP-000001.pdf, url=https://... (público)
[PDF-UPLOAD] Metadatos guardados en quotation X: path=cotizacion/Empresa_Nombre/2025/12/COT-EMP-000001.pdf
```

**Validación - Firestore**:
- Colección: `quotations/{quotation_id}`
- Campos: `pdf_storage_path`, `pdf_url`

### 3. Sanitización de Nombres

**Objetivo**: Confirmar sanitización correcta

**Prueba con empresa**: "Constructora & Servicios (SRL)"

**Resultado esperado**:
- Ruta: `factura/Constructora__Servicios__SRL_/...`
- Solo caracteres: `[a-zA-Z0-9_-]`

### 4. URLs Firmadas (Fallback)

**Objetivo**: Verificar fallback a URLs firmadas

**Escenario**: Storage bucket con reglas que no permiten acceso público

**Validación**:
- Log: `[PDF-UPLOAD] No se pudo hacer público, usando URL firmada: ...`
- URL debe incluir parámetros de firma
- URL debe ser válida por 1 año

## Pruebas de Refrescos en InvoiceTab

### 1. Refresco de Vencimiento

**Objetivo**: Confirmar actualización del vencimiento desde backend

**Pasos**:
1. Cambiar empresa seleccionada
2. Observar campo "Vencimiento"

**Validación**:
- Log: `[ITAB-DUE] Refresh from backend for company_id=X -> YYYY-MM-DD`
- Log: `[ITAB-DUE] Prefill widget invoice_due_date <- YYYY-MM-DD`
- Campo "Vencimiento" debe mostrar fecha configurada en empresa

### 2. Refresco tras NCFConfigDialog

**Objetivo**: Verificar actualización automática de NCF y vencimiento

**Pasos**:
1. Navegar a pestaña Facturas
2. Menú → Herramientas → Configurar Secuencias NCF
3. Modificar secuencia NCF para tipo B01
4. Modificar invoice_due_date
5. Guardar cambios (Aceptar)

**Validación - Logs**:
```
[MAINWINDOW] NCFConfigDialog cerrado con Accepted - InvoiceTab refrescado
[ITAB-NCF-PREVIEW] Refrescando NCF y vencimiento tras configuración...
[ITAB-DUE] Refresh from backend for company_id=X -> YYYY-MM-DD
```

**Validación - UI**:
- Campo "NCF Asignado" debe mostrar el nuevo preview
- Campo "Vencimiento" debe mostrar la nueva fecha
- NO es necesario cambiar de pestaña o reiniciar

### 3. Cambio de Empresa

**Objetivo**: Verificar que cambiar empresa actualiza todo

**Pasos**:
1. Seleccionar empresa A
2. Verificar NCF y vencimiento
3. Cambiar a empresa B
4. Verificar que NCF y vencimiento cambian

**Validación**:
- `refresh_company_due_date()` se llama automáticamente
- NCF muestra secuencia de empresa B
- Vencimiento muestra configuración de empresa B

## Casos de Error

### 1. Sin Credenciales Firebase

**Escenario**: Firebase no configurado

**Resultado esperado**:
- Log: `[PDF-UPLOAD] ERROR: Storage no disponible`
- PDF se guarda localmente pero no se sube
- NO se debe crashear la aplicación

### 2. Sin invoice_id/quotation_id

**Escenario**: Preview antes de guardar documento

**Resultado esperado**:
- Log: `[PDF-UPLOAD] No se puede subir: falta logic o invoice_id`
- PDF se guarda localmente
- No se sube a Storage (esperado)

### 3. Error de Red

**Escenario**: Sin conexión a internet

**Resultado esperado**:
- Log: `[PDF-UPLOAD] ERROR subiendo archivo: ...`
- Stack trace en consola
- Mensaje de error NO bloquea guardado local

### 4. Archivo Local No Existe

**Escenario**: Ruta de archivo inválida

**Resultado esperado**:
- Log: `[PDF-UPLOAD] ERROR: Archivo local no existe: /ruta/invalida`
- No intenta subir
- No se guardan metadatos

## Checklist de Validación Final

- [ ] Dashboard muestra métricas correctas del mes actual
- [ ] Solo facturas 'emitida' se cuentan en ingresos
- [ ] Clientes Activos cuenta únicos correctamente
- [ ] Actividad Reciente muestra 10 eventos con tiempos relativos
- [ ] PDFs de facturas se suben a Storage correctamente
- [ ] PDFs de cotizaciones se suben a Storage correctamente
- [ ] Metadatos (pdf_storage_path, pdf_url) se guardan en Firestore
- [ ] Rutas en Storage siguen formato tipo/empresa/año/mes/numero.pdf
- [ ] Nombres de empresa se sanitizan correctamente
- [ ] URLs públicas o firmadas funcionan
- [ ] Refrescos de NCF y vencimiento funcionan tras NCFConfigDialog
- [ ] Cambio de empresa actualiza NCF y vencimiento
- [ ] Logs [DASHBOARD], [PDF-UPLOAD], [ITAB-DUE] aparecen correctamente
- [ ] Manejo de errores no crashea la aplicación

## Logs de Depuración a Monitorear

```bash
# Dashboard
[DASHBOARD] Filtered X 'emitida' invoices from Y total
[DASHBOARD] Ingresos Totales (mes actual): $X.XX de N facturas
[DASHBOARD] Facturas Pendientes: $X.XX de N facturas
[DASHBOARD] Clientes Activos (mes actual): N
[DASHBOARD] Cotizaciones (mes actual): N
[DASHBOARD] Actividad Reciente: N eventos mostrados

# PDF Upload
[PDF-UPLOAD] Subiendo /path a storage_path...
[PDF-UPLOAD] storage_path=..., url=... (público/firmada)
[PDF-UPLOAD] Metadatos guardados en invoice/quotation X: path=...

# InvoiceTab
[ITAB-DUE] Refresh from backend for company_id=X -> YYYY-MM-DD
[ITAB-DUE] Prefill widget invoice_due_date <- YYYY-MM-DD
[ITAB-NCF-PREVIEW] Refrescando NCF y vencimiento tras configuración...

# MainWindow
[MAINWINDOW] NCFConfigDialog cerrado con Accepted - InvoiceTab refrescado
```

## Notas

1. En entornos headless (sin display), pyqtgraph puede fallar. El código tiene fallback.
2. URLs firmadas tienen expiración de 1 año (SIGNED_URL_EXPIRY_SECONDS).
3. Si preview se hace antes de guardar documento, invoice_id es None y no se sube PDF.
4. Sanitización usa regex `[^a-zA-Z0-9_-]` → `_`.
5. Tiempos relativos asumen timezone local.
