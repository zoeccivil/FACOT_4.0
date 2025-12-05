"""
Implementación de DataAccess para Firebase (Firestore).
Proporciona acceso a datos usando Firestore como backend.
"""

from __future__ import annotations
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Asegúrate de que estos imports funcionen en tu proyecto
try:
    from .base import DataAccess
except ImportError:
    # Si base.py no existe o falla, definimos una clase base dummy
    class DataAccess: pass

from firebase import get_firebase_client
from utils.logger import get_audit_logger


class FirebaseDataAccess(DataAccess):
    """
    Implementación de DataAccess usando Firebase Firestore.
    """

    def __init__(self, user_id: Optional[str] = None):
        self.client = get_firebase_client()
        self.db = self.client.get_firestore()
        self.storage = self.client.get_storage()
        self.user_id = user_id or "system"
        self.audit_logger = get_audit_logger()

        if not self.db:
            raise RuntimeError("Firestore no está disponible. Verificar configuración de Firebase.")

    def _add_metadata(self, data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """Agrega metadatos de auditoría a un documento."""
        now = datetime.utcnow().isoformat()
        if not is_update:
            data['created_at'] = now
            data['created_by'] = self.user_id
        data['updated_at'] = now
        data['updated_by'] = self.user_id
        return data

    # ==========================================
    #               EMPRESAS
    # ==========================================

    def get_all_companies(self) -> List[Dict[str, Any]]:
        try:
            companies_ref = self.db.collection('companies')
            docs = list(companies_ref.stream())
            companies = []
            for doc in docs:
                d = doc.to_dict() or {}
                # Asegurar ID (int si es dígito)
                cid = doc.id
                if isinstance(cid, str) and cid.isdigit():
                    cid = int(cid)
                d['id'] = cid
                # Si no hay invoice_due_date en el doc, intentar sequences/<id>_meta
                if not d.get('invoice_due_date'):
                    try:
                        meta_ref = self.db.collection('sequences').document(f"{cid}_meta")
                        meta_doc = meta_ref.get()
                        if meta_doc.exists:
                            meta = meta_doc.to_dict() or {}
                            inv_due = meta.get('invoice_due_date')
                            if inv_due:
                                d['invoice_due_date'] = inv_due
                    except Exception:
                        pass
                companies.append(d)
            return companies
        except Exception as e:
            print(f"[FIREBASE] ERROR obteniendo empresas: {e}")
            return []

    def get_company_details(self, company_id: int) -> Optional[Dict[str, Any]]:
        try:
            company_id_str = str(company_id)
            doc_ref = self.db.collection('companies').document(company_id_str)
            doc = doc_ref.get()
            if doc.exists:
                d = doc.to_dict() or {}
                d['id'] = company_id if isinstance(company_id, int) else company_id_str
                # Merge invoice_due_date desde sequences/<id>_meta si falta
                if not d.get('invoice_due_date'):
                    try:
                        meta_ref = self.db.collection('sequences').document(f"{company_id_str}_meta")
                        meta_doc = meta_ref.get()
                        if meta_doc.exists:
                            meta = meta_doc.to_dict() or {}
                            inv_due = meta.get('invoice_due_date')
                            if inv_due:
                                d['invoice_due_date'] = inv_due
                    except Exception:
                        pass
                return d
            return None
        except Exception as e:
            print(f"[FIREBASE] Error getting company {company_id}: {e}")
            return None

    def add_company(self, name: str, rnc: str, address: str = "") -> int:
        try:
            import time
            company_id = int(time.time() * 1000) % 1000000
            company_data = {
                'name': name, 'rnc': rnc, 'address': address,
                'address_line1': address, 'company_id': company_id
            }
            company_data = self._add_metadata(company_data)
            self.db.collection('companies').document(str(company_id)).set(company_data)
            return company_id
        except Exception as e:
            print(f"[FIREBASE] Error adding company: {e}")
            raise

    def update_company_fields(self, company_id: int, fields: Dict[str, Any]) -> None:
        """
        Actualiza campos en el doc companies/{id} y, si 'invoice_due_date' está presente,
        también lo guarda en sequences/{id}_meta (merge, no sobrescribe otros campos).
        """
        try:
            # split meta fields: currently only 'invoice_due_date'
            fields = dict(fields or {})
            meta_updates = {}
            if 'invoice_due_date' in fields:
                inv_due = (fields.get('invoice_due_date') or '').strip()
                meta_updates['invoice_due_date'] = inv_due
                # no guardamos en company doc si prefieres solo sequences, pero mantenemos ambos por compatibilidad
            # update company document
            company_updates = dict(fields)
            company_updates = self._add_metadata(company_updates, is_update=True)
            self.db.collection('companies').document(str(company_id)).set(company_updates, merge=True)

            # update sequences meta
            if meta_updates:
                meta_updates = self._add_metadata(meta_updates, is_update=True)
                self.db.collection('sequences').document(f"{company_id}_meta").set(meta_updates, merge=True)

        except Exception as e:
            print(f"[FIREBASE] Error updating company {company_id}: {e}")
            raise

    def delete_company(self, company_id: int) -> Tuple[bool, str]:
        try:
            # borrar doc de company
            self.db.collection('companies').document(str(company_id)).delete()
            # borrar meta opcional (no crítico si falla)
            try:
                self.db.collection('sequences').document(f"{company_id}_meta").delete()
            except Exception:
                pass
            return True, "Eliminada correctamente"
        except Exception as e:
            print(f"[FIREBASE] Error deleting company {company_id}: {e}")
            return False, str(e)

    # ==========================================
    #               CATEGORÍAS
    # ==========================================

    def get_all_categories(self) -> List[Dict[str, Any]]:
        try:
            cats_ref = self.db.collection('categories')
            docs = list(cats_ref.stream())
            categories = []
            for doc in docs:
                d = doc.to_dict() or {}
                d['id'] = doc.id
                categories.append(d)
            return categories
        except Exception as e:
            print(f"[FIREBASE] ERROR categorías: {e}")
            return []

    def add_category(self, data: Dict[str, Any]) -> str:
        try:
            import time
            cat_id = str(int(time.time() * 1000))
            data = self._add_metadata(data)
            self.db.collection('categories').document(cat_id).set(data)
            return cat_id
        except Exception as e:
            print(f"[FIREBASE] Error adding category: {e}")
            raise

    def update_category(self, cat_id: str, data: Dict[str, Any]):
        try:
            data = self._add_metadata(data, is_update=True)
            self.db.collection('categories').document(str(cat_id)).update(data)
        except Exception as e:
            print(f"[FIREBASE] Error updating category: {e}")
            raise

    def delete_category(self, cat_id: str):
        try:
            self.db.collection('categories').document(str(cat_id)).delete()
        except Exception as e:
            print(f"[FIREBASE] Error deleting category: {e}")
            raise

    # ==========================================
    #               ÍTEMS
    # ==========================================

    def get_all_items(self) -> List[Dict[str, Any]]:
        try:
            items_ref = self.db.collection('items')
            docs = list(items_ref.stream())
            items = []
            for doc in docs:
                item_data = doc.to_dict() or {}
                item_data['id'] = doc.id
                items.append(item_data)
            return items
        except Exception as e:
            print(f"[FIREBASE] ERROR ítems: {e}")
            return []

    def add_item(self, data: Dict[str, Any]) -> str:
        try:
            item_id = data.get('code')
            if not item_id:
                import time
                item_id = f"ITEM_{int(time.time()*1000)}"
            data = self._add_metadata(data)
            self.db.collection('items').document(item_id).set(data)
            return item_id
        except Exception as e:
            print(f"[FIREBASE] Error adding item: {e}")
            raise

    def update_item(self, item_id: str, data: Dict[str, Any]):
        try:
            data = self._add_metadata(data, is_update=True)
            self.db.collection('items').document(str(item_id)).update(data)
        except Exception as e:
            print(f"[FIREBASE] Error updating item: {e}")
            raise

    def delete_item(self, item_id: str):
        try:
            self.db.collection('items').document(str(item_id)).delete()
        except Exception as e:
            print(f"[FIREBASE] Error deleting item: {e}")
            raise

    def get_next_code(self, category_id: str) -> str:
        return "GEN0000"  # TODO: implementar con sequences si se usa en Firestore

    def get_item_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        try:
            items_ref = self.db.collection('items')
            doc = items_ref.document(code).get()
            if doc.exists:
                d = doc.to_dict() or {}
                d['id'] = doc.id
                return d

            query = items_ref.where('code', '==', code).limit(1)
            docs = list(query.stream())
            if docs:
                d = docs[0].to_dict() or {}
                d['id'] = docs[0].id
                return d
            return None
        except Exception as e:
            print(f"[FIREBASE] Error getting item by code {code}: {e}")
            return None

    def get_items_like(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        all_items = self.get_all_items()
        q = (query or "").lower()
        filtered = [
            i for i in all_items
            if q in str(i.get('code', '')).lower() or q in str(i.get('name', '')).lower()
        ]
        return filtered[:limit]

    # ==========================================
    #      RESTO (Facturas, Cotizaciones, Terceros)
    # ==========================================

    def get_third_party_by_rnc(self, rnc: str) -> Optional[Dict[str, Any]]:
        try:
            parties_ref = self.db.collection('third_parties')
            query = parties_ref.where('rnc', '==', rnc).limit(1)
            docs = list(query.stream())
            if docs:
                party_data = docs[0].to_dict() or {}
                party_data['id'] = docs[0].id
                return party_data
            return None
        except Exception as e:
            print(f"[FIREBASE] Error getting third party by RNC {rnc}: {e}")
            return None

    def search_third_parties(self, query: str, search_by: str = 'name') -> List[Dict[str, Any]]:
        try:
            parties_ref = self.db.collection('third_parties')
            all_parties = []
            for doc in parties_ref.limit(100).stream():
                party_data = doc.to_dict() or {}
                party_data['id'] = doc.id

                if search_by == 'name':
                    if (query or "").lower() in str(party_data.get('name', '')).lower():
                        all_parties.append(party_data)
                elif search_by == 'rnc':
                    if (query or "") in str(party_data.get('rnc', '')):
                        all_parties.append(party_data)

                if len(all_parties) >= 20:
                    break
            return all_parties
        except Exception as e:
            print(f"[FIREBASE] Error searching third parties: {e}")
            return []

    def add_or_update_third_party(self, rnc: str, name: str) -> None:
        try:
            parties_ref = self.db.collection('third_parties')
            query = parties_ref.where('rnc', '==', rnc).limit(1)
            docs = list(query.stream())

            party_data = {'rnc': rnc, 'name': name}
            party_data = self._add_metadata(party_data, is_update=len(docs) > 0)

            if docs:
                docs[0].reference.update(party_data)
            else:
                parties_ref.add(party_data)
        except Exception as e:
            print(f"[FIREBASE] Error adding/updating third party: {e}")
            raise

    # ===== FACTURAS (INVOICES) =====

    def get_facturas(self, company_id: int, only_issued: bool = True) -> List[Dict[str, Any]]:
        return self.get_invoices(company_id, limit=5000)

    def add_invoice(self, invoice_data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        """
        Crea factura y sus ítems. Si no viene 'invoice_number', intenta generar NCF usando sequences.
        Guarda company_id y tipos coherentes.
        """
        try:
            import time
            invoice_id = str(int(time.time() * 1000))
            data = dict(invoice_data or {})
            # Normalizar company_id
            if 'company_id' in data and isinstance(data['company_id'], str) and data['company_id'].isdigit():
                data['company_id'] = int(data['company_id'])
            # Generar invoice_number si se solicita (requiere ncf_type)
            ncf_type = (data.get('ncf_type') or '').strip().upper()
            if not data.get('invoice_number') and ncf_type:
                data['invoice_number'] = self.get_next_ncf(int(data.get('company_id')), ncf_type)

            data = self._add_metadata(data)
            doc_ref = self.db.collection('invoices').document(invoice_id)
            doc_ref.set(data)
            for i, item in enumerate(items or []):
                item_data = self._add_metadata(dict(item or {}))
                doc_ref.collection('items').document(str(i)).set(item_data)
            return int(invoice_id) if invoice_id.isdigit() else invoice_id
        except Exception as e:
            print(f"[FIREBASE] Error adding invoice: {e}")
            raise

    def get_invoices(self, company_id: int, limit: int = 5000, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            ref = self.db.collection('invoices')
            # Probar int y str para company_id
            docs = []
            try:
                from google.cloud.firestore_v1 import FieldFilter
                q1 = ref.where(filter=FieldFilter('company_id', '==', company_id)).limit(limit)
                docs = list(q1.stream())
                if not docs:
                    q2 = ref.where(filter=FieldFilter('company_id', '==', str(company_id))).limit(limit)
                    docs = list(q2.stream())
            except Exception:
                q1 = ref.where('company_id', '==', company_id).limit(limit)
                docs = list(q1.stream())
                if not docs:
                    q2 = ref.where('company_id', '==', str(company_id)).limit(limit)
                    docs = list(q2.stream())
            out = []
            for d in docs:
                dd = d.to_dict() or {}
                try:
                    dd['id'] = int(d.id)
                except Exception:
                    dd['id'] = d.id
                out.append(dd)
            return out
        except Exception as e:
            print(f"[FIREBASE] Error getting invoices: {e}")
            return []

    def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        try:
            invoice_ref = self.db.collection('invoices').document(str(invoice_id))
            doc = invoice_ref.get()
            if not doc.exists:
                return None
            invoice_data = doc.to_dict() or {}
            invoice_data['id'] = invoice_id if isinstance(invoice_id, int) else str(invoice_id)
            items_ref = invoice_ref.collection('items')
            items = []
            for item_doc in items_ref.stream():
                item_data = item_doc.to_dict() or {}
                items.append(item_data)
            invoice_data['items'] = items
            return invoice_data
        except Exception as e:
            print(f"[FIREBASE] Error getting invoice {invoice_id}: {e}")
            return None

    def get_invoice_items(self, invoice_id: Any) -> List[Dict[str, Any]]:
        try:
            ref = self.db.collection('invoices').document(str(invoice_id)).collection('items')
            docs = list(ref.stream())
            out = []
            for d in docs:
                dd = d.to_dict() or {}
                dd['id'] = d.id
                out.append(dd)
            return out
        except Exception as e:
            print(f"[FIREBASE] Error getting invoice items: {e}")
            return []

    def delete_factura(self, factura_id: int) -> None:
        try:
            invoice_ref = self.db.collection('invoices').document(str(factura_id))
            items_ref = invoice_ref.collection('items')
            for item_doc in items_ref.stream():
                item_doc.reference.delete()
            invoice_ref.delete()
        except Exception as e:
            print(f"[FIREBASE] Error deleting invoice {factura_id}: {e}")
            raise

    # ===== COTIZACIONES (QUOTATIONS) =====

    def add_quotation(self, quotation_data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        try:
            import time
            quotation_id = int(time.time() * 1000) % 1000000
            quotation_doc = dict(quotation_data or {})
            quotation_doc = self._add_metadata(quotation_doc)
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            quotation_ref.set(quotation_doc)
            items_ref = quotation_ref.collection('items')
            for idx, item in enumerate(items or []):
                item_doc = self._add_metadata(dict(item or {}))
                items_ref.document(str(idx)).set(item_doc)
            return quotation_id
        except Exception as e:
            print(f"[FIREBASE] Error adding quotation: {e}")
            raise

    def get_quotations(self, company_id: Optional[int] = None, limit: int = 5000, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            quotations_ref = self.db.collection('quotations')
            if company_id:
                query = quotations_ref.where('company_id', '==', company_id)
            else:
                query = quotations_ref
            query = query.limit(limit).offset(offset)
            quotations = []
            for doc in query.stream():
                quotation_data = doc.to_dict() or {}
                quotation_data['id'] = int(doc.id) if doc.id.isdigit() else doc.id
                quotations.append(quotation_data)
            return quotations
        except Exception as e:
            print(f"[FIREBASE] Error getting quotations: {e}")
            return []

    def get_quotation_by_id(self, quotation_id: int) -> Optional[Dict[str, Any]]:
        try:
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            doc = quotation_ref.get()
            if not doc.exists:
                return None
            quotation_data = doc.to_dict() or {}
            quotation_data['id'] = quotation_id
            items_ref = quotation_ref.collection('items')
            items = []
            for item_doc in items_ref.stream():
                item_data = item_doc.to_dict() or {}
                items.append(item_data)
            quotation_data['items'] = items
            return quotation_data
        except Exception as e:
            print(f"[FIREBASE] Error getting quotation {quotation_id}: {e}")
            return None

    def get_quotation_items(self, quotation_id: Any) -> List[Dict[str, Any]]:
        """Obtiene solo los ítems de una cotización específica."""
        try:
            ref = self.db.collection('quotations').document(str(quotation_id)).collection('items')
            docs = list(ref.stream())
            out = []
            for d in docs:
                dd = d.to_dict() or {}
                dd['id'] = d.id
                out.append(dd)
            return out
        except Exception as e:
            print(f"[FIREBASE] Error getting quotation items: {e}")
            return []

    def delete_quotation(self, quotation_id: int) -> None:
        try:
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            items_ref = quotation_ref.collection('items')
            for item_doc in items_ref.stream():
                item_doc.reference.delete()
            quotation_ref.delete()
        except Exception as e:
            print(f"[FIREBASE] Error deleting quotation {quotation_id}: {e}")
            raise

    def update_quotation(self, quotation_id: int, quotation_data: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
        try:
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            quotation_doc = dict(quotation_data or {})
            quotation_doc = self._add_metadata(quotation_doc, is_update=True)
            quotation_ref.update(quotation_doc)
            items_ref = quotation_ref.collection('items')
            for item_doc in items_ref.stream():
                item_doc.reference.delete()
            for idx, item in enumerate(items or []):
                item_doc = self._add_metadata(dict(item or {}))
                items_ref.document(str(idx)).set(item_doc)
        except Exception as e:
            print(f"[FIREBASE] Error updating quotation {quotation_id}: {e}")
            raise

    # ===== NCF / SECUENCIAS =====

    def get_next_ncf(self, company_id: int, ncf_type: str) -> str:
        """
        Obtiene el siguiente NCF de sequences/{company_id}_ncf_{TYPE} de forma transaccional.
        Devuelve B01/B14/B15 + 8 dígitos.
        """
        try:
            from google.cloud import firestore as gcf

            # normalizar tipo (solo dígitos y mayúsculas)
            ncf_type = (ncf_type or "").upper().strip()
            # Aceptar valores como B01/B14/B15 o solo '01', '14', '15'
            if ncf_type.startswith("B"):
                prefix = ncf_type
            else:
                prefix = f"B{ncf_type}"
            # llave de documento
            seq_doc_id = f"{company_id}_ncf_{prefix}"
            sequence_ref = self.db.collection('sequences').document(seq_doc_id)

            @gcf.transactional
            def increment_sequence(transaction):
                snapshot = sequence_ref.get(transaction=transaction)
                current = int(snapshot.get('current') or 0) if snapshot.exists else 0
                new_value = current + 1
                transaction.set(sequence_ref, {'current': new_value, 'updated_at': datetime.utcnow().isoformat(), 'updated_by': self.user_id}, merge=True)
                return new_value

            transaction = self.db.transaction()
            seq_num = increment_sequence(transaction)
            return f"{prefix}{seq_num:08d}"
        except Exception as e:
            print(f"[FIREBASE] Error getting next NCF: {e}")
            # fallback seguro
            prefix = (ncf_type or "B01").upper().strip()
            if not prefix.startswith("B"):
                prefix = f"B{prefix}"
            return f"{prefix}00000001"

    # ===== LOGOS EN STORAGE =====

    def upload_logo_to_storage(self, local_path: str, template_id: str) -> Optional[str]:
        if not self.storage:
            return None
        if not os.path.exists(local_path):
            return None
        try:
            _, ext = os.path.splitext(local_path)
            if not ext:
                ext = ".png"
            storage_path = f"templates/{template_id}/logo{ext}"
            blob = self.storage.blob(storage_path)
            content_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            content_type = content_types.get(ext.lower(), "application/octet-stream")
            blob.upload_from_filename(local_path, content_type=content_type)
            try:
                blob.make_public()
                public_url = blob.public_url
            except Exception:
                public_url = blob.generate_signed_url(version="v4", expiration=3600*24*365, method="GET")
            print(f"[FIREBASE] Logo subido: {storage_path}")
            return public_url
        except Exception as e:
            print(f"[FIREBASE] Error subiendo logo: {e}")
            return None

    def download_logo(self, storage_path: str, template_id: str) -> Optional[str]:
        if not self.storage:
            return None
        CACHE_EXPIRATION_SECONDS = 24 * 60 * 60
        try:
            cache_dir = os.path.join(".", "data", "cache", "logos")
            os.makedirs(cache_dir, exist_ok=True)
            _, ext = os.path.splitext(storage_path)
            if not ext:
                ext = ".png"
            local_path = os.path.join(cache_dir, f"{template_id}{ext}")
            if os.path.exists(local_path):
                import time
                if time.time() - os.path.getmtime(local_path) < CACHE_EXPIRATION_SECONDS:
                    return local_path
            blob = self.storage.blob(storage_path)
            if not blob.exists():
                return None
            blob.download_to_filename(local_path)
            return local_path
        except Exception as e:
            print(f"[FIREBASE] Error descargando logo: {e}")
            return None

    def update_template_logo(self, template_id: str, local_logo_path: str) -> Dict[str, Any]:
        result = {}
        public_url = self.upload_logo_to_storage(local_logo_path, template_id)
        if public_url:
            _, ext = os.path.splitext(local_logo_path)
            storage_path = f"templates/{template_id}/logo{ext}"
            result = {"logo_storage_path": storage_path, "logo_url": public_url}
            try:
                template_ref = self.db.collection('templates').document(str(template_id))
                template_ref.update({
                    "logo_storage_path": storage_path, "logo_url": public_url,
                    "updated_at": datetime.utcnow().isoformat(), "updated_by": self.user_id
                })
            except Exception as e:
                print(f"[FIREBASE] Error actualizando plantilla: {e}")
        return result

    def get_template_logo(self, template_id: str, fallback_local_path: Optional[str] = None) -> Optional[str]:
        try:
            template_ref = self.db.collection('templates').document(str(template_id))
            doc = template_ref.get()
            if doc.exists:
                template_data = doc.to_dict() or {}
                storage_path = template_data.get('logo_storage_path')
                if storage_path:
                    local_path = self.download_logo(storage_path, template_id)
                    if local_path:
                        return local_path
            if fallback_local_path and os.path.exists(fallback_local_path):
                return fallback_local_path
            return None
        except Exception:
            if fallback_local_path and os.path.exists(fallback_local_path):
                return fallback_local_path
            return None

    # ===== PDF UPLOAD TO STORAGE =====

    def upload_file_to_storage(self, local_path: str, storage_path: str) -> Optional[str]:
        """
        Sube un archivo a Firebase Storage y devuelve la URL pública o firmada.
        
        Args:
            local_path: Ruta local del archivo a subir
            storage_path: Ruta en Storage (ej: "factura/empresa/2025/12/B01001.pdf")
        
        Returns:
            URL pública o firmada del archivo, o None si falla
        
        Logs:
            [PDF-UPLOAD] storage_path=..., url=...
        """
        if not self.storage:
            print("[PDF-UPLOAD] ERROR: Storage no disponible")
            return None
        
        if not os.path.exists(local_path):
            print(f"[PDF-UPLOAD] ERROR: Archivo local no existe: {local_path}")
            return None
        
        try:
            # Subir archivo a Storage
            blob = self.storage.blob(storage_path)
            
            # Detectar content type
            _, ext = os.path.splitext(local_path)
            content_type = "application/pdf" if ext.lower() == ".pdf" else "application/octet-stream"
            
            blob.upload_from_filename(local_path, content_type=content_type)
            
            # Intentar hacer público
            url = None
            try:
                blob.make_public()
                url = blob.public_url
                print(f"[PDF-UPLOAD] storage_path={storage_path}, url={url} (público)")
            except Exception as e:
                # Fallback: generar URL firmada (válida por 1 año)
                print(f"[PDF-UPLOAD] No se pudo hacer público, usando URL firmada: {e}")
                try:
                    url = blob.generate_signed_url(version="v4", expiration=3600*24*365, method="GET")
                    print(f"[PDF-UPLOAD] storage_path={storage_path}, url={url} (firmada)")
                except Exception as e2:
                    print(f"[PDF-UPLOAD] ERROR generando URL firmada: {e2}")
                    return None
            
            return url
        
        except Exception as e:
            print(f"[PDF-UPLOAD] ERROR subiendo archivo: {e}")
            return None

    def set_invoice_pdf_info(self, invoice_id: Any, storage_path: str, url: str) -> None:
        """
        Guarda metadatos de PDF en documento de factura (merge).
        
        Args:
            invoice_id: ID de la factura
            storage_path: Ruta en Storage
            url: URL del PDF (pública o firmada)
        """
        try:
            invoice_ref = self.db.collection('invoices').document(str(invoice_id))
            invoice_ref.set({
                'pdf_storage_path': storage_path,
                'pdf_url': url,
                'updated_at': datetime.utcnow().isoformat(),
                'updated_by': self.user_id
            }, merge=True)
            print(f"[PDF-UPLOAD] Metadatos guardados en invoice {invoice_id}: path={storage_path}")
        except Exception as e:
            print(f"[PDF-UPLOAD] ERROR guardando metadatos de factura {invoice_id}: {e}")
            raise

    def set_quotation_pdf_info(self, quotation_id: Any, storage_path: str, url: str) -> None:
        """
        Guarda metadatos de PDF en documento de cotización (merge).
        
        Args:
            quotation_id: ID de la cotización
            storage_path: Ruta en Storage
            url: URL del PDF (pública o firmada)
        """
        try:
            quotation_ref = self.db.collection('quotations').document(str(quotation_id))
            quotation_ref.set({
                'pdf_storage_path': storage_path,
                'pdf_url': url,
                'updated_at': datetime.utcnow().isoformat(),
                'updated_by': self.user_id
            }, merge=True)
            print(f"[PDF-UPLOAD] Metadatos guardados en quotation {quotation_id}: path={storage_path}")
        except Exception as e:
            print(f"[PDF-UPLOAD] ERROR guardando metadatos de cotización {quotation_id}: {e}")
            raise

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass