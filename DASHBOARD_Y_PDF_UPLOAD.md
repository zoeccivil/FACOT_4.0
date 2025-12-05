# Dashboard y Subida Automática de PDFs a Firebase Storage

## Resumen

Este documento describe la implementación del Dashboard completo y la funcionalidad de subida automática de PDFs de facturas y cotizaciones a Firebase Storage con registro de metadatos en Firestore.

## 1. Dashboard (dashboard_tab.py)

### Métricas Implementadas

#### 1.1 Ingresos Totales
- **Filtro**: Solo facturas con `invoice_type.lower() == 'emitida'`
- **Período**: Mes actual (basado en `invoice_date`)
- **Cálculo**: Suma de `total_amount` de todas las facturas 'emitida' del mes
- **Log**: `[DASHBOARD] Ingresos Totales (mes actual): $X.XX de N facturas`

#### 1.2 Facturas Pendientes
- **Filtro**: Facturas 'emitida' del mes actual con `status != 'paid'`
- **Cálculo**: Suma de `total_amount` de facturas pendientes
- **Log**: `[DASHBOARD] Facturas Pendientes: $X.XX de N facturas`

#### 1.3 Clientes Activos
- **Método**: `_calculate_active_clients()`
- **Lógica**: Cuenta clientes únicos en facturas 'emitida' del mes actual
- **Identificación**: Por RNC (prioritario) o por nombre del cliente
- **Normalización**: RNC y nombres se convierten a mayúsculas para evitar duplicados
- **Retorno**: Número de clientes distintos
- **Log**: `[DASHBOARD] Clientes Activos (mes actual): N`

#### 1.4 Cotizaciones
- **Filtro**: Cotizaciones del mes actual basadas en `quotation_date`
- **Cálculo**: Conteo simple de cotizaciones creadas en el mes
- **Log**: `[DASHBOARD] Cotizaciones (mes actual): N`

### Actividad Reciente

#### Método: `_update_recent_activity()`

**Proceso**:
1. Recopila eventos de facturas y cotizaciones
2. Para cada factura 'emitida':
   - Extrae timestamp (`created_at`, `updated_at` o `invoice_date`)
   - Crea evento con icono 📄, texto descriptivo y tiempo relativo
3. Para cada cotización:
   - Extrae timestamp (`created_at`, `updated_at` o `quotation_date`)
   - Crea evento con icono 📝, texto descriptivo y tiempo relativo
4. Ordena eventos por timestamp (más recientes primero)
5. Muestra los 10 eventos más recientes

**Formato de tiempo relativo** (`_format_relative_time()`):
- < 1 minuto: "Hace un momento"
- < 1 hora: "Hace X minuto(s)"
- < 1 día: "Hace X hora(s)"
- < 1 semana: "Hace X día(s)"
- < 4 semanas: "Hace X semana(s)"
- Más antiguo: Muestra fecha (DD/MM/YYYY)

**Log**: `[DASHBOARD] Actividad Reciente: N eventos mostrados`

### Gráfico Mensual

- **Datos**: Ventas por mes del año actual
- **Filtro**: Solo facturas 'emitida'
- **Biblioteca**: pyqtgraph (opcional)
- **Fallback**: Si pyqtgraph no está instalado, muestra placeholder con instrucciones
- **Instalación**: `pip install pyqtgraph`

### Método Helper: `_parse_date()`

Parsea múltiples formatos de fecha:
- Objetos datetime
- Strings ISO 8601 (con soporte para timezone)
- Formatos comunes: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY

## 2. Subida de PDF a Firebase Storage

### FirebaseDataAccess

#### 2.1 `upload_file_to_storage(local_path, storage_path) -> Optional[str]`

**Proceso**:
1. Verifica que el archivo local existe
2. Sube el archivo a Firebase Storage en la ruta especificada
3. Detecta content type (application/pdf para PDFs)
4. Intenta hacer el blob público
5. Si falla, genera URL firmada (válida 1 año)
6. Retorna URL pública o firmada

