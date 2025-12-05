from __future__ import annotations
import sys, os, json, types
from pathlib import Path

# Evita problemas de sandbox del WebEngine en algunos entornos
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

# FIJAR ATRIBUTO ANTES DE CREAR QApplication
from PyQt6.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

# (Opcional) Import temprano del WebEngine
try:
    from PyQt6 import QtWebEngineWidgets, QtWebEngineCore  # noqa: F401
except Exception:
    pass

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

# IMPORTS DE TU LÓGICA Y DATOS
from data_access.firebase_data_access import FirebaseDataAccess
from logic import LogicController


def _ensure_facot_config_loaded(app: QApplication) -> None:
    try:
        import facot_config  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    QMessageBox.information(
        None,
        "Configuración requerida",
        "No se encontró 'facot_config'. Selecciona la base de datos SQLite (*.db).\n"
        "NOTA: Al usar Firebase, este archivo solo servirá de referencia local."
    )
    fn, _ = QFileDialog.getOpenFileName(
        None,
        "Selecciona la base de datos",
        "",
        "SQLite (*.db);;Todos (*.*)"
    )
    if not fn:
        fn = str(Path(os.getcwd()) / "dummy_fallback.db")

    # Módulo dinámico mínimo
    mod = types.ModuleType("facot_config")
    def get_db_path() -> str:
        return fn
    mod.get_db_path = get_db_path 
    def get_empresa_activa():
        return None
    mod.get_empresa_activa = get_empresa_activa 
    sys.modules["facot_config"] = mod

    # Persistir JSON
    try:
        cfg_path = Path(os.getcwd()) / "facot_config.json"
        cfg_path.write_text(json.dumps({"db_path": fn}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        try:
            appdata = os.environ.get("APPDATA") or str(Path.home())
            cfg_dir = Path(appdata) / "FACOT"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "facot_config.json").write_text(
                json.dumps({"db_path": fn}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

def main():
    app = QApplication.instance() or QApplication(sys.argv)

    _ensure_facot_config_loaded(app)
    import facot_config

    # ---------------------------
    # Aplicar tema
    # ---------------------------
    try:
        from utils.theme_manager import get_theme_manager
        tm = get_theme_manager()
        tm.set_app(app)
        saved_id = tm.load_saved_theme()
        theme_to_apply = saved_id or "light"
        tm.apply_theme(app, theme_to_apply)
        print(f"[THEME] Tema aplicado al inicio: {theme_to_apply}")
    except Exception as e:
        print(f"[THEME] No se pudo aplicar tema al inicio: {e}")

    # Bootstrap recursos
    try:
        from utils.bootstrap import ensure_first_run, ensure_required_resources
        ensure_first_run()
        ensure_required_resources(required_template_names=["invoice_template.html", "quotation_template.html"], parent=None)
    except Exception:
        pass

    # ---------------------------
    # INICIALIZACIÓN FIREBASE Y LOGIC
    # ---------------------------
    firebase_ready = False
    try:
        from firebase.firebase_client import ensure_initialized
        firebase_ready = ensure_initialized()
        if firebase_ready:
            print("[MAIN] Firebase inicializado correctamente")
        else:
            print("[MAIN] Firebase no disponible")
    except Exception as e:
        print(f"[MAIN] Error inicializando Firebase: {e}")

    # 1. Crear DataAccess (Backend)
    data_access = None
    if firebase_ready:
        try:
            current_user = os.environ.get("USERNAME", "system")
            data_access = FirebaseDataAccess(user_id=current_user)
            print(f"[MAIN] DataAccess creado. Usuario: {current_user}")
        except Exception as e:
            print(f"[MAIN] Error crítico creando FirebaseDataAccess: {e}")

    # 2. Crear LogicController (Puente)
    # Si data_access existe, LogicController funcionará en modo Proxy (Firebase Only)
    db_path = facot_config.get_db_path()
    logic = LogicController(db_path=db_path, data_access=data_access)

    if data_access:
        print("[MAIN] >>> MODO FIREBASE ACTIVADO <<<")
        # Backup scheduler
        try:
            from utils.backups import start_backup_scheduler
            start_backup_scheduler()
            print("[MAIN] Scheduler de backups iniciado")
        except Exception as e:
            print(f"[MAIN] Error iniciando scheduler: {e}")
    else:
        print("[MAIN] !!! MODO OFFLINE (SQLITE) !!!")

    # ---------------------------
    # INICIO DE UI (CORRECCIÓN CRÍTICA)
    # ---------------------------
    from ui_mainwindow import MainWindow
    
    # 1. Intentar inyectar en el constructor
    try:
        w = MainWindow(logic_controller=logic)
    except TypeError:
        print("[MAIN] Constructor de MainWindow no acepta argumentos. Iniciando estándar...")
        w = MainWindow()

    # 2. FORZAR LA INYECCIÓN (Sobrescribe cualquier LogicController "Zombi" creado internamente)
    print("[MAIN] 🛡️  BLINDAJE: Forzando LogicController correcto en la ventana principal...")
    w.logic = logic
    if hasattr(w, 'controller'):
        w.controller = logic
    
    # 3. Propagar a las pestañas hijas (Tablas de Facturas, Cotizaciones, etc.)
    if hasattr(w, 'invoice_tab'):
        print("[MAIN] Inyectando lógica en Pestaña Facturas...")
        if hasattr(w.invoice_tab, 'logic'): w.invoice_tab.logic = logic
        if hasattr(w.invoice_tab, 'controller'): w.invoice_tab.controller = logic
        # Recargar datos de la pestaña si es necesario
        if hasattr(w.invoice_tab, 'load_invoices'): w.invoice_tab.load_invoices()

    if hasattr(w, 'quotation_tab'):
        print("[MAIN] Inyectando lógica en Pestaña Cotizaciones...")
        if hasattr(w.quotation_tab, 'logic'): w.quotation_tab.logic = logic
        if hasattr(w.quotation_tab, 'controller'): w.quotation_tab.controller = logic

    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()