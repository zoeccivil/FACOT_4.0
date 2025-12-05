"""
Diálogo de migración Selectiva SQLite -> Firebase.
Ubicación: db_migration_window.py
"""
import sys
import sqlite3
import time
import traceback
from datetime import datetime
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFileDialog, QCheckBox, QLineEdit,
    QGroupBox, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

class MigrationThread(QThread):
    """
    Thread que ejecuta la migración basada en un PLAN seleccionado por el usuario.
    """
    progress_updated = pyqtSignal(int, str)
    log_message = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, db_path, migration_plan):
        super().__init__()
        self.db_path = db_path
        self.migration_plan = migration_plan # Dict: {'invoices': {'migrate': True, 'clean': True}, ...}
        self.is_running = True
        self.db_firestore = None

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            self.log_message.emit("--- INICIANDO PROCESO ---", "blue")
            
            # --- IMPORTS ---
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore
                from firebase.firebase_client import get_firebase_client
            except ImportError as e:
                self.log_message.emit(f"Faltan librerías: {e}", "red")
                return

            # 1. CONEXIÓN FIREBASE
            try:
                self.log_message.emit("Conectando a Firebase...", "black")
                client = get_firebase_client()
                
                if not client.is_available():
                    cred_path = "firebase_credentials.json"
                    if not os.path.exists(cred_path): cred_path = "E:/Dropbox/PROGAIN/FACOT/firebase_credentials.json"
                    
                    if not os.path.exists(cred_path):
                         self.log_message.emit(f"No credencial: {cred_path}", "red"); return

                    if not firebase_admin._apps:
                        cred = credentials.Certificate(cred_path)
                        firebase_admin.initialize_app(cred)
                    self.db_firestore = firestore.client()
                else:
                    self.db_firestore = client.get_firestore()
            except Exception as e:
                self.log_message.emit(f"Error Firebase: {e}", "red"); return

            # 2. CONEXIÓN SQLITE
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # --- EJECUCIÓN DEL PLAN ---
            total_tasks = len([t for t in self.migration_plan.values() if t['migrate'] or t['clean']])
            current_task = 0

            for table, actions in self.migration_plan.items():
                if not self.is_running: break
                
                firebase_col = table # Mismo nombre por defecto
                
                # FASE 1: LIMPIEZA (Si se seleccionó)
                if actions['clean']:
                    self.log_message.emit(f"🗑️ Limpiando colección '{firebase_col}'...", "orange")
                    self._delete_collection(self.db_firestore.collection(firebase_col), 50)
                    self.log_message.emit(f"   Colección '{firebase_col}' vaciada.", "orange")

                # FASE 2: MIGRACIÓN (Si se seleccionó)
                if actions['migrate']:
                    current_task += 1
                    percent = int((current_task / total_tasks) * 100)
                    self.progress_updated.emit(percent, f"Migrando {table}...")
                    
                    # Ruteo de lógica
                    if table == 'invoices':
                        self._migrate_invoices_complete(cursor)
                    elif table == 'quotations':
                        self._migrate_quotations_complete(cursor)
                    else:
                        self._migrate_generic_table(cursor, table)

            conn.close()
            self.progress_updated.emit(100, "Finalizado")
            self.log_message.emit("=== PROCESO COMPLETADO ===", "green")
            self.finished.emit()

        except Exception as e:
            self.log_message.emit(f"ERROR CRÍTICO: {e}", "red")
            self.log_message.emit(traceback.format_exc(), "red")

    # --- HELPERS ---
    def _delete_collection(self, coll_ref, batch_size):
        docs = list(coll_ref.limit(batch_size).stream())
        while docs:
            batch = self.db_firestore.batch()
            for doc in docs:
                batch.delete(doc.reference)
                # Borrar subcolecciones 'items'
                sub = doc.reference.collection('items').limit(50).stream()
                for s in sub: batch.delete(s.reference)
            batch.commit()
            if not self.is_running: return
            docs = list(coll_ref.limit(batch_size).stream())

    def _migrate_generic_table(self, cursor, table):
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            if not rows:
                self.log_message.emit(f"Tabla '{table}' vacía localmente.", "black")
                return

            batch = self.db_firestore.batch()
            count = 0
            
            # Import firestore for timestamp
            from firebase_admin import firestore

            for row in rows:
                data = dict(row)
                doc_id = None
                
                # ID Strategy
                if 'id' in data:
                    doc_id = str(data.pop('id'))
                elif 'code' in data:
                    doc_id = str(data['code'])
                
                # Timestamp
                data['updated_at'] = firestore.SERVER_TIMESTAMP
                
                # Write
                ref = self.db_firestore.collection(table)
                doc_ref = ref.document(doc_id) if doc_id else ref.document()
                batch.set(doc_ref, data)
                count += 1
                
                if count % 400 == 0:
                    batch.commit()
                    batch = self.db_firestore.batch()

            if count % 400 != 0: batch.commit()
            self.log_message.emit(f"✅ {table}: {count} registros subidos.", "green")

        except Exception as e:
            self.log_message.emit(f"Error en {table}: {e}", "red")

    def _migrate_invoices_complete(self, cursor):
        try:
            cursor.execute("SELECT * FROM invoices")
            rows = cursor.fetchall()
            count = 0
            for r in rows:
                if not self.is_running: break
                d = dict(r)
                if 'id' not in d: continue
                
                inv_id = str(d.pop('id'))
                
                # Tipos
                d['total_amount'] = float(d.get('total_amount') or 0)
                d['company_id'] = int(d.get('company_id') or 0)
                
                doc_ref = self.db_firestore.collection('invoices').document(inv_id)
                doc_ref.set(d)
                
                # Items
                cursor.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (inv_id,))
                items = cursor.fetchall()
                batch = self.db_firestore.batch()
                for it in items:
                    it_d = dict(it)
                    sid = str(it_d.pop('id'))
                    it_d.pop('invoice_id', None)
                    it_d['quantity'] = float(it_d.get('quantity') or 0)
                    it_d['unit_price'] = float(it_d.get('unit_price') or 0)
                    batch.set(doc_ref.collection('items').document(sid), it_d)
                batch.commit()
                count += 1
            self.log_message.emit(f"✅ Invoices: {count} facturas completas subidas.", "green")
        except Exception as e:
            self.log_message.emit(f"Error Invoices: {e}", "red")

    def _migrate_quotations_complete(self, cursor):
        try:
            cursor.execute("SELECT * FROM quotations")
            rows = cursor.fetchall()
            count = 0
            for r in rows:
                if not self.is_running: break
                d = dict(r)
                q_id = str(d.pop('id'))
                d['total_amount'] = float(d.get('total_amount') or 0)
                d['company_id'] = int(d.get('company_id') or 0)
                
                doc_ref = self.db_firestore.collection('quotations').document(q_id)
                doc_ref.set(d)
                
                cursor.execute("SELECT * FROM quotation_items WHERE quotation_id=?", (q_id,))
                items = cursor.fetchall()
                batch = self.db_firestore.batch()
                for it in items:
                    it_d = dict(it)
                    sid = str(it_d.pop('id'))
                    it_d.pop('quotation_id', None)
                    it_d['quantity'] = float(it_d.get('quantity') or 0)
                    batch.set(doc_ref.collection('items').document(sid), it_d)
                batch.commit()
                count += 1
            self.log_message.emit(f"✅ Quotations: {count} cotizaciones completas subidas.", "green")
        except Exception as e:
            self.log_message.emit(f"Error Quotations: {e}", "red")


