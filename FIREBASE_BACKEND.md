# Firebase-Only Backend Configuration

## Overview

**IMPORTANT**: As of this version, FACOT requires Firebase/Firestore as the primary backend for all data operations. SQLite is retained only for backwards compatibility and migration tools.

## Why Firebase-Only?

- **Multi-user Support**: Firebase enables real-time collaboration across multiple devices
- **Cloud Backup**: Data is automatically backed up to the cloud
- **Scalability**: Better performance with large datasets
- **Audit Trail**: Built-in versioning and change tracking
- **Security**: Firebase provides enterprise-grade security features

## First-Time Setup

When you launch the application for the first time (or if Firebase is not configured):

1. **Configuration Prompt**: You'll see a dialog stating "Firebase Requerido"
2. **Configure Now**: Click "Yes" to open the Firebase configuration dialog
3. **Enter Credentials**: Provide your Firebase project credentials:
   - Project ID
   - Service Account Key (JSON file)
   - Firestore Database ID (optional)
4. **Save**: Click "Save" to store the configuration
5. **Restart**: The application will use Firebase for all operations

## Firebase Configuration Dialog

Access via: **Herramientas > Configurar Firebase...**

### Required Information

1. **Firebase Credentials File**: 
   - Download from Firebase Console
   - Go to Project Settings > Service Accounts
   - Click "Generate New Private Key"
   - Save the JSON file securely

2. **Project ID**:
   - Found in Firebase Console > Project Settings
   - Example: `facot-production-12345`

3. **Database ID** (optional):
   - For projects with multiple Firestore databases
   - Leave blank to use default database

### Configuration File Location

Credentials are stored at:
- Linux/Mac: `~/.facot/firebase_credentials.json`
- Windows: `%USERPROFILE%\.facot\firebase_credentials.json`

**SECURITY NOTE**: This file contains sensitive credentials. Ensure appropriate file permissions.

## Migration from SQLite

If you have existing data in SQLite:

1. **Configure Firebase**: Follow the setup steps above
2. **Run Migration**: Go to **Herramientas > Migrar a Firebase...**
3. **Select Data**: Choose which data to migrate:
   - Companies
   - Invoices
   - Quotations
   - Items
   - Third Parties
4. **Monitor Progress**: Watch the migration progress bar
5. **Verify**: Check that data appears correctly in Firebase Console

### Migration Notes

- SQLite database remains intact (read-only)
- Migration can be run multiple times (updates existing data)
- Large datasets may take several minutes
- Internet connection required during migration

## Firestore Data Structure

### Collections

```
companies/
  {company_id}/
    name, rnc, address, ...

items/
  {item_id}/
    code, description, price, ...

third_parties/
  {party_id}/
    rnc, name, address, ...

invoices/
  {invoice_id}/
    company_id, invoice_type, total_amount, ...
    items/
      {item_index}/
        description, quantity, price, ...

quotations/
  {quotation_id}/
    company_id, total_amount, ...
    items/
      {item_index}/
        description, quantity, price, ...

sequences/
  {company_id}_ncf/
    {ncf_type}/
      current_sequence, prefix, ...
```

## Enforcement Details

### What Happens on Startup

```python
# 1. SQLite is initialized (for migration tools only)
self.logic = LogicController(db_path)

# 2. Firebase availability is checked
firebase_client = get_firebase_client()
if not firebase_client.is_available():
    # Show configuration dialog or exit

# 3. Firebase is set as primary backend (FORCED)
self.data_access = get_data_access(mode=DataAccessMode.FIREBASE)

# 4. Hybrid wrapper uses Firebase for all operations
self.hybrid_logic = HybridLogicWrapper(self.logic, self.data_access)
```

### Backend Priority

When tabs request data:

1. **Primary**: Firebase (via `data_access`)
2. **Fallback**: SQLite (only if method not available in Firebase)
3. **Migration Tools**: Direct SQLite access for migration operations

## Troubleshooting

### Error: "Firebase no está configurado"

**Solution**: Configure Firebase via Herramientas > Configurar Firebase

### Error: "Firestore no está disponible"

**Possible Causes**:
1. Invalid credentials
2. Network connectivity issues
3. Firebase project not accessible
4. Service account permissions insufficient

**Solutions**:
1. Verify credentials file is valid JSON
2. Check internet connection
3. Verify project ID in Firebase Console
4. Ensure service account has Firestore permissions:
   - Cloud Datastore User
   - Firebase Admin

### Error: "firebase-admin module not found"

**Solution**: Install Firebase dependencies:
```bash
pip install firebase-admin google-cloud-firestore
```

### Performance Issues

**Solutions**:
1. Check internet connection speed
2. Enable Firestore caching (automatic)
3. Consider upgrading Firebase plan for better performance
4. Use indexes for frequently queried fields

## Offline Mode

**Current Status**: Not supported

**Future Enhancement**: Implement offline caching with sync when online

## Security Best Practices

1. **Credentials**:
   - Never commit `firebase_credentials.json` to version control
   - Use different credentials for development/production
   - Rotate service account keys regularly

2. **Firestore Rules**:
   - Configure strict security rules in Firebase Console
   - Limit access to authenticated users
   - Validate data on write operations

3. **Network**:
   - Use HTTPS for all connections (automatic with Firebase)
   - Consider VPN for sensitive data transmission

## Backup Strategy

### Automatic Backups

Firebase provides automatic daily backups (retention depends on plan)

### Manual Backups

1. **Export Firestore Data**:
   ```bash
   gcloud firestore export gs://[BUCKET_NAME]/[EXPORT_FOLDER]
   ```

2. **SQLite Backup** (for migration reference):
   - Use **Archivo > Hacer Backup...**
   - Stores SQLite snapshot (read-only reference)

## Support

For Firebase-specific issues:
- Firebase Console: https://console.firebase.google.com
- Firebase Documentation: https://firebase.google.com/docs
- Support: https://firebase.google.com/support

For FACOT issues:
- Check FACOT documentation in this repository
- Review audit logs: `~/.facot/logs/facot_audit.log`
