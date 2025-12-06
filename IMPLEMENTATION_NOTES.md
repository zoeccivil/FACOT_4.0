# Implementation Notes: Invoice Management Improvements

## Summary

This implementation adds secure storage integration, PDF metadata persistence, and improved logo management to the FACOT invoice system.

## Changes Made

### 1. Backend Storage Methods (`logic.py`)

Added three new methods with Firebase integration and fallback handling:

- **`upload_file_to_storage(local_path, storage_path)`**: Uploads files to Firebase Storage, returns signed or public URL
- **`generate_signed_url_for_path(storage_path, days=7)`**: Generates temporary signed URLs for storage files
- **`set_invoice_pdf_info(invoice_id, storage_path, url, expires_at)`**: Persists PDF metadata to invoice records

All methods include:
- Fallback to SQLite when Firebase unavailable
- Automatic column creation if needed
- Comprehensive error handling and logging

### 2. Invoice Save Improvements (`tabs/invoice_tab.py`)

**Changes to `_save_invoice()` method:**
- Ensures `currency` and `exchange_rate` are always included in payload
- Handles multiple return types from `add_invoice()`: int, str, or dict
- Added debug prints: `[INV-PAYLOAD]` before save, `[INV-SAVE]` after save
- Consumes PDF metadata from `_preview_pdf_info` and persists via `set_invoice_pdf_info()`
- Robust invoice ID extraction with type conversion
- Initialized `_preview_pdf_info = None` in `__init__`

**Example debug output:**
```
[INV-PAYLOAD] Saving invoice with currency='USD', exchange_rate=58.5, total=1000.0, total_rd=58500.0
[INV-SAVE] add_invoice returned: {'id': 123} (type: dict), extracted invoice_id: 123
[INV-SAVE] PDF metadata persisted for invoice 123
```

### 3. Invoice Delete Robustness (`tabs/invoice_history_tab.py`)

Added `_delete_invoice(inv_id_or_record)` method that:
- Accepts dict (full record), int (id), or str (id)
- Extracts invoice ID safely regardless of input type
- Tries `logic.delete_factura` first, falls back to `data_access.delete_factura`
- Includes confirmation dialog
- Debug print: `[INV-DELETE] Received dict record, extracted id: 123`
- Comprehensive error handling

### 4. Logo Upload to Storage (`company_management_window.py`)

**Updated `_browse_logo()` method:**
- Attempts upload to Firebase Storage for existing companies
- Generates storage path: `logos/company_{id}.{ext}`
- Falls back to `copy_logo_to_assets` if upload fails or unavailable
- Shows appropriate success message with URL or relative path
- Saves URL directly to `logo_path` field if upload succeeds

**Updated `_prepare_logo_to_save()` method:**
- Tries storage upload for pending logos first
- Handles file:/// URLs and absolute paths
- Attempts upload before falling back to local copy
- Maintains relative paths and HTTP(S) URLs as-is
- Comprehensive debug logging

### 5. Logo Resolution with Signed URLs

**Invoice Preview (`dialogs/invoice_preview_dialog.py`):**
- Modified `_prepare_company_data_for_preview()` to detect storage-relative paths
- Requests signed URLs for paths that don't start with `http://`, `https://`, or `file:///`
- Uses `logic.generate_signed_url_for_path(path, days=7)`
- Maintains backward compatibility with existing file:// and http(s):// URLs

**Quotation Preview (`dialogs/quotation_preview_dialog.py`):**
- Applied same logic as invoice preview
- Ensures consistent logo handling across all preview dialogs

### 6. PDF Export with Storage Upload (`dialogs/invoice_preview_dialog.py`)

**Updated `_on_export_pdf()` method:**
- Uploads generated PDF to storage automatically
- Storage path format: `pdfs/invoice_{display_number}_{timestamp}.pdf`
- Generates metadata: `storage_path`, `url`, `expires_at` (1 year)
- Communicates metadata to parent via `parent._preview_pdf_info`
- Falls back silently if upload fails (local PDF still saved)

### 7. Template Editing Integration (`tabs/invoice_tab.py`)

**Updated `_on_edit_template()` method:**
- Opens `CompanyManagementWindow` instead of `TemplateEditorDialog`
- Pre-selects current company in the window
- Loads company details automatically
- Falls back to `TemplateEditorDialog` if CompanyManagementWindow unavailable
- Maintains backward compatibility

## Testing Instructions

### Test 1: Invoice Save with Currency and PDF Metadata

1. Open FACOT application
2. Navigate to Invoice Tab
3. Fill in invoice details:
   - Select company
   - Add client name and RNC
   - Select currency: USD or EUR
   - Enter exchange rate (e.g., 58.50)
   - Add line items
4. Generate preview (optional: export PDF)
5. Click "Guardar en Base de Datos"
6. Check console for:
   ```
   [INV-PAYLOAD] Saving invoice with currency='USD', exchange_rate=58.5, ...
   [INV-SAVE] add_invoice returned: ... extracted invoice_id: ...
   [INV-SAVE] PDF metadata persisted for invoice ...
   ```
7. Verify invoice saved with correct currency and exchange_rate in database

### Test 2: Invoice Delete with Different ID Types

1. Navigate to Invoice History Tab
2. Right-click on invoice (if context menu exists) or create UI button to test
3. Click Delete/Eliminar
4. Check console for:
   ```
   [INV-DELETE] Received dict record, extracted id: 123
   ```
   or
   ```
   [INV-DELETE] Received primitive id: 123 (type: int)
   ```
5. Confirm deletion dialog
6. Verify invoice is deleted and list refreshes

### Test 3: Logo Upload to Storage

1. Open Settings → Company Management (or via Edit Template button)
2. Select existing company
3. Click "Elegir logo..."
4. Select an image file (PNG, JPG, SVG)
5. Check console for:
   ```
   [COMPANY-LOGO] Selected logo file: ...
   [COMPANY-LOGO] Successfully uploaded to storage: https://...
   ```
   or (if Firebase unavailable):
   ```
   [COMPANY-LOGO] Falling back to copy_logo_to_assets
   [COMPANY-LOGO] Copied pending logo to assets: logos/...
   ```
6. Verify logo_path field shows URL or relative path
7. Click Save
8. Open invoice preview to verify logo appears

### Test 4: Logo Preview with Signed URLs

**Prerequisite:** Company must have logo stored in Firebase Storage with relative path

1. Open Invoice Tab
2. Select company with storage-based logo
3. Generate invoice preview
4. Check console for:
   ```
   [INV-LOGO] Attempting to generate signed URL for storage path: logos/company_123.png
   [INV-LOGO] Using signed URL: https://storage.googleapis.com/...
   ```
5. Verify logo appears in preview
6. Test same with quotation preview

### Test 5: Fallback When Storage Unavailable

**Setup:** Ensure Firebase credentials are not configured

1. Attempt logo upload
   - Expected: Falls back to `copy_logo_to_assets`
   - Console shows: `[LOGIC-STORAGE] Firebase upload failed: ...`
2. Generate invoice preview
   - Logo should still resolve via file:// URI
3. Export PDF
   - PDF saves locally
   - Console shows: `[INV-PDF] Upload returned None, PDF not uploaded to storage`

## Expected Console Output Samples

### Successful Storage Upload
```
[COMPANY-LOGO] Selected logo file: /path/to/logo.png
[LOGIC-STORAGE] File uploaded to logos/company_1.png: https://storage.googleapis.com/...
[COMPANY-LOGO] Successfully uploaded to storage: https://storage.googleapis.com/...
```

### Fallback to Local Storage
```
[COMPANY-LOGO] Selected logo file: /path/to/logo.png
[LOGIC-STORAGE] Firebase upload failed: [Errno 2] No such file or directory: 'firebase-credentials.json'
[LOGIC-STORAGE] upload_file_to_storage not available, file not uploaded: /path/to/logo.png
[COMPANY-LOGO] Falling back to copy_logo_to_assets
[COMPANY-LOGO] Copied pending logo to assets: logos/company_1_logo.png
```

### Invoice Save with PDF Metadata
```
[INV-PAYLOAD] Saving invoice with currency='USD', exchange_rate=58.5, total=1000.0, total_rd=58500.0
[DEBUG-LOGIC] NCF reservado: B01000001
[INV-SAVE] add_invoice returned: 42 (type: int), extracted invoice_id: 42
[INV-SAVE] PDF metadata persisted for invoice 42
Factura creada (ID: 42)
```

## Compatibility Notes

- All changes maintain backward compatibility with existing code
- Storage methods gracefully fall back to local file operations
- Works with both SQLite and Firebase backends
- No breaking changes to existing APIs

## Security Considerations

- Signed URLs expire after configured time (default: 7 days for logos, 1 year for PDFs)
- Storage paths are sanitized to prevent directory traversal
- All storage operations include error handling to prevent data loss
- Local fallback ensures functionality without Firebase

## Files Modified

1. `logic.py` - Added storage wrapper methods
2. `tabs/invoice_tab.py` - Enhanced save and template editing
3. `tabs/invoice_history_tab.py` - Added robust delete method
4. `company_management_window.py` - Logo upload with storage
5. `dialogs/invoice_preview_dialog.py` - Logo signed URLs and PDF upload
6. `dialogs/quotation_preview_dialog.py` - Logo signed URLs

## Dependencies

- Existing: PyQt6, Firebase Admin SDK (optional)
- No new dependencies added
- Firebase features are optional with local fallback