class MigrationDialog(QDialog):
    def __init__(self, parent=None, default_db_path=None):
        super().__init__(parent)
        self.setWindowTitle("Migrador Selectivo FACOT")
        self.resize(900, 700)
        self.thread = None
        self.default_db_path = default_db_path or ""
        self._init_ui()
        
        # Si hay ruta, analizar al inicio
        if self.default_db_path and os.path.exists(self.default_db_path):
            self._analyze_db(self.default_db_path)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 1. Selección de Archivo
        gb_file = QGroupBox("1. Origen de Datos (SQLite)")
        hb_file = QHBoxLayout()
        self.txt_path = QLineEdit(self.default_db_path)
        self.txt_path.setPlaceholderText("Ruta del archivo .db")
        btn_browse = QPushButton("Examinar...")
        btn_browse.clicked.connect(self._browse)
        btn_reload = QPushButton("Analizar")
        btn_reload.clicked.connect(lambda: self._analyze_db(self.txt_path.text()))
        
        hb_file.addWidget(self.txt_path)
        hb_file.addWidget(btn_browse)
        hb_file.addWidget(btn_reload)
        gb_file.setLayout(hb_file)
        layout.addWidget(gb_file)

        # 2. Tabla de Selección
        gb_plan = QGroupBox("2. Plan de Migración (Selecciona qué hacer)")
        vb_plan = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Tabla Local", "Registros", "Migrar a Firebase", "Limpiar Firebase antes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        vb_plan.addWidget(self.table)
        gb_plan.setLayout(vb_plan)
        layout.addWidget(gb_plan)

        # 3. Log y Progreso
        gb_log = QGroupBox("3. Progreso")
        vb_log = QVBoxLayout()
        self.pbar = QProgressBar()
        self.pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background: #f5f5f5; font-family: Consolas; font-size: 11px;")
        vb_log.addWidget(self.pbar)
        vb_log.addWidget(self.txt_log)
        gb_log.setLayout(vb_log)
        layout.addWidget(gb_log)

        # 4. Botones
        hb_btns = QHBoxLayout()
        self.btn_run = QPushButton("EJECUTAR MIGRACIÓN")
        self.btn_run.setMinimumHeight(45)
        self.btn_run.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; font-size: 14px;")
        self.btn_run.clicked.connect(self._start)
        self.btn_close = QPushButton("Salir")
        self.btn_close.clicked.connect(self.close)
        
        hb_btns.addWidget(self.btn_run)
        hb_btns.addWidget(self.btn_close)
        layout.addLayout(hb_btns)

    def _browse(self):
        fn, _ = QFileDialog.getOpenFileName(self, "BD", "", "SQLite (*.db)")
        if fn:
            self.txt_path.setText(fn)
            self._analyze_db(fn)

    def _analyze_db(self, path):
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error", "Archivo no encontrado.")
            return

        self.table.setRowCount(0)
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [r[0] for r in cur.fetchall()]
            
            # Filtrar subtablas que no se migran solas
            ignored = ['invoice_items', 'quotation_items']
            tables = [t for t in tables if t not in ignored]
            
            self.table.setRowCount(len(tables))
            
            for i, tbl in enumerate(tables):
                # Count
                try:
                    count = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                except: count = "?"
                
                # Nombre
                self.table.setItem(i, 0, QTableWidgetItem(tbl))
                # Count
                item_count = QTableWidgetItem(str(count))
                item_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 1, item_count)
                
                # Check Migrate
                chk_mig = QCheckBox()
                chk_mig.setChecked(True) # Por defecto sí
                # Centrar checkbox
                w_mig = QWidget(); l_mig = QHBoxLayout(w_mig); l_mig.addWidget(chk_mig); l_mig.setAlignment(Qt.AlignmentFlag.AlignCenter); l_mig.setContentsMargins(0,0,0,0)
                self.table.setCellWidget(i, 2, w_mig)
                
                # Check Clean
                chk_clean = QCheckBox()
                chk_clean.setChecked(True) # Por defecto limpiar
                chk_clean.setStyleSheet("QCheckBox::indicator { border: 1px solid red; }") # Aviso visual
                w_cln = QWidget(); l_cln = QHBoxLayout(w_cln); l_cln.addWidget(chk_clean); l_cln.setAlignment(Qt.AlignmentFlag.AlignCenter); l_cln.setContentsMargins(0,0,0,0)
                self.table.setCellWidget(i, 3, w_cln)

            conn.close()
            self.txt_log.append(f"Análisis completado: {len(tables)} tablas encontradas.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer la BD: {e}")

    def _start(self):
        plan = {}
        for i in range(self.table.rowCount()):
            tbl_name = self.table.item(i, 0).text()
            
            # Obtener checkboxes desde los widgets contenedores
            w_mig = self.table.cellWidget(i, 2)
            chk_mig = w_mig.layout().itemAt(0).widget()
            
            w_cln = self.table.cellWidget(i, 3)
            chk_cln = w_cln.layout().itemAt(0).widget()
            
            plan[tbl_name] = {
                'migrate': chk_mig.isChecked(),
                'clean': chk_cln.isChecked()
            }
        
        # Validar si hay algo que hacer
        if not any(p['migrate'] or p['clean'] for p in plan.values()):
            QMessageBox.warning(self, "Nada que hacer", "Selecciona al menos una acción en la tabla.")
            return

        confirm = QMessageBox.question(self, "Confirmar", 
                                       "Se iniciará la operación según lo seleccionado en la tabla.\n¿Continuar?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes: return

        self.btn_run.setEnabled(False)
        self.txt_log.clear()
        
        self.thread = MigrationThread(self.txt_path.text(), plan)
        self.thread.log_message.connect(self._log)
        self.thread.progress_updated.connect(self._progress)
        self.thread.finished.connect(self._finished)
        self.thread.start()

    def _log(self, msg, color):
        self.txt_log.append(f'<span style="color:{color}">{msg}</span>')

    def _progress(self, val, txt):
        self.pbar.setValue(val)
        self.pbar.setFormat(f"{txt} %p%")

    def _finished(self):
        self.btn_run.setEnabled(True)
        QMessageBox.information(self, "Listo", "Proceso completado.")

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    # Ruta de prueba
    w = MigrationDialog(default_db_path="C:/Users/ZOEC CIVIL DESK/AppData/Roaming/FACOT/facturas_db.db")
    w.show()
    sys.exit(app.exec())