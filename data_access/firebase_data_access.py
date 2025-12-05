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

    def _normalize_ncf_prefix(self, prefix3: str) -> str:
        """Normaliza el prefijo a formato estándar (B01, E31, etc.)"""
        p = (prefix3 or "").upper().strip()
        # Si ya tiene formato completo (B01, E31), devolverlo
        if len(p) == 3 and (p[0].isalpha() and p[1:].isdigit()):
            return p
        # Si es solo dígitos (01, 31), agregar B o E según el caso
        if p.isdigit():
            if p == "31":
                return "E31"
            return f"B{p}"
        # Si empieza con letra pero no tiene 3 caracteres, intentar arreglar
        if p and p[0].isalpha():
            if len(p) >= 3:
                return p[:3]
            # Agregar dígitos faltantes
            if len(p) == 1:
                return f"{p}01"
        return "B01"  # fallback

    def _format_ncf(self, prefix3: str, seq_num: int) -> str:
        """Formatea NCF según el prefijo."""
        prefix3 = self._normalize_ncf_prefix(prefix3)
        # E-CF (E31): E + 2 dígitos tipo + 11 dígitos secuencia = 14 total
        if prefix3.startswith("E"):
            tipo = prefix3[1:3]  # ej: "31"
            return f"E{tipo}{seq_num:011d}"
        # NCF estándar (Bxx): Prefix (3 chars) + 8 dígitos
        return f"{prefix3}{seq_num:08d}"

    def get_ncf_last_seq(self, company_id: int, prefix3: str) -> int:
        """
        Obtiene la última secuencia asignada para un prefijo NCF.
        NO incrementa. Retorna 0 si no existe.
        """
        try:
            prefix3 = self._normalize_ncf_prefix(prefix3)
            doc_path = f"sequences/{company_id}ncf{prefix3}"
            print(f"[SEQ get_ncf_last_seq] doc_path={doc_path}")
            
            doc_ref = self.db.collection('sequences').document(f"{company_id}ncf{prefix3}")
            doc = doc_ref.get()
            
            exists = doc.exists
            current = int(doc.get('current') or 0) if exists else 0
            
            print(f"[SEQ get_ncf_last_seq] exists={exists}, current={current}")
            return current
        except Exception as e:
            print(f"[SEQ get_ncf_last_seq] ERROR: {e}")
            return 0

    def set_ncf_last_seq(self, company_id: int, prefix3: str, last_seq: int) -> bool:
        """
        Establece la última secuencia para un prefijo NCF.
        Usado para configuración manual.
        """
        try:
            prefix3 = self._normalize_ncf_prefix(prefix3)
            doc_path = f"sequences/{company_id}ncf{prefix3}"
            print(f"[SEQ set_ncf_last_seq] doc_path={doc_path}")
            
            doc_ref = self.db.collection('sequences').document(f"{company_id}ncf{prefix3}")
            
            # Leer valor anterior
            doc = doc_ref.get()
            before = int(doc.get('current') or 0) if doc.exists else 0
            print(f"[SEQ set_ncf_last_seq] before={before}")
            
            # Guardar nuevo valor
            data = {
                'current': int(last_seq),
                'updated_at': datetime.utcnow().isoformat(),
                'updated_by': self.user_id
            }
            doc_ref.set(data, merge=True)
            print(f"[SEQ set_ncf_last_seq] after/guardado={last_seq}")
            
            return True
        except Exception as e:
            print(f"[SEQ set_ncf_last_seq] ERROR: {e}")
            return False

    def get_ncf_preview(self, company_id: int, prefix3: str) -> str:
        """
        Obtiene preview del próximo NCF SIN incrementar la secuencia.
        """
        try:
            prefix3 = self._normalize_ncf_prefix(prefix3)
            doc_ref = self.db.collection('sequences').document(f"{company_id}ncf{prefix3}")
            doc = doc_ref.get()
            
            current = int(doc.get('current') or 0) if doc.exists else 0
            next_seq = current + 1
            preview_result = self._format_ncf(prefix3, next_seq)
            
            print(f"[SEQ get_ncf_preview] company_id={company_id}, prefix3={prefix3}, current={current}, preview_result={preview_result}")
            
            return preview_result
        except Exception as e:
            print(f"[SEQ get_ncf_preview] ERROR: {e}")
            prefix3 = self._normalize_ncf_prefix(prefix3)
            return self._format_ncf(prefix3, 1)

    def allocate_next_ncf(self, company_id: int, prefix3: str) -> str:
        """
        Asigna y consume el siguiente NCF de forma transaccional.
        SÍ incrementa la secuencia.
        """
        try:
            from google.cloud import firestore as gcf
            
            prefix3 = self._normalize_ncf_prefix(prefix3)
            doc_id = f"{company_id}ncf{prefix3}"
            sequence_ref = self.db.collection('sequences').document(doc_id)
            
            print(f"[SEQ allocate_next_ncf] company_id={company_id}, prefix3={prefix3}")
            
            @gcf.transactional
            def increment_and_allocate(transaction):
                snapshot = sequence_ref.get(transaction=transaction)
                before = int(snapshot.get('current') or 0) if snapshot.exists else 0
                after = before + 1
                
                transaction.set(
                    sequence_ref,
                    {
                        'current': after,
                        'updated_at': datetime.utcnow().isoformat(),
                        'updated_by': self.user_id
                    },
                    merge=True
                )
                
                allocated_ncf = self._format_ncf(prefix3, after)
                print(f"[SEQ allocate_next_ncf] before={before}, after={after}, allocated_ncf={allocated_ncf}")
                return allocated_ncf
            
            transaction = self.db.transaction()
            result = increment_and_allocate(transaction)
            return result
            
        except ImportError as ie:
            # Fallback sin transacciones (NO-TXN)
            # Solo si falla la importación de google.cloud.firestore
            print(f"[SEQ allocate_next_ncf] NO-TXN fallback (google.cloud.firestore no disponible: {ie})")
            prefix3 = self._normalize_ncf_prefix(prefix3)
            doc_id = f"{company_id}ncf{prefix3}"
            doc_ref = self.db.collection('sequences').document(doc_id)
            
            doc = doc_ref.get()
            before = int(doc.get('current') or 0) if doc.exists else 0
            after = before + 1
            
            doc_ref.set(
                {
                    'current': after,
                    'updated_at': datetime.utcnow().isoformat(),
                    'updated_by': self.user_id
                },
                merge=True
            )
            
            allocated_ncf = self._format_ncf(prefix3, after)
            print(f"[SEQ allocate_next_ncf NO-TXN] before={before}, after={after}, allocated_ncf={allocated_ncf}")
            return allocated_ncf
            
        except Exception as e:
            print(f"[SEQ allocate_next_ncf] ERROR: {e}")
            prefix3 = self._normalize_ncf_prefix(prefix3)
            return self._format_ncf(prefix3, 1)

    def get_company_due_date(self, company_id: int) -> str:
        """
        Obtiene la fecha de vencimiento fija de facturas para una empresa.
        Preferencia: sequences/{id}_meta, luego companies/{id}.
        """
        try:
            # Primero intentar sequences/{id}_meta
            meta_path = f"sequences/{company_id}_meta"
            print(f"[DUE get_company_due_date] Consultando {meta_path}")
            
            meta_ref = self.db.collection('sequences').document(f"{company_id}_meta")
            meta_doc = meta_ref.get()
            
            if meta_doc.exists:
                meta = meta_doc.to_dict() or {}
                inv_due = (meta.get('invoice_due_date') or '').strip()
                if inv_due:
                    print(f"[DUE get_company_due_date] Encontrado en {meta_path}: {inv_due}")
                    return inv_due
            
            # Fallback: companies/{id}
            company_path = f"companies/{company_id}"
            print(f"[DUE get_company_due_date] Consultando fallback {company_path}")
            
            company_ref = self.db.collection('companies').document(str(company_id))
            company_doc = company_ref.get()
            
            if company_doc.exists:
                company = company_doc.to_dict() or {}
                inv_due = (company.get('invoice_due_date') or '').strip()
                print(f"[DUE get_company_due_date] Valor final: {inv_due}")
                return inv_due
            
            print(f"[DUE get_company_due_date] No encontrado, retornando vacío")
            return ""
            
        except Exception as e:
            print(f"[DUE get_company_due_date] ERROR: {e}")
            return ""

    def set_company_due_date(self, company_id: int, due: str) -> bool:
        """
        Establece la fecha de vencimiento fija para facturas.
        Guarda en sequences/{id}_meta y opcionalmente en companies/{id}.
        """
        try:
            due = (due or '').strip()
            
            # Guardar en sequences/{id}_meta
            meta_path = f"sequences/{company_id}_meta"
            print(f"[DUE set_company_due_date] Guardando en {meta_path}: {due}")
            
            meta_ref = self.db.collection('sequences').document(f"{company_id}_meta")
            meta_data = {
                'invoice_due_date': due,
                'updated_at': datetime.utcnow().isoformat(),
                'updated_by': self.user_id
            }
            meta_ref.set(meta_data, merge=True)
            print(f"[DUE set_company_due_date] Guardado en {meta_path}: OK")
            
            # Espejo en companies/{id} por compatibilidad
            company_path = f"companies/{company_id}"
            print(f"[DUE set_company_due_date] Reflejando en {company_path}: {due}")
            
            company_ref = self.db.collection('companies').document(str(company_id))
            company_ref.set({'invoice_due_date': due}, merge=True)
            print(f"[DUE set_company_due_date] Reflejado en {company_path}: OK")
            
            return True
            
        except Exception as e:
            print(f"[DUE set_company_due_date] ERROR: {e}")
            return False

    def get_next_ncf(self, company_id: int, ncf_type: str) -> str:
        """
        LEGACY: Mantiene compatibilidad con código existente.
        IMPORTANTE: Este método ahora INCREMENTA la secuencia (delega a allocate_next_ncf).
        Para preview sin incrementar, usar get_ncf_preview.
        
        Args:
            company_id: ID de la empresa
            ncf_type: Tipo de NCF (B01, B02, E31, etc.)
        
        Returns:
            NCF formateado y asignado (secuencia incrementada)
        """
        prefix3 = self._normalize_ncf_prefix(ncf_type)
        return self.allocate_next_ncf(company_id, prefix3)

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

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass