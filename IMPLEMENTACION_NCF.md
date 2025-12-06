# Implementación de Secuencias NCF y Vencimiento Fijo

## Resumen de Cambios

Esta implementación añade soporte completo para:
1. **Secuencias NCF persistentes**: Preview vs consumo transaccional
2. **Vencimiento fijo de facturas**: Por empresa en Firestore
3. **Logs detallados**: En todos los métodos críticos
4. **Diálogo de configuración**: NCFConfigDialog para gestionar secuencias y vencimientos

## Archivos Modificados

### 1. `data_access/firebase_data_access.py`

**Métodos Nuevos Implementados:**

#### `_normalize_ncf_prefix(prefix3: str) -> str`
- Normaliza prefijos a formato estándar (B01, E31, etc.)
- Acepta: "B01", "01", "b01" → retorna "B01"
- Acepta: "E31", "31" → retorna "E31"

#### `_format_ncf(prefix3: str, seq_num: int) -> str`
- Formatea NCF según el prefijo:
  - NCF estándar (Bxx): `Prefix + 8 dígitos` (ej: B0100000123)
  - E-CF (E31): `E + tipo (2 dígitos) + 11 dígitos` (ej: E3100000000123)

#### `get_ncf_last_seq(company_id: int, prefix3: str) -> int`
- Obtiene la última secuencia asignada
- NO incrementa la secuencia
- Retorna 0 si no existe
- **Prints:**
  - `[SEQ get_ncf_last_seq] doc_path=...`
  - `[SEQ get_ncf_last_seq] exists=..., current=...`

#### `set_ncf_last_seq(company_id: int, prefix3: str, last_seq: int) -> bool`
- Establece la última secuencia (configuración manual)
- **Prints:**
  - `[SEQ set_ncf_last_seq] doc_path=...`
  - `[SEQ set_ncf_last_seq] before=...`
  - `[SEQ set_ncf_last_seq] after/guardado=...`

#### `get_ncf_preview(company_id: int, prefix3: str) -> str`
- Preview del próximo NCF SIN consumir
- **Prints:**
  - `[SEQ get_ncf_preview] company_id=..., prefix3=..., current=..., preview_result=...`

#### `allocate_next_ncf(company_id: int, prefix3: str) -> str`
- Asigna y consume el siguiente NCF (TRANSACCIONAL)
- Usa `@gcf.transactional` si está disponible
- Fallback NO-TXN si no hay soporte de transacciones
- **Prints:**
  - `[SEQ allocate_next_ncf] company_id=..., prefix3=...`
  - `[SEQ allocate_next_ncf] before=..., after=..., allocated_ncf=...`
  - `[SEQ allocate_next_ncf NO-TXN] ...` (si usa fallback)

#### `get_company_due_date(company_id: int) -> str`
- Obtiene fecha de vencimiento fija
- Preferencia: `sequences/{id}_meta` → `companies/{id}`
- **Prints:**
  - `[DUE get_company_due_date] Consultando sequences/{id}_meta`
  - `[DUE get_company_due_date] Encontrado en ...: ...`
  - `[DUE get_company_due_date] Consultando fallback companies/{id}`
  - `[DUE get_company_due_date] Valor final: ...`

#### `set_company_due_date(company_id: int, due: str) -> bool`
- Establece fecha de vencimiento fija
- Guarda en `sequences/{id}_meta` y espejo en `companies/{id}`
- **Prints:**
  - `[DUE set_company_due_date] Guardando en sequences/{id}_meta: ...`
  - `[DUE set_company_due_date] Guardado en sequences/{id}_meta: OK`
  - `[DUE set_company_due_date] Reflejando en companies/{id}: ...`
  - `[DUE set_company_due_date] Reflejado en companies/{id}: OK`

**Método Modificado:**

#### `get_next_ncf(company_id: int, ncf_type: str) -> str`
- LEGACY: Mantiene compatibilidad
- Delega a `allocate_next_ncf`

### 2. `logic.py`

**Métodos Modificados:**

#### `get_company_invoice_due_date(company_id: int) -> str`
- Ahora intenta `get_company_due_date` primero
- Fallback a `get_company_invoice_due_date` si existe
- Fallback genérico a `get_company_details`

#### `get_ncf_preview(company_id: int, prefix3: str) -> str`
- Delega a `data_access.get_ncf_preview` si existe
- Fallback a `get_next_ncf`

#### `allocate_next_ncf(company_id: int, prefix3: str) -> str`
- Delega a `data_access.allocate_next_ncf` si existe
- Fallback a `get_next_ncf`

### 3. `tabs/invoice_tab.py`

**Métodos Modificados:**

#### `_update_ncf_sequence()`
- **Print añadido:**
  - `[ITAB-NCF-PREVIEW] company_id=..., prefix3=..., preview=...`

#### `_on_next_ncf_clicked()`
- Obtiene preview antes del consumo (para logging)
- **Print añadido:**
  - `[ITAB-NCF-ALLOC] company_id=..., prefix3=..., before=..., after=..., assigned=...`

**Print Existente Preservado:**
- `[ITAB-DUE] Prefill widget invoice_due_date <- YYYY-MM-DD` (en `_set_invoice_due_date_widget`)

### 4. `dialogs/ncf_config_dialog.py` (NUEVO)

**Clase Creada:** `NCFConfigDialog`

Diálogo completo para configurar:
- Secuencias NCF por empresa y prefijo
- Vencimiento fijo de facturas por empresa

**Características:**
- Selector de empresas con cambio dinámico
- Tabla de secuencias para prefijos B01, B02, B14, B15, B16, E31
- Preview del próximo NCF en cada fila
- Botones para guardar secuencias y vencimiento

**Prints Implementados:**

#### `_on_company_changed(index)`
- `[NCF-CONFIG] Empresa cambiada: id=..., nombre=...`

#### `_save_due_date()`
- `[NCF-CONFIG] Intentando guardar vencimiento: empresa=..., fecha=...`
- `[NCF-CONFIG] set_company_due_date: OK=...`
- `[NCF-CONFIG] update_company_fields: OK=True`

#### `_save_sequences()`
- `[NCF-CONFIG] Guardando secuencia: empresa=..., prefix=..., seq=..., resultado=...`

## Esquema Firestore

### Colección `sequences`

#### Documentos de Secuencia NCF
- **Path:** `sequences/{companyId}ncf{PREFIX}`
- **Ejemplo:** `sequences/101ncfB01`
- **Estructura:**
```json
{
  "current": 123,
  "updated_at": "2025-12-05T12:00:00.000Z",
  "updated_by": "admin"
}
```

#### Documento Meta de Empresa
- **Path:** `sequences/{companyId}_meta`
- **Ejemplo:** `sequences/101_meta`
- **Estructura:**
```json
{
  "invoice_due_date": "2025-12-31",
  "updated_at": "2025-12-05T12:00:00.000Z",
  "updated_by": "admin"
}
```

### Colección `companies`

#### Documento de Empresa
- **Path:** `companies/{companyId}`
- **Campo adicional (espejo):** `invoice_due_date`

## Formato NCF

### NCF Estándar (B01-B16)
- **Formato:** `PREFIX + 8 dígitos`
- **Ejemplos:**
  - B01: `B0100000001`, `B0100000123`
  - B02: `B0200000001`
  - B15: `B1500000042`

### E-CF (E31)
- **Formato:** `E + tipo (2 dígitos) + 11 dígitos`
- **Total:** 14 caracteres
- **Ejemplos:**
  - E31: `E3100000000001`, `E3100000000123`

## Transaccionalidad

### Método `allocate_next_ncf`

**Con Transacciones (Preferido):**
```python
from google.cloud import firestore as gcf

@gcf.transactional
def increment_and_allocate(transaction):
    snapshot = sequence_ref.get(transaction=transaction)
    before = int(snapshot.get('current') or 0) if snapshot.exists else 0
    after = before + 1
    
    transaction.set(sequence_ref, {
        'current': after,
        'updated_at': datetime.utcnow().isoformat(),
        'updated_by': self.user_id
    }, merge=True)
    
    return self._format_ncf(prefix3, after)
```

**Fallback NO-TXN:**
- Se activa si `from google.cloud import firestore as gcf` falla
- Usa get/set secuencial (sin garantía de atomicidad)
- Logs marcados con `[SEQ allocate_next_ncf NO-TXN]`

## Normalización de company_id

Todos los métodos normalizan `company_id`:
- Aceptan `int` o `str`
- Firestore usa documentos con ID como `str`
- Intentan con `int` y fallback a `str` en consultas

## Casos de Uso

### 1. Preview de NCF (sin consumir)

```python
# En InvoiceTab al cambiar tipo de factura
preview = logic.get_ncf_preview(company_id=101, prefix3="B01")
# Resultado: "B0100000124"
# Log: [ITAB-NCF-PREVIEW] company_id=101, prefix3=B01, preview=B0100000124
# Log: [SEQ get_ncf_preview] company_id=101, prefix3=B01, current=123, preview_result=B0100000124
```

### 2. Consumo de NCF (incrementa secuencia)

```python
# Al presionar "Siguiente NCF"
ncf = logic.allocate_next_ncf(company_id=101, prefix3="B01")
# Resultado: "B0100000124"
# Log: [ITAB-NCF-ALLOC] company_id=101, prefix3=B01, before=B0100000123, after=B0100000124, assigned=B0100000124
# Log: [SEQ allocate_next_ncf] company_id=101, prefix3=B01
# Log: [SEQ allocate_next_ncf] before=123, after=124, allocated_ncf=B0100000124
```

### 3. Configuración Manual de Secuencia

```python
# En NCFConfigDialog
logic.set_ncf_last_seq(company_id=101, prefix3="B01", last_seq=200)
# Log: [NCF-CONFIG] Guardando secuencia: empresa=101, prefix=B01, seq=200, resultado=True
# Log: [SEQ set_ncf_last_seq] doc_path=sequences/101ncfB01
# Log: [SEQ set_ncf_last_seq] before=123
# Log: [SEQ set_ncf_last_seq] after/guardado=200
```

### 4. Configuración de Vencimiento Fijo

```python
# En NCFConfigDialog
logic.set_company_due_date(company_id=101, due="2025-12-31")
# Log: [NCF-CONFIG] Intentando guardar vencimiento: empresa=101, fecha=2025-12-31
# Log: [DUE set_company_due_date] Guardando en sequences/101_meta: 2025-12-31
# Log: [DUE set_company_due_date] Guardado en sequences/101_meta: OK
# Log: [DUE set_company_due_date] Reflejando en companies/101: 2025-12-31
# Log: [DUE set_company_due_date] Reflejado en companies/101: OK
```

### 5. Prellenado de Vencimiento en InvoiceTab

```python
# Al cargar empresa en InvoiceTab
due = logic.get_company_due_date(company_id=101)
# Resultado: "2025-12-31"
# Log: [DUE get_company_due_date] Consultando sequences/101_meta
# Log: [DUE get_company_due_date] Encontrado en sequences/101_meta: 2025-12-31
# Log: [ITAB-DUE] Prefill widget invoice_due_date <- 2025-12-31
```

## Compatibilidad

### Interfaces Mantenidas
- `get_next_ncf`: Ahora delega a `allocate_next_ncf` (mantiene compatibilidad)
- `HybridLogicWrapper`: No afectado
- `from firebase import get_firebase_client`: Sin cambios

### Código Existente
- `InvoiceHistoryTab`: Sin cambios
- `InvoiceTab._dedupe_ncf`: Preservado para compatibilidad
- `validate_ncf` y `split_ncf` en `logic.py`: Sin cambios

## Pruebas Realizadas

Ver `test_ncf_implementation.py`:
- ✓ Normalización de prefijos (B01, 01, E31, 31, etc.)
- ✓ Formateo de NCF (8 dígitos para Bxx, 13 para E31)
- ✓ Delegación correcta en LogicController
- ✓ Todos los métodos retornan valores esperados

## Consideraciones de Seguridad

1. **Transacciones:** Se usan cuando están disponibles para evitar colisiones
2. **Validación de entrada:** Todos los prefijos se normalizan
3. **Logs detallados:** Permiten auditar cada operación
4. **Fallback seguro:** Si fallan transacciones, se usa método NO-TXN con logging claro

## Logs Esperados

Ejemplo de flujo completo:

```
# Usuario selecciona empresa en NCFConfigDialog
[NCF-CONFIG] Empresa cambiada: id=101, nombre=Mi Empresa S.A.

# Usuario ve preview de B01
[SEQ get_ncf_last_seq] doc_path=sequences/101ncfB01
[SEQ get_ncf_last_seq] exists=True, current=123

# Usuario modifica secuencia a 200 y guarda
[NCF-CONFIG] Guardando secuencia: empresa=101, prefix=B01, seq=200, resultado=True
[SEQ set_ncf_last_seq] doc_path=sequences/101ncfB01
[SEQ set_ncf_last_seq] before=123
[SEQ set_ncf_last_seq] after/guardado=200

# Usuario guarda vencimiento
[NCF-CONFIG] Intentando guardar vencimiento: empresa=101, fecha=2025-12-31
[DUE set_company_due_date] Guardando en sequences/101_meta: 2025-12-31
[DUE set_company_due_date] Guardado en sequences/101_meta: OK
[DUE set_company_due_date] Reflejando en companies/101: 2025-12-31
[DUE set_company_due_date] Reflejado en companies/101: OK

# En InvoiceTab: preview de NCF
[ITAB-NCF-PREVIEW] company_id=101, prefix3=B01, preview=B0100000201
[SEQ get_ncf_preview] company_id=101, prefix3=B01, current=200, preview_result=B0100000201

# Usuario presiona "Siguiente NCF"
[ITAB-NCF-ALLOC] company_id=101, prefix3=B01, before=B0100000201, after=B0100000201, assigned=B0100000201
[SEQ allocate_next_ncf] company_id=101, prefix3=B01
[SEQ allocate_next_ncf] before=200, after=201, allocated_ncf=B0100000201

# Vencimiento se prellenó
[DUE get_company_due_date] Consultando sequences/101_meta
[DUE get_company_due_date] Encontrado en sequences/101_meta: 2025-12-31
[ITAB-DUE] Prefill widget invoice_due_date <- 2025-12-31
```

## Próximos Pasos

1. Ejecutar la aplicación y verificar logs en consola
2. Probar NCFConfigDialog desde el menú
3. Probar preview y consumo de NCF en InvoiceTab
4. Verificar que Firestore almacena correctamente los documentos
5. Validar formato de NCF en facturas guardadas
