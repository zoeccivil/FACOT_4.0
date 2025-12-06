from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QWidget, QHeaderView, QDateEdit
)
from PyQt6.QtCore import QDate, Qt

# Asegúrate de que este import funcione en tu estructura de carpetas
from utils.asset_paths import copy_logo_to_assets, relativize_if_under_assets

class CompanyManagementWindow(QDialog):
    """
    Ventana para gestionar empresas.
    Conectada directamente a FirebaseDataAccess via 'logic_controller'.
    """

    SMALL_LINEHEIGHT = 24  # altura compacta para inputs

    def __init__(self, parent, logic_controller):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Empresas")
        self.resize(980, 560)

        # Este es tu FirebaseDataAccess
        self.logic = logic_controller

        self.selected_company_id: Optional[int] = None
        self._pending_logo_source_abs: Optional[str] = None
        self._companies_cache: List[Dict[str, Any]] = []

        self._build_ui()
        self._load_companies()

    # -------------------------
    # Normalización (Adaptado a tu JSON de Firebase)
    # -------------------------
    @staticmethod
    def _norm_full(row: Dict[str, Any]) -> Dict[str, Any]:
        """Asegura que el diccionario tenga todos los campos que la UI espera."""
        return {
            "id": row.get("id"),
            "name": row.get("name", ""),
            "rnc": row.get("rnc") or row.get("rnc_number", "") or "",
            "address_line1": row.get("address_line1") or row.get("address", "") or "",
            "address_line2": row.get("address_line2", "") or "",
            "phone": row.get("phone") or row.get("telefono", "") or "",
            "email": row.get("email") or row.get("correo") or "",
            "signature_name": row.get("signature_name", "") or "",
            "logo_path": row.get("logo_path", "") or "",
            "invoice_due_date": row.get("invoice_due_date", "") or "",
        }

    # -------------------------
    # UI Construction
    # -------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # --- Tabla de empresas ---
        table_frame = QWidget()
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.company_table = QTableWidget(0, 4)
        self.company_table.setHorizontalHeaderLabels(["Nombre de la Empresa", "RNC", "Teléfono", "Email"])
        header = self.company_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.company_table.verticalHeader().setVisible(False)
        self.company_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.company_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.company_table.cellClicked.connect(self._on_select)
        self.company_table.setStyleSheet("QTableWidget::item { padding: 4px 6px; }")
        table_layout.addWidget(self.company_table)
        main_layout.addWidget(table_frame, stretch=2)

        # --- Formulario ---
        form_frame = QWidget()
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(6)
        form_layout.setContentsMargins(4, 4, 4, 4)

        def compact_lineedit(placeholder: str = "") -> QLineEdit:
            le = QLineEdit()
            if placeholder:
                le.setPlaceholderText(placeholder)
            le.setMinimumHeight(self.SMALL_LINEHEIGHT)
            le.setMaximumHeight(self.SMALL_LINEHEIGHT + 2)
            return le

        # Row 1: Nombre / RNC
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Nombre:"))
        self.name_edit = compact_lineedit()
        row1.addWidget(self.name_edit, stretch=3)
        row1.addWidget(QLabel("RNC:"))
        self.rnc_edit = compact_lineedit()
        row1.addWidget(self.rnc_edit, stretch=1)
        form_layout.addLayout(row1)

        # Row 2: Dirección 1 / Dirección 2
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Dirección 1:"))
        self.address1_edit = compact_lineedit()
        row2.addWidget(self.address1_edit, stretch=3)
        row2.addWidget(QLabel("Dirección 2:"))
        self.address2_edit = compact_lineedit()
        row2.addWidget(self.address2_edit, stretch=2)
        form_layout.addLayout(row2)

        # Row 3: Teléfono / Email
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Teléfono:"))
        self.phone_edit = compact_lineedit()
        row3.addWidget(self.phone_edit, stretch=1)
        row3.addWidget(QLabel("Email:"))
        self.email_edit = compact_lineedit()
        row3.addWidget(self.email_edit, stretch=2)
        form_layout.addLayout(row3)

        # Row 4: Firma autorizada
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Firma autorizada (nombre):"))
        self.signature_edit = compact_lineedit()
        row4.addWidget(self.signature_edit, stretch=3)
        form_layout.addLayout(row4)

        # Row 5: Logo
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Logo (ruta relativa):"))
        self.logo_path_edit = compact_lineedit()
        row5.addWidget(self.logo_path_edit, stretch=3)
        btn_logo = QPushButton("Elegir logo…")
        btn_logo.setMinimumHeight(self.SMALL_LINEHEIGHT + 4)
        btn_logo.clicked.connect(self._browse_logo)
        row5.addWidget(btn_logo)
        form_layout.addLayout(row5)

        # Row 6: Vencimiento fijo
        row6 = QHBoxLayout()
        row6.addWidget(QLabel("Vencimiento fijo facturas:"))
        self.invoice_due_date_edit = QDateEdit()
        self.invoice_due_date_edit.setCalendarPopup(True)
        self.invoice_due_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.invoice_due_date_edit.setMinimumHeight(self.SMALL_LINEHEIGHT + 2)
        self.invoice_due_date_edit.setDate(QDate.currentDate())
        row6.addWidget(self.invoice_due_date_edit, stretch=1)
        btn_clear_due = QPushButton("Limpiar")
        btn_clear_due.setMinimumHeight(self.SMALL_LINEHEIGHT + 4)
        btn_clear_due.setToolTip("Deja el vencimiento vacío (N/A)")
        btn_clear_due.clicked.connect(lambda: self.invoice_due_date_edit.setDate(QDate.currentDate()))
        row6.addWidget(btn_clear_due)
        form_layout.addLayout(row6)

        main_layout.addWidget(form_frame, stretch=1)

        # --- Botones inferiores ---
        btns = QHBoxLayout()
        btn_new = QPushButton("Nuevo")
        btn_new.setMinimumHeight(self.SMALL_LINEHEIGHT + 6)
        btn_new.clicked.connect(self._clear_fields)
        btns.addWidget(btn_new)

        btn_save = QPushButton("Guardar Cambios")
        btn_save.setMinimumHeight(self.SMALL_LINEHEIGHT + 6)
        btn_save.clicked.connect(self._save_company)
        btns.addWidget(btn_save)

        btn_del = QPushButton("Eliminar Empresa")
        btn_del.setMinimumHeight(self.SMALL_LINEHEIGHT + 6)
        btn_del.clicked.connect(self._delete_company)
        btns.addWidget(btn_del)

        main_layout.addLayout(btns)

    # -------------------------
    # Carga de Datos
    # -------------------------
    def _load_companies(self):
        self.company_table.setRowCount(0)

        if not hasattr(self.logic, "get_all_companies"):
            QMessageBox.critical(self, "Error", "El backend no tiene el método get_all_companies")
            return

        # Llamada directa al backend
        try:
            raw = self.logic.get_all_companies() or []
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar empresas de Firebase:\n{e}")
            raw = []

        self._companies_cache = raw[:]

        # Llenar la tabla
        for row, c in enumerate(self._companies_cache):
            name = c.get("name", "")
            rnc = c.get("rnc") or c.get("rnc_number", "")
            phone = c.get("phone") or c.get("telefono", "")
            email = c.get("email") or c.get("correo", "")
            self.company_table.insertRow(row)
            self.company_table.setItem(row, 0, QTableWidgetItem(str(name)))
            self.company_table.setItem(row, 1, QTableWidgetItem(str(rnc)))
            self.company_table.setItem(row, 2, QTableWidgetItem(str(phone)))
            self.company_table.setItem(row, 3, QTableWidgetItem(str(email)))
            self.company_table.setRowHeight(row, 22)

    def _on_select(self, row, _column):
        if row < 0 or row >= len(self._companies_cache):
            return

        cid = self._companies_cache[row].get("id")
        if not cid:
            return

        self.selected_company_id = cid

        # Cargar detalles completos
        try:
            det_raw = self.logic.get_company_details(int(cid)) or {}
        except Exception:
            det_raw = self._companies_cache[row]  # Fallback

        det = self._norm_full(det_raw)

        # Rellenar formulario
        self.name_edit.setText(str(det["name"]))
        self.rnc_edit.setText(str(det["rnc"]))
        self.address1_edit.setText(str(det["address_line1"]))
        self.address2_edit.setText(str(det["address_line2"]))
        self.phone_edit.setText(str(det["phone"]))
        self.email_edit.setText(str(det["email"]))
        self.signature_edit.setText(str(det["signature_name"]))
        self.logo_path_edit.setText(str(det["logo_path"]))
        self._set_due_date_from_str(det.get("invoice_due_date") or "")

    def _clear_fields(self):
        self.selected_company_id = None
        self._pending_logo_source_abs = None
        self.name_edit.clear()
        self.rnc_edit.clear()
        self.address1_edit.clear()
        self.address2_edit.clear()
        self.phone_edit.clear()
        self.email_edit.clear()
        self.signature_edit.clear()
        self.logo_path_edit.clear()
        self.invoice_due_date_edit.setDate(QDate.currentDate())
        self.company_table.clearSelection()
        self.name_edit.setFocus()

    # -------------------------
    # Guardado
    # -------------------------
    def _save_company(self):
        # 1. Recolectar datos del form
        name = self.name_edit.text().strip()
        rnc = self.rnc_edit.text().strip()

        if not name or not rnc:
            QMessageBox.critical(self, "Error", "El Nombre y el RNC son obligatorios.")
            return

        address1 = self.address1_edit.text().strip()
        address2 = self.address2_edit.text().strip()
        phone = self.phone_edit.text().strip()
        email = self.email_edit.text().strip()
        signature_name = self.signature_edit.text().strip()
        fixed_due_date = self._dateedit_to_str(self.invoice_due_date_edit)

        logo_val = self.logo_path_edit.text().strip()

        # 2. Definir ID (existente o nuevo)
        is_new = self.selected_company_id is None

        try:
            if is_new:
                new_id = self.logic.add_company(name, rnc, address1)
                self.selected_company_id = new_id
                cid = new_id
            else:
                cid = int(self.selected_company_id)

            # 3. Procesar logo (requiere el ID para la ruta)
            logo_rel = self._prepare_logo_to_save(logo_val, cid)

            # 4. Preparar diccionario completo de actualización
            payload = {
                "name": name,
                "rnc": rnc,
                "address_line1": address1,
                "address": address1,  # compat
                "address_line2": address2,
                "phone": phone,
                "email": email,
                "signature_name": signature_name,
                "logo_path": logo_rel,
                "invoice_due_date": fixed_due_date,  # será guardado también en sequences/<id>_meta
            }

            # 5. Guardar campos extra
            self.logic.update_company_fields(cid, payload)

            QMessageBox.information(self, "Éxito", "Empresa guardada correctamente.")

            # Recargar tabla y re-seleccionar
            self._load_companies()
            self._reselect_by_id(cid)

            # Notificar al padre si tiene método de actualización
            if hasattr(self.parent(), "_populate_companies"):
                try:
                    self.parent()._populate_companies()
                except Exception:
                    pass

        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", f"Ocurrió un error:\n{e}")

    def _delete_company(self):
        if not self.selected_company_id:
            QMessageBox.warning(self, "Sin Selección", "Selecciona una empresa para eliminar.")
            return

        confirm = QMessageBox.question(
            self, "Confirmar",
            "¿Seguro que deseas eliminar esta empresa?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            if hasattr(self.logic, "delete_company"):
                success, msg = self.logic.delete_company(self.selected_company_id)
                if success:
                    QMessageBox.information(self, "Eliminado", "Empresa eliminada.")
                    self._clear_fields()
                    self._load_companies()
                else:
                    QMessageBox.warning(self, "Error", f"No se pudo eliminar: {msg}")
            else:
                QMessageBox.critical(self, "Error", "El backend no soporta eliminación de empresas.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error técnico al eliminar:\n{e}")

    # -------------------------
    # Helpers y Utilidades
    # -------------------------
    def _browse_logo(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Seleccionar Logo", "", "Imágenes (*.png *.jpg *.jpeg *.svg);;Todos los archivos (*)")
        if not fn:
            return
        
        print(f"[COMPANY-LOGO] Selected logo file: {fn}")
        
        if self.selected_company_id:
            # Empresa existente: intentar subir a storage
            try:
                cid = int(self.selected_company_id)
                storage_path = f"logos/company_{cid}{os.path.splitext(fn)[1]}"
                
                # Intentar upload_file_to_storage
                url = None
                if hasattr(self.logic, 'upload_file_to_storage'):
                    try:
                        url = self.logic.upload_file_to_storage(fn, storage_path)
                        if url:
                            print(f"[COMPANY-LOGO] Successfully uploaded to storage: {url}")
                            self.logo_path_edit.setText(url)
                            QMessageBox.information(self, "Logo", f"Logo subido exitosamente al storage.\n\nURL: {url}")
                            return
                        else:
                            print(f"[COMPANY-LOGO] upload_file_to_storage returned None, falling back")
                    except Exception as e:
                        print(f"[COMPANY-LOGO] upload_file_to_storage failed: {e}, falling back")
                
                # Fallback a copy_logo_to_assets
                print(f"[COMPANY-LOGO] Falling back to copy_logo_to_assets")
                rel = copy_logo_to_assets(fn, cid)
                self.logo_path_edit.setText(rel)
                QMessageBox.information(self, "Logo", f"Logo copiado a assets (ruta relativa):\n\n{rel}")
            except Exception as e:
                QMessageBox.warning(self, "Logo", f"No se pudo procesar el logo:\n{e}")
        else:
            # Nueva empresa: guardar path temporalmente
            self._pending_logo_source_abs = fn
            self.logo_path_edit.setText(os.path.basename(fn))
            print(f"[COMPANY-LOGO] Pending logo for new company: {fn}")

    def _prepare_logo_to_save(self, current_logo_value: str, company_id: int) -> str:
        """
        Prepara el logo para guardar: intenta subir a storage, fallback a copy_logo_to_assets.
        
        Returns:
            URL (si se subió a storage) o ruta relativa (si se copió a assets)
        """
        print(f"[COMPANY-LOGO] _prepare_logo_to_save: current_value='{current_logo_value}', company_id={company_id}")
        
        # Caso 1: pending_logo (nueva empresa o cambio de logo)
        if self._pending_logo_source_abs:
            local_path = self._pending_logo_source_abs
            print(f"[COMPANY-LOGO] Processing pending logo: {local_path}")
            
            # Intentar subir a storage
            storage_path = f"logos/company_{company_id}{os.path.splitext(local_path)[1]}"
            if hasattr(self.logic, 'upload_file_to_storage'):
                try:
                    url = self.logic.upload_file_to_storage(local_path, storage_path)
                    if url and url.startswith(('http://', 'https://')):
                        print(f"[COMPANY-LOGO] Uploaded pending logo to storage: {url}")
                        self._pending_logo_source_abs = None
                        return url
                    else:
                        print(f"[COMPANY-LOGO] upload_file_to_storage returned non-URL: {url}")
                except Exception as e:
                    print(f"[COMPANY-LOGO] Error uploading pending logo to storage: {e}")
            
            # Fallback a copy_logo_to_assets
            try:
                rel = copy_logo_to_assets(local_path, int(company_id))
                print(f"[COMPANY-LOGO] Copied pending logo to assets: {rel}")
                self._pending_logo_source_abs = None
                return rel
            except Exception as e:
                print(f"[COMPANY-LOGO] Error copying pending logo to assets: {e}")
                self._pending_logo_source_abs = None
                return ""

        # Caso 2: valor actual es URL http(s) - mantener
        if current_logo_value and current_logo_value.startswith(('http://', 'https://')):
            print(f"[COMPANY-LOGO] Current value is URL, keeping: {current_logo_value}")
            return current_logo_value

        # Caso 3: valor actual vacío
        if not current_logo_value:
            print(f"[COMPANY-LOGO] No logo value")
            return ""

        # Caso 4: ruta file:/// o absoluta - intentar subir o relativizar
        val = current_logo_value
        if val.lower().startswith("file:///") or os.path.isabs(val):
            # Primero intentar relativizar si ya está bajo assets
            rel_try = relativize_if_under_assets(val)
            if rel_try != val:
                print(f"[COMPANY-LOGO] Relativized existing logo: {rel_try}")
                return rel_try
            
            # Extraer ruta absoluta
            abs_src = val[8:].replace("/", os.sep) if val.lower().startswith("file:///") else val
            
            # Intentar subir a storage
            if hasattr(self.logic, 'upload_file_to_storage') and os.path.exists(abs_src):
                storage_path = f"logos/company_{company_id}{os.path.splitext(abs_src)[1]}"
                try:
                    url = self.logic.upload_file_to_storage(abs_src, storage_path)
                    if url and url.startswith(('http://', 'https://')):
                        print(f"[COMPANY-LOGO] Uploaded absolute path to storage: {url}")
                        return url
                except Exception as e:
                    print(f"[COMPANY-LOGO] Error uploading absolute path to storage: {e}")
            
            # Fallback a copy_logo_to_assets
            try:
                rel = copy_logo_to_assets(abs_src, int(company_id))
                print(f"[COMPANY-LOGO] Copied absolute path to assets: {rel}")
                return rel
            except Exception as e:
                print(f"[COMPANY-LOGO] Error copying absolute path to assets: {e}")
                return ""
        
        # Caso 5: ruta relativa - mantener
        print(f"[COMPANY-LOGO] Keeping relative path: {val}")
        return val.replace("\\", "/")

    def _dateedit_to_str(self, de: QDateEdit) -> str:
        try:
            qd = de.date()
            return f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
        except Exception:
            return ""

    def _set_due_date_from_str(self, s: str):
        if not s:
            self.invoice_due_date_edit.setDate(QDate.currentDate())
            return
        try:
            parts = s[:10].split("-")
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            self.invoice_due_date_edit.setDate(QDate(y, m, d))
        except Exception:
            self.invoice_due_date_edit.setDate(QDate.currentDate())

    def _reselect_by_id(self, company_id: Optional[int]):
        if not company_id:
            return
        for row, c in enumerate(self._companies_cache):
            if c.get("id") == company_id:
                self.company_table.selectRow(row)
                break