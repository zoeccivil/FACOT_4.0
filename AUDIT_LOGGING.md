# Audit Logging System

## Overview

FACOT now includes a centralized audit logging system that tracks all significant data operations (Create, Read, Update, Delete) with timestamps and detailed context.

## Purpose

- **Audit Trail**: Track all data modifications for compliance and debugging
- **System Recovery**: Log can be used to rebuild indices or recover from data issues
- **Error Tracking**: All errors are logged with full context and stack traces

## Log Location

Logs are stored at: `~/.facot/logs/facot_audit.log`

## Log Format

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] Message | Details: {JSON}
```

Example:
```
[2025-12-04 08:07:04] [INFO] CREATE Invoice ID: 105 | Details: {"type": "EMITIDA", "total": "5000.00", "company_id": 1, "client": "ABC Corp"}
```

## Usage

### Basic Logging

```python
from utils.logger import get_audit_logger

logger = get_audit_logger()

# Log create operation
logger.log_create('Invoice', invoice_id, {'type': 'emitida', 'total': 5000.0})

# Log update operation
logger.log_update('Invoice', invoice_id, {'total': 6000.0})

# Log delete operation
logger.log_delete('Invoice', invoice_id, {'type': 'emitida', 'total': 5000.0})

# Log error
try:
    # operation
except Exception as e:
    logger.log_error('operation_name', e, {'context': 'additional info'})
```

### Convenience Functions

```python
from utils.logger import log_create, log_update, log_delete, log_error

# Shorter syntax
log_create('Invoice', 123, {'type': 'emitida'})
log_update('Invoice', 123, {'total': 6000.0})
log_delete('Invoice', 123, {'type': 'emitida'})
```

### Invoice-Specific Logging

```python
logger.log_invoice_created(
    invoice_id=105,
    invoice_type='emitida',
    total=5000.0,
    company_id=1,
    client='ABC Corp'
)
```

## What Gets Logged

### Firebase Data Access

All Firebase CRUD operations are automatically logged:

- **Invoice Creation**: Type, total, company, client
- **Invoice Deletion**: Type, total, company (with WARNING level)
- **Quotation Updates**: Total, company
- **Quotation Deletion**: Total, company (with WARNING level)
- **All Errors**: Full exception details with context

### Log Levels

- `INFO`: Normal operations (Create, Read, Update)
- `WARNING`: Deletions and important changes
- `ERROR`: Exceptions and failures

## Performance

- Logs are written asynchronously to avoid blocking operations
- File handler with UTF-8 encoding for international characters
- Console handler only shows WARNING and ERROR levels to avoid noise

## Maintenance

### Log Rotation

Logs are NOT automatically rotated. To implement log rotation:

```python
from logging.handlers import RotatingFileHandler

# Add to logger.py
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
```

### Viewing Logs

```bash
# View recent logs
tail -n 100 ~/.facot/logs/facot_audit.log

# Search for specific invoice
grep "Invoice ID: 105" ~/.facot/logs/facot_audit.log

# View all errors
grep "\[ERROR\]" ~/.facot/logs/facot_audit.log
```

## Security Considerations

- Log files contain sensitive business data (invoice totals, client names)
- Ensure log directory has appropriate permissions
- Consider encrypting logs for compliance requirements
- Do NOT commit log files to version control (already in .gitignore)

## Examples

### Typical Log Entries

```
[2025-12-04 10:00:00] [INFO] Audit logger initialized
[2025-12-04 10:00:15] [INFO] CREATE Invoice ID: 105 | Details: {"type": "EMITIDA", "total": "5000.00", "company_id": 1, "client": "ABC Corp"}
[2025-12-04 10:05:30] [INFO] UPDATE Invoice ID: 105 | Changes: {"total": "5500.00"}
[2025-12-04 10:10:00] [WARNING] DELETE Invoice ID: 105 | Details: {"type": "EMITIDA", "total": "5500.00", "company_id": 1}
[2025-12-04 10:15:00] [ERROR] ERROR add_invoice | Error: Network timeout | Context: {"invoice_data": {...}}
```

### Recovery Scenario

If you need to rebuild indices or verify data integrity:

```bash
# Extract all CREATE operations
grep "CREATE Invoice" ~/.facot/logs/facot_audit.log > created_invoices.log

# Extract all DELETE operations
grep "DELETE Invoice" ~/.facot/logs/facot_audit.log > deleted_invoices.log

# Compare to verify data integrity
```