**Logs**:
- `[PDF-UPLOAD] storage_path=..., url=... (público)` - Si se pudo hacer público
- `[PDF-UPLOAD] storage_path=..., url=... (firmada)` - Si se usó URL firmada
- `[PDF-UPLOAD] ERROR: ...` - En caso de error

#### 2.2 `set_invoice_pdf_info(invoice_id, storage_path, url)`

Guarda metadatos en Firestore usando merge:
- `pdf_storage_path`: Ruta en Storage
- `pdf_url`: URL del PDF
- `updated_at`: Timestamp de actualización
- `updated_by`: Usuario que actualizó

**Documento**: `invoices/{invoice_id}`

#### 2.3 `set_quotation_pdf_info(quotation_id, storage_path, url)`

Similar a facturas, pero para cotizaciones.

**Documento**: `quotations/{quotation_id}`

### Estructura de Rutas en Storage

#### Facturas
```
factura/{empresa_nombre_sanitizado}/{año}/{mes}/{ncf_o_numero}.pdf
```

**Ejemplo**:
```
factura/Constructora_Retro_SRL/2025/12/B0100000001.pdf
```

#### Cotizaciones
```
cotizacion/{empresa_nombre_sanitizado}/{año}/{mes}/{numero}.pdf
```

**Ejemplo**:
```
cotizacion/Constructora_Retro_SRL/2025/12/COT-CON-000001.pdf
```

### Sanitización de Nombres

**Regla**: Solo caracteres alfanuméricos, guiones y guiones bajos
- Patrón regex: `[^a-zA-Z0-9_-]`
- Reemplazo: `_`
- Ejemplo: "Constructora Retro SRL" → "Constructora_Retro_SRL"

### InvoicePreviewDialog y QuotationPreviewDialog

#### Cambios en `__init__`

Nuevos parámetros opcionales:
- `logic`: Referencia al backend (FirebaseDataAccess o HybridLogic)
- `invoice_id` / `quotation_id`: ID del documento guardado

#### Método `_upload_pdf_to_storage(local_pdf_path)`

**Proceso**:
1. Verifica que `logic` y `invoice_id`/`quotation_id` estén disponibles
2. Verifica que backend soporte los métodos necesarios
3. Construye ruta de Storage:
   - Sanitiza nombre de empresa
   - Extrae año/mes de la fecha del documento
   - Sanitiza NCF/número de documento
4. Llama `upload_file_to_storage()`
5. Si exitoso, llama `set_invoice_pdf_info()` o `set_quotation_pdf_info()`

**Integración**: Se llama automáticamente después de guardar PDF exitosamente en `finish_with_message()`

## 3. Refrescos en InvoiceTab

### 3.1 `refresh_company_due_date()`

**Propósito**: Actualizar el vencimiento fijo desde el backend

**Proceso**:
1. Obtiene empresa actual
2. Lee `invoice_due_date` desde:
   - Datos de company en memoria
   - Llamada a `get_company_details()` si no está disponible
3. Aplica fecha al widget usando `_set_invoice_due_date_widget()`
4. Si no hay fecha configurada, aplica vencimiento por defecto

**Logs**:
- `[ITAB-DUE] Refresh from backend for company_id=X -> YYYY-MM-DD`
- `[ITAB-DUE] No hay invoice_due_date configurado para company_id=X`

### 3.2 `refresh_after_ncf_config()`

**Propósito**: Refrescar UI después de configurar NCF

**Proceso**:
1. Refresca NCF preview llamando `_update_ncf_sequence()`
2. Refresca vencimiento llamando `refresh_company_due_date()`

**Log**: `[ITAB-NCF-PREVIEW] Refrescando NCF y vencimiento tras configuración...`

**Llamada desde**: `ui_mainwindow._abrir_configuracion_ncf()` después de cerrar `NCFConfigDialog` con `Accepted`

### Cambio en `on_company_change()`

Ahora llama `refresh_company_due_date()` en lugar de `_apply_default_due_date()` para consistencia con el backend.

## 4. Integración en ui_mainwindow.py

### Método `_abrir_configuracion_ncf()`

**Cambios**:
1. Captura resultado de `dialog.exec()`
2. Si resultado es `1` (QDialog.Accepted):
   - Llama `invoice_tab.refresh_after_ncf_config()`
   - Log: `[MAINWINDOW] NCFConfigDialog cerrado con Accepted - InvoiceTab refrescado`

## 5. Pruebas Recomendadas

### Dashboard
1. Verificar que solo cuenta facturas 'emitida' (no gastos ni compras)
2. Confirmar que métricas son del mes actual
3. Verificar conteo de clientes activos únicos
4. Confirmar que actividad reciente muestra eventos reales con tiempos relativos

### PDF Upload
1. Crear factura y guardar PDF → verificar subida a Storage
2. Confirmar que `pdf_storage_path` y `pdf_url` se guardan en Firestore
3. Verificar estructura de ruta: `factura/empresa/año/mes/numero.pdf`
4. Repetir con cotizaciones

### Refrescos
1. Cambiar vencimiento en NCFConfigDialog → verificar actualización inmediata
2. Cambiar secuencia NCF → verificar preview actualizado
3. Cambiar empresa → verificar vencimiento y NCF se actualizan

## 6. Instalación de pyqtgraph

```bash
pip install pyqtgraph
```

**Nota**: pyqtgraph requiere PyQt6, PyQt5, PySide2 o PySide6. El proyecto usa PyQt6.

En entornos headless (sin display), pyqtgraph puede fallar. El código tiene fallback para mostrar placeholder con instrucciones de instalación.

## 7. Logs de Depuración

### Dashboard
- `[DASHBOARD] Filtered X 'emitida' invoices from Y total`
- `[DASHBOARD] Ingresos Totales (mes actual): $X.XX de N facturas`
- `[DASHBOARD] Facturas Pendientes: $X.XX de N facturas`
- `[DASHBOARD] Clientes Activos (mes actual): N`
- `[DASHBOARD] Cotizaciones (mes actual): N`
- `[DASHBOARD] Actividad Reciente: N eventos mostrados`

### PDF Upload
- `[PDF-UPLOAD] Subiendo {local_path} a {storage_path}...`
- `[PDF-UPLOAD] storage_path=..., url=... (público/firmada)`
- `[PDF-UPLOAD] Metadatos guardados en invoice/quotation X: path=...`
- `[PDF-UPLOAD] ERROR: ...`

### InvoiceTab
- `[ITAB-DUE] Refresh from backend for company_id=X -> YYYY-MM-DD`
- `[ITAB-DUE] Prefill widget invoice_due_date <- YYYY-MM-DD`
- `[ITAB-NCF-PREVIEW] Refrescando NCF y vencimiento tras configuración...`

### MainWindow
- `[MAINWINDOW] NCFConfigDialog cerrado con Accepted - InvoiceTab refrescado`

## 8. Consideraciones de Seguridad

1. **URLs Firmadas**: Tienen expiración de 1 año. Considerar regenerar periódicamente.
2. **URLs Públicas**: Usar solo si el bucket lo permite. Preferir URLs firmadas para mayor control.
3. **Sanitización**: Nombres de empresa y archivos se sanitizan para prevenir path traversal.
4. **Validación**: Se verifica existencia de archivo local antes de subir.

## 9. Limitaciones Conocidas

1. **pyqtgraph en entornos headless**: No funciona sin display. Fallback a placeholder.
2. **Timezone**: Cálculos de tiempo relativo asumen timezone local. Considerar UTC para precisión.
3. **IDs de preview**: En preview antes de guardar, `invoice_id`/`quotation_id` son `None`, por lo que PDF no se sube automáticamente. Solo se sube cuando hay ID disponible.

## 10. Mejoras Futuras

1. Soporte para regenerar URLs firmadas expiradas
2. Thumbnails de PDFs en actividad reciente
3. Notificaciones al usuario tras subida exitosa
4. Retry automático en caso de fallo de red
5. Caché local de PDFs descargados
6. Soporte para múltiples idiomas en tiempos relativos
