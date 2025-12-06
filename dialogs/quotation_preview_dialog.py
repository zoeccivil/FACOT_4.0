from __future__ import annotations

import os
import json
import webbrowser
import re
import urllib.parse
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox, QSizePolicy, QInputDialog
)
from PyQt6.QtCore import QUrl, QTimer, QByteArray
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Config opcional (vencimientos y logos)
try:
    import facot_config
except Exception:
    try:
        import config_facot as facot_config
    except Exception:
        class _Cfg:
            INVOICE_DUE_DAYS = 0
            INVOICE_FIXED_DUE_DATE = ""  # "YYYY-MM-DD"
            COMPANY_LOGOS = {}  # {company_id(str/int) or name: path}
            DEFAULT_LOGO_PATH = ""
        facot_config = _Cfg()

# Inyector HTML opcional
try:
    from utils.html_injector import build_html_with_json_block
except Exception:
    build_html_with_json_block = None

# Raíz de datos para resolver rutas relativas
try:
    from utils.template_manager import get_data_root
except Exception:
    def get_data_root():
        return os.getcwd()


def _to_file_uri(path: str) -> str:
    if not path:
        return ""
    p = os.path.abspath(path)
    if os.name == "nt":
        return "file:///" + p.replace("\\", "/")
    return "file://" + p


def _resolve_logo_uri(company: Dict[str, Any], tpl_from_db: Optional[Dict[str, Any]] = None) -> str:
    candidates: List[str] = []
    db_logo = (company or {}).get("logo_path") or ""
    if db_logo:
        candidates.append(db_logo)
    tpl_logo = (tpl_from_db or {}).get("logo_path") or ""
    if tpl_logo:
        candidates.append(tpl_logo)

    logos = getattr(facot_config, "COMPANY_LOGOS", {}) or {}
    cid = company.get("id")
    name = (company.get("name") or "").strip()
    if cid is not None:
        key_id = str(cid)
        if key_id in logos:
            candidates.append(logos[key_id])
    if name and name in logos:
        candidates.append(logos[name])

    default_logo = getattr(facot_config, "DEFAULT_LOGO_PATH", "") or ""
    if default_logo:
        candidates.append(default_logo)

    root = get_data_root()

    print("\n[QT-LOGO] _resolve_logo_uri()")
    print(f"  company.id={cid} name='{name}'")
    print(f"  raw company.logo_path='{db_logo}'  tpl.logo_path='{tpl_logo}'")
    print(f"  data_root='{root}'")
    print(f"  candidates (ordered)={candidates}")

    for c in candidates:
        if not c:
            continue
        if isinstance(c, str) and c.startswith("file:///"):
            local = c.replace("file:///", "")
            if os.path.exists(local):
                print(f"  -> PICK file URI as-is: {c} (exists)")
                return c
            else:
                print(f"  .. skip file URI (not found): {c}")
                continue
        try:
            rel = os.path.join(root, c)
            if os.path.exists(rel):
                uri = _to_file_uri(rel)
                print(f"  -> PICK relative to data_root: '{c}' -> '{rel}' -> '{uri}'")
                return uri
            else:
                print(f"  .. not found relative: '{rel}'")
        except Exception as e:
            print(f"  .. join error relative '{c}': {e}")

        if os.path.isabs(c) and os.path.exists(c):
            uri = _to_file_uri(c)
            print(f"  -> PICK absolute path: '{c}' -> '{uri}'")
            return uri
        elif os.path.isabs(c):
            print(f"  .. absolute path not found: '{c}'")

        if isinstance(c, str) and c.startswith(("http://", "https://")):
            print(f"  -> PICK http(s) URL: {c}")
            return c

    print("  !! NO LOGO FOUND - returning empty string")
    return ""


def _prepare_company_data_for_preview(company_record: Dict[str, Any], tpl_from_db: Optional[Dict[str, Any]] = None, logic_controller=None) -> Dict[str, Any]:
    company = dict(company_record or {})

    # Debug inputs
    print("\n[QT-LOGO] _prepare_company_data_for_preview() - INPUTS")
    try:
        print(f"  INPUT company: id={company.get('id')} name='{company.get('name')}' logo_path='{company.get('logo_path')}'")
        print(f"  INPUT template.logo_path='{(tpl_from_db or {}).get('logo_path')}'")
    except Exception:
        pass

    # Refrescar desde backend (incluye firma, due_date y branding en companies/<id>)
    try:
        cid = company.get("id")
        if logic_controller and cid:
            details = logic_controller.get_company_details(cid) or {}
            print(f"  [FALLBACK] get_company_details({cid}) -> {details}")
            for key in [
                "address_line1","address_line2","address","signature_name","authorized_name","logo_path",
                "phone","email","rnc","invoice_due_date",
                # Branding Opción A:
                "primary_color","secondary_color","font_name","font_size","layout","header_lines","footer_lines","show_logo"
            ]:
                # Si ya hay valor en company, respétalo; si no, toma el remoto
                if company.get(key) in (None, "", []) and details.get(key) is not None:
                    company[key] = details.get(key)
    except Exception as e:
        print(f"  [FALLBACK ERROR] get_company_details failed: {e}")

    # Normalizar fecha de vencimiento si falta: buscar helpers y sequences/<id>_meta
    from datetime import datetime
    def _normalize_date_str(s: Optional[str]) -> str:
        if not s: return ""
        try:
            s2 = str(s).strip()
            if len(s2) >= 10 and s2[4] == '-' and s2[7] == '-':
                return s2[:10]
            try:
                d = datetime.fromisoformat(s2[:19])
                return d.strftime("%Y-%m-%d")
            except Exception:
                try:
                    parts = s2.replace("/", "-").split("-")
                    if len(parts) >= 3:
                        y, m, d = parts[0], parts[1], parts[2]
                        if len(y) == 4:
                            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                except Exception:
                    pass
            return ""
        except Exception:
            return ""

    try:
        if not (company.get("invoice_due_date") or "").strip() and logic_controller:
            for fn in ("get_company_due_date", "get_company_invoice_due_date", "get_company_due", "get_invoice_due_date"):
                try:
                    if hasattr(logic_controller, fn):
                        v = getattr(logic_controller, fn)(company.get("id"))
                        v_norm = _normalize_date_str(v)
                        if v_norm:
                            company["invoice_due_date"] = v_norm
                            print(f"  [FALLBACK-DUE] obtained due_date via {fn}: {v_norm}")
                            break
                except Exception as e_fn:
                    print(f"  [FALLBACK-DUE] {fn} raised: {e_fn}")
            try:
                da = getattr(logic_controller, "data_access", None) or getattr(logic_controller, "dataAccess", None)
                if da and hasattr(da, "db"):
                    mid = f"{company.get('id')}_meta"
                    doc = da.db.collection("sequences").document(mid).get()
                    if doc and getattr(doc, "exists", False):
                        dd = doc.to_dict() or {}
                        v2 = dd.get("invoice_due_date") or dd.get("due_date") or ""
                        v2n = _normalize_date_str(v2)
                        if v2n and not company.get("invoice_due_date"):
                            company["invoice_due_date"] = v2n
                            print(f"  [FALLBACK-DUE] obtained due_date from sequences/{mid}: {v2n}")
            except Exception as e_da:
                print(f"  [FALLBACK-DUE] data_access check error: {e_da}")
    except Exception:
        pass

    # Campos básicos
    company["name"] = company.get("name") or company.get("company_name") or ""
    company["rnc"] = company.get("rnc") or company.get("rnc_number") or company.get("rnc_cliente") or ""
    company["phone"] = company.get("phone") or company.get("telefono") or ""
    company["email"] = company.get("email") or company.get("correo") or ""

    a1 = (company.get("address_line1") or company.get("address") or "").strip()
    a2 = (company.get("address_line2") or "").strip()
    company["address_line1"] = a1
    company["address_line2"] = a2
    address_full = (a1 + (" " + a2 if a2 else "")).strip() or (company.get("address") or "").strip()
    company["address"] = address_full or "Dirección no especificada"

    # Firma autorizada
    sig = ""
    for k in ("signature_name", "authorized_name", "firma", "signature", "authorized_signer", "authorized"):
        v = company.get(k)
        if v and isinstance(v, str) and v.strip():
            sig = v.strip()
            break
    if not sig and logic_controller and company.get("id"):
        try:
            details2 = logic_controller.get_company_details(company.get("id")) or {}
            for k in ("signature_name", "authorized_name", "firma", "signature", "authorized_signer", "authorized"):
                v = details2.get(k)
                if v and isinstance(v, str) and v.strip():
                    sig = v.strip()
                    break
            if sig:
                print(f"  [FALLBACK-2] Found signature in remote details: '{sig}'")
        except Exception as e:
            print(f"  [FALLBACK-2 ERROR] fetching company details for signature: {e}")
    company["signature_name"] = sig
    company["authorized_name"] = sig

    # Logo: Opción A → usar URL pública almacenada en companies.logo_path. No generar signed URL.
    resolved = company.get("logo_path") or (tpl_from_db or {}).get("logo_path") or ""
    company["logo_path"] = resolved

    # Branding: priorizar companies/<id>
    company["primary_color"] = company.get("primary_color") or (tpl_from_db or {}).get("primary_color") or "#0087C3"
    company["secondary_color"] = company.get("secondary_color") or (tpl_from_db or {}).get("secondary_color") or "#F5F5F5"
    company["header_lines"] = company.get("header_lines") or (tpl_from_db or {}).get("header_lines") or ["", "", ""]
    company["footer_lines"] = company.get("footer_lines") or (tpl_from_db or {}).get("footer_lines") or []
    company["font_name"] = company.get("font_name") or (tpl_from_db or {}).get("font_name") or "Inter"
    company["font_size"] = company.get("font_size") or (tpl_from_db or {}).get("font_size") or 13
    company["layout"] = company.get("layout") or (tpl_from_db or {}).get("layout") or "default"

    # Normalizar due_date final
    try:
        company["invoice_due_date"] = _normalize_date_str(company.get("invoice_due_date") or "")
    except Exception:
        company["invoice_due_date"] = (company.get("invoice_due_date") or "").strip()

    # Debug outputs
    print("[QT-LOGO] _prepare_company_data_for_preview() - OUTPUTS")
    try:
        print(f"  OUTPUT company.logo_path='{company.get('logo_path')}' (display-ready)")
        print(f"  OUTPUT company.primary_color='{company.get('primary_color')}', secondary_color='{company.get('secondary_color')}'")
        print(f"  OUTPUT company.header_lines={company.get('header_lines')}, footer_lines={company.get('footer_lines')}")
        print(f"  OUTPUT company.name='{company.get('name')}', rnc='{company.get('rnc')}'")
        print(f"  OUTPUT company.address='{company.get('address')}'")
        print(f"  OUTPUT company.signature_name='{company.get('signature_name')}' (authorized_name='{company.get('authorized_name')}')")
        print(f"  OUTPUT company.invoice_due_date='{company.get('invoice_due_date','')}'")
    except Exception:
        pass

    return company


def _compute_due_date_if_missing(quotation: Dict[str, Any]) -> None:
    if not isinstance(quotation, dict):
        return
    if quotation.get("due_date") and quotation.get("due_date") != quotation.get("date"):
        return
    fixed = getattr(facot_config, "INVOICE_FIXED_DUE_DATE", "") or ""
    if fixed:
        quotation["due_date"] = fixed
        return
    days = int(getattr(facot_config, "INVOICE_DUE_DAYS", 0) or 0)
    inv_date = (quotation.get("date") or "").strip()
    if days > 0 and inv_date:
        try:
            d = datetime.strptime(inv_date, "%Y-%m-%d")
            new_due_date = (d + timedelta(days=days)).strftime("%Y-%m-%d")
            if new_due_date != inv_date:
                quotation["due_date"] = new_due_date
        except Exception:
            pass


def _ensure_units(quotation: Dict[str, Any], logic_controller=None) -> None:
    try:
        items = quotation.get("items") or []

        if logic_controller:
            try:
                from services import UnitResolver
                resolver = UnitResolver(logic_controller)
                resolver.resolve_items(items)
                return
            except Exception as e:
                print(f"[ENSURE_UNITS] Could not use UnitResolver: {e}, falling back to simple method")

        for it in items:
            if not (it.get("unit") or "").strip():
                it["unit"] = "UND"
    except Exception as e:
        print(f"[ENSURE_UNITS] Error: {e}")


def _local_build_html_with_json_block(template_path: str, company: Dict[str, Any], tpl: Dict[str, Any], quotation: Dict[str, Any]) -> str:
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    payload = {"COMPANY": company or {}, "TEMPLATE": tpl or {}, "QUOTATION": quotation or {}}
    js = json.dumps(payload, ensure_ascii=False).replace("</script>", "<\\/script>")
    html = html.replace("/* INJECT_JSON_PLACEHOLDER */", js)
    return html


class QuotationPreviewDialog(QDialog):
    def __init__(
        self,
        company: Dict[str, Any],
        template: Dict[str, Any],
        quotation: Dict[str, Any],
        template_path: str = "quotation_template.html",
        parent=None,
        debug: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Vista previa - Cotización")
        self.resize(1000, 800)

        self.raw_company = company or {}
        self.raw_template = template or {}
        self.raw_quotation = quotation or {}

        print("\n" + "=" * 80)
        print("[QUOTATION_PREVIEW_DIALOG] PAYLOAD RECIBIDO:")
        print("=" * 80)
        try:
            import json as _json
            print("\n[RAW_COMPANY]:")
            print(_json.dumps(self.raw_company, ensure_ascii=False, indent=2))
            print("\n[RAW_TEMPLATE]:")
            print(_json.dumps(self.raw_template, ensure_ascii=False, indent=2))
            print("\n[RAW_QUOTATION]:")
            print(_json.dumps(self.raw_quotation, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"[ERROR] No se pudo serializar: {e}")
            print(f"raw_company: {self.raw_company}")
            print(f"raw_template: {self.raw_template}")
            print(f"raw_quotation: {self.raw_quotation}")
        print("=" * 80 + "\n")

        self.template_path = template_path
        self.debug = bool(debug)

        self._last_payload = {}

        self._build_ui()
        self._load_html()

    def _build_ui(self):
        v = QVBoxLayout(self)
        self.view = QWebEngineView(self)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        v.addWidget(self.view)

        row = QHBoxLayout()
        self.btn_export_pdf = QPushButton("Exportar a PDF")
        self.btn_export_excel = QPushButton("Exportar a Excel")
        self.btn_save_html = QPushButton("Guardar HTML")
        self.btn_close = QPushButton("Cerrar")
        row.addStretch(1)
        row.addWidget(self.btn_export_pdf)
        row.addWidget(self.btn_export_excel)
        row.addWidget(self.btn_save_html)
        row.addWidget(self.btn_close)
        v.addLayout(row)

        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        self.btn_export_excel.clicked.connect(self._on_export_excel)
        self.btn_save_html.clicked.connect(self._on_save_html)
        self.btn_close.clicked.connect(self.reject)

    def _load_html(self):
        try:
            if self.debug:
                q = dict(self.raw_quotation or {})
                if not q.get("client_name"):
                    txt, ok = QInputDialog.getText(self, "Cliente - Nombre", "Ingrese Nombre o Razón Social del cliente:", text="")
                    if ok and txt:
                        self.raw_quotation["client_name"] = txt.strip()
                if not q.get("client_rnc"):
                    txt2, ok2 = QInputDialog.getText(self, "Cliente - RNC/Cédula", "Ingrese RNC / Cédula del cliente:", text="")
                    if ok2 and txt2:
                        self.raw_quotation["client_rnc"] = txt2.strip()

            company, tpl, quotation = self._build_injectable_payloads()
            self._last_payload = {"COMPANY": company, "TEMPLATE": tpl, "QUOTATION": quotation}

            if build_html_with_json_block:
                html = build_html_with_json_block(self.template_path, company, tpl, quotation)
            else:
                html = _local_build_html_with_json_block(self.template_path, company, tpl, quotation)

            base = QUrl.fromLocalFile(os.path.abspath(os.path.dirname(self.template_path)) + os.sep)

            try:
                self.view.loadFinished.disconnect(self._on_loaded)
            except Exception:
                pass
            self.view.loadFinished.connect(self._on_loaded)

            self.view.setHtml(html, base)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la vista previa:\n{e}")

    def _on_loaded(self, ok: bool):
        if self.debug:
            print(f"[QuotationPreviewDialog] page.loadFinished ok={ok}")

        try:
            payload = self._last_payload or {"COMPANY": {}, "TEMPLATE": {}, "QUOTATION": {}}
            js_payload = json.dumps(payload, ensure_ascii=False).replace("</script>", "<\\/script>")

            assign_js = f"""
(function(){{
  try {{
    var payload = {js_payload};
    window.COMPANY = payload.COMPANY || {{}}; 
    window.TEMPLATE = payload.TEMPLATE || {{}}; 
    window.QUOTATION = payload.QUOTATION || payload.INVOICE || {{}}; 
    if (typeof renderAll === 'function') {{
      try {{ renderAll(); }} catch (e) {{ console.warn('renderAll error', e); }}
    }}
    return true;
  }} catch (e) {{
    console.error('[INJECT ERROR]', e);
    return false;
  }}
}})();
"""
            def after_assign(res):
                if self.debug:
                    print(f"[PREVIEW] assign_js ejecutado, resultado: {res}")

                fallback_js = r"""
(function(){
  try {
    var comp = window.COMPANY || {};
    var tpl  = window.TEMPLATE || {};
    var q    = window.QUOTATION || {};

    // Nombre empresa
    var nameNode = document.getElementById('company-name');
    if (nameNode) nameNode.textContent = (comp.name || '').toString().toUpperCase();

    // Meta
    var metaContainer = document.getElementById('company-meta-container');
    if (metaContainer) {
      var parts = [];
      if (comp.rnc) parts.push('RNC: ' + comp.rnc);
      var address = comp.address || comp.address_line1 || 'Dirección no especificada';
      parts.push(address);
      if (comp.phone) parts.push('Teléfono: ' + comp.phone);
      if (comp.email) parts.push('Email: ' + comp.email);
      metaContainer.innerHTML = parts.map(function(x){return '<div>'+x+'</div>';}).join('');
    }

    // Firma Autorizada
    var sigNode = document.getElementById('signature-name');
    if (sigNode) {
      var sig = comp.authorized_name || comp.signature_name || '';
      sigNode.textContent = (sig && String(sig).trim()) ? String(sig).toUpperCase() : 'NOMBRE AUTORIZADO';
    }

    // Items
    var tbody = document.getElementById('items-table-body');
    if (tbody) {
      var html = '';
      var subtotal = 0;
      (q.items || []).forEach(function(it, idx){
        var qty = Number(it.quantity) || 0;
        var up  = Number(it.unit_price) || 0;
        var line = qty * up; subtotal += line;
        var unit = (it.unit && String(it.unit).trim()) ? it.unit : 'UNID';
        html += '<tr>';
        html += '<td class="no">' + String(idx + 1).padStart(2, '0') + '</td>';
        html += '<td class="desc"><div class="code">' + (it.code || '') + '</div><div class="sub-text">' + (it.description || '') + '</div></td>';
        html += '<td class="unit">' + unit + '</td>';
        html += '<td class="unit-price">' + new Intl.NumberFormat("es-DO",{minimumFractionDigits:2,maximumFractionDigits:2}).format(up) + '</td>';
        var qfmt = (qty % 1 === 0) ? new Intl.NumberFormat("es-DO",{maximumFractionDigits:0}).format(qty) : new Intl.NumberFormat("es-DO",{minimumFractionDigits:2,maximumFractionDigits:2}).format(qty);
        html += '<td class="qty">' + qfmt + '</td>';
        html += '<td class="total">' + new Intl.NumberFormat("es-DO",{minimumFractionDigits:2,maximumFractionDigits:2}).format(line) + '</td>';
        html += '</tr>';
      });
      tbody.innerHTML = html;
    }
  } catch(e) {
    console.error('fallback renderer error', e);
  }
})();
"""
                self.view.page().runJavaScript(fallback_js)

            self.view.page().runJavaScript(assign_js, after_assign)

        except Exception as e:
            print(f"[PREVIEW] Error inyectando payload: {e}")

    def _on_save_html(self):
        try:
            company, tpl, quotation = self._build_injectable_payloads()

            if build_html_with_json_block:
                html = build_html_with_json_block(self.template_path, company, tpl, quotation)
            else:
                html = _local_build_html_with_json_block(self.template_path, company, tpl, quotation)

            fn, _ = QFileDialog.getSaveFileName(self, "Guardar HTML de Vista Previa", "quotation_preview.html", "HTML Files (*.html *.htm)")
            if not fn:
                return
            save_path = fn if fn.lower().endswith((".html", ".htm")) else fn + ".html"

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html)

            QMessageBox.information(self, "Guardar HTML", f"Archivo HTML guardado en:\n{save_path}")

            if QMessageBox.question(self, "Abrir archivo", "¿Deseas abrir el HTML en el navegador?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                try:
                    webbrowser.open(os.path.abspath(save_path))
                except Exception as e:
                    QMessageBox.warning(self, "Abrir HTML", f"No se pudo abrir el archivo en el navegador: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Guardar HTML", f"No se pudo generar/guardar el HTML:\n{e}")

    def _show_uploaded_link_actions(self, upload_url: str):
        try:
            if not upload_url:
                return
            from PyQt6.QtWidgets import QMessageBox
            import webbrowser
            from PyQt6.QtGui import QGuiApplication

            msg = QMessageBox(self)
            msg.setWindowTitle("PDF subido")
            msg.setText("El PDF fue subido correctamente. ¿Qué deseas hacer?")
            open_btn = msg.addButton("Abrir enlace", QMessageBox.ButtonRole.AcceptRole)
            copy_btn = msg.addButton("Copiar enlace", QMessageBox.ButtonRole.ActionRole)
            msg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked is open_btn:
                try:
                    webbrowser.open(upload_url)
                except Exception as e:
                    QMessageBox.warning(self, "Abrir enlace", f"No se pudo abrir el enlace:\n{e}")
            elif clicked is copy_btn:
                try:
                    QGuiApplication.clipboard().setText(upload_url)
                    QMessageBox.information(self, "Copiar enlace", "Enlace copiado al portapapeles.")
                except Exception as e:
                    QMessageBox.warning(self, "Copiar enlace", f"No se pudo copiar el enlace:\n{e}")
        except Exception as e:
            print(f"[QT-UPLOAD] Error mostrando popup enlace: {e}")

    def _on_export_pdf(self):
        import re
        from datetime import datetime, timedelta

        payload = getattr(self, "_last_payload", {}) or {}
        comp = (payload.get("COMPANY") or self.raw_company or {}) or {}
        q = (payload.get("QUOTATION") or self.raw_quotation or {}) or {}

        company_name = (comp.get("name") or "").strip() or "EMPRESA"
        display_number = (q.get("display_number") or q.get("number") or "").strip()
        if not display_number:
            letters = re.sub(r"[^A-Za-z]", "", (company_name.encode("ascii", "ignore").decode("ascii") if isinstance(company_name, str) else ""))
            prefix = (letters[:3] or "EMP").upper()
            try:
                qid = int(q.get("id") or 0)
            except Exception:
                qid = 0
            display_number = f"COT-{prefix}-{qid:06d}"

        base = f"COT_{display_number}_{company_name}"
        safe = re.sub(r"[^A-Za-z0-9._\\-]+", "_", base).strip("_")
        suggested = f"{safe}.pdf"

        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como PDF", suggested, "PDF Files (*.pdf)")
        if not fn:
            return

        save_path = fn if fn.lower().endswith(".pdf") else fn + ".pdf"
        try:
            self.btn_export_pdf.setEnabled(False)
        except Exception:
            pass
        print(f"[QT-EXPORT] Inicio export PDF. save_path={save_path}")

        def finish_with_message(ok: bool, msg: str = None):
            try:
                self.btn_export_pdf.setEnabled(True)
            except Exception:
                pass
            if ok:
                print(f"[QT-EXPORT] PDF generado correctamente: {save_path}")
                QMessageBox.information(self, "PDF", f"PDF generado:\n{save_path}")
            else:
                print(f"[QT-EXPORT] ERROR generando PDF: {msg}")
                QMessageBox.warning(self, "PDF", msg or "No se pudo generar el PDF o está vacío.")

        def try_request_bytes_fallback():
            try:
                wrote = False
                def cb_bytes(data):
                    nonlocal wrote
                    try:
                        bytes_data = bytes(data) if isinstance(data, QByteArray) else data
                        if isinstance(bytes_data, (bytes, bytearray)):
                            print(f"[QT-EXPORT] Fallback cb_bytes received length={len(bytes_data)}")
                            with open(save_path, "wb") as f:
                                f.write(bytes_data)
                            wrote = True
                        else:
                            print(f"[QT-EXPORT] Fallback cb_bytes unexpected type: {type(bytes_data)}")
                    except Exception as ex:
                        print(f"[QT-EXPORT] Error en cb_bytes: {ex}")
                try:
                    self.view.page().printToPdf(cb_bytes)
                except TypeError:
                    try:
                        self.view.page().printToPdf(save_path, cb_bytes)
                    except Exception as ex2:
                        print(f"[QT-EXPORT] Fallback printToPdf(save_path, cb_bytes) falló: {ex2}")
                return wrote
            except Exception as e:
                print(f"[QT-EXPORT] Fallback para obtener bytes falló: {e}")
                return False

        def on_pdf_result(result):
            print(f"[QT-EXPORT] on_pdf_result called. type(result)={type(result)}")
            upload_url = None
            file_written = False

            try:
                if isinstance(result, QByteArray):
                    data_bytes = bytes(result)
                    print(f"[QT-EXPORT] Received QByteArray length={len(data_bytes)}")
                    with open(save_path, "wb") as f:
                        f.write(data_bytes)
                    file_written = True
                    finish_with_message(True)
                elif isinstance(result, (bytes, bytearray)):
                    print(f"[QT-EXPORT] Received bytes-like length={len(result)}")
                    with open(save_path, "wb") as f:
                        f.write(result)
                    file_written = True
                    finish_with_message(True)
                elif isinstance(result, bool) or result is None:
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        size = os.path.getsize(save_path)
                        print(f"[QT-EXPORT] File exists after printToPdf: size={size}")
                        file_written = True
                        finish_with_message(True)
                    else:
                        print("[QT-EXPORT] No file found on disk after printToPdf; trying fallback bytes callback")
                        wrote = try_request_bytes_fallback()
                        if wrote:
                            file_written = True
                            finish_with_message(True)
                        else:
                            finish_with_message(False, "Fallback: no se pudo obtener bytes del render")
                            return
                else:
                    print(f"[QT-EXPORT] Resultado inesperado de printToPdf: {result} (type={type(result)})")
                    finish_with_message(False, "Resultado inesperado al generar PDF.")
                    return
            except Exception as e:
                print(f"[QT-EXPORT] Error processing printToPdf result: {e}")
                finish_with_message(False, f"Error al procesar PDF generado: {e}")
                return

            if not file_written:
                print("[QT-UPLOAD] No se escribió fichero local; abortando upload.")
                return

            try:
                safe_company = ''.join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_') or f"company_{comp.get('id','unknown')}"
                file_name = (q.get("quotation_number") or q.get("number") or display_number or f"DRAFT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}").strip()
                year = (q.get("date") or datetime.utcnow().strftime("%Y-%m-%d"))[:4]
                month = (q.get("date") or datetime.utcnow().strftime("%Y-%m-%d"))[5:7]
                storage_path = f"cotizacion/{safe_company}/{year}/{month}/{file_name}.pdf"
                print(f"[QT-UPLOAD] Intentando upload local={save_path} -> storage_path={storage_path}")

                logic = None
                try:
                    if hasattr(self.parent(), 'logic'):
                        logic = getattr(self.parent(), 'logic')
                except Exception:
                    logic = None

                da = None
                if logic is not None:
                    da = getattr(logic, "data_access", None) or logic
                else:
                    try:
                        from data_access.firebase_data_access import FirebaseDataAccess  # type: ignore
                        da = FirebaseDataAccess(user_id="system")
                    except Exception:
                        da = None

                try:
                    if logic and hasattr(logic, "upload_file_to_storage"):
                        upload_url = logic.upload_file_to_storage(save_path, storage_path)
                    elif da and hasattr(da, "upload_file_to_storage"):
                        upload_url = da.upload_file_to_storage(save_path, storage_path)
                    else:
                        print("[QT-UPLOAD] No se encontró upload_file_to_storage en logic/data_access")
                except Exception as ex_up:
                    print(f"[QT-UPLOAD] Excepción durante upload: {ex_up}")

                print(f"[QT-UPLOAD] upload_url -> {upload_url}")

                expires_at = ""
                if upload_url:
                    try:
                        days = int(getattr(facot_config, "PDF_SIGNED_URL_DAYS", 7) or 7)
                        days = min(days, 7)
                    except Exception:
                        days = 7
                    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
                else:
                    try:
                        storage_client = getattr(da, "storage", None)
                        if storage_client:
                            blob = storage_client.blob(storage_path)
                            try:
                                exists = blob.exists()
                            except Exception as exb:
                                exists = False
                                print(f"[QT-UPLOAD] blob.exists() error: {exb}")
                            print(f"[QT-UPLOAD] blob.exists() -> {exists} for {storage_path}")
                            if exists and hasattr(da, "generate_signed_url_for_path"):
                                try:
                                    upload_url = da.generate_signed_url_for_path(storage_path, days=7)
                                    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
                                    print(f"[QT-UPLOAD] Generated signed URL for existing blob: {upload_url}")
                                except Exception as ex_gen:
                                    print(f"[QT-UPLOAD] Error generating signed URL: {ex_gen}")
                    except Exception as e_check:
                        print(f"[QT-UPLOAD] Error comprobando blob: {e_check}")

                quotation_id = q.get("id") or None
                if quotation_id:
                    try:
                        if logic and hasattr(logic, "set_quotation_pdf_info"):
                            try:
                                logic.set_quotation_pdf_info(quotation_id, storage_path, upload_url, expires_at=expires_at)
                            except TypeError:
                                logic.set_quotation_pdf_info(quotation_id, storage_path, upload_url)
                        elif da and hasattr(da, "set_quotation_pdf_info"):
                            try:
                                da.set_quotation_pdf_info(quotation_id, storage_path, upload_url, expires_at=expires_at)
                            except TypeError:
                                da.set_quotation_pdf_info(quotation_id, storage_path, upload_url)
                        print(f"[QT-UPLOAD] set_quotation_pdf_info called for quotation_id={quotation_id}")
                    except Exception as ex_set:
                        print(f"[QT-UPLOAD] Error calling set_quotation_pdf_info: {ex_set}")
                else:
                    try:
                        parent = getattr(self, "parent", None) and self.parent()
                        if parent and hasattr(parent, "_preview_pdf_info_quotation"):
                            parent._preview_pdf_info_quotation = {"storage_path": storage_path, "url": upload_url, "company_id": comp.get("id"), "quotation_number": file_name, "expires_at": expires_at}
                            print("[QT-UPLOAD] Preview PDF info guardada en parent._preview_pdf_info_quotation")
                        else:
                            print("[QT-UPLOAD] NO quotation_id disponible. Debes guardar manualmente pdf_storage_path/pdf_url o implementar la asociación preview->quotation al guardar.")
                    except Exception as e_parent:
                        print(f"[QT-UPLOAD] Error guardando preview info en parent: {e_parent}")

                if upload_url:
                    try:
                        self._show_uploaded_link_actions(upload_url)
                    except Exception as e_popup:
                        print(f"[QT-UPLOAD] Error mostrando popup enlace: {e_popup}")

            except Exception as e_up_all:
                print(f"[QT-UPLOAD] Error general post-upload: {e_up_all}")

    def _on_print_dialog(self):
        try:
            def cb(_):
                QMessageBox.information(self, "Imprimir", "Se generó PDF temporal para imprimir.")
            try:
                self.view.page().printToPdf(cb)
            except TypeError:
                self.view.page().printToPdf("temp_print.pdf", cb)
        except Exception as e:
            QMessageBox.critical(self, "Imprimir", f"No se pudo iniciar la impresión:\n{e}")

    def _on_export_excel(self):
        try:
            payload = getattr(self, "_last_payload", {}) or {}
            comp = (payload.get("COMPANY") or self.raw_company or {}) or {}
            tpl = (payload.get("TEMPLATE") or self.raw_template or {}) or {}
            q = (payload.get("QUOTATION") or self.raw_quotation or {}) or {}

            company_name = (comp.get("name") or "EMPRESA").strip()

            display_number = (q.get("display_number") or q.get("number") or "").strip()
            if not display_number:
                letters = re.sub(r"[^A-Za-z]", "", (company_name.encode("ascii", "ignore").decode("ascii") if isinstance(company_name, str) else ""))
                prefix = (letters[:3] or "EMP").upper()
                try:
                    qid = int(q.get("id") or 0)
                except Exception:
                    qid = 0
                display_number = f"COT-{prefix}-{qid:06d}"

            base = f"COT_{display_number}_{company_name}"
            safe = re.sub(r"[^A-Za-z0-9._\\-]+", "_", base).strip("_")
            suggested = f"{safe}.xlsx"

            fn, _ = QFileDialog.getSaveFileName(self, "Guardar Cotización como Excel", suggested, "Excel Files (*.xlsx)")
            if not fn:
                return
            save_path = fn if fn.lower().endswith(".xlsx") else fn + ".xlsx"

            from utils.quotation_templates import generate_quotation_excel as gen_xlsx
            items_src = q.get("items") or []
            items = []
            subtotal = 0.0

            for it in items_src:
                code = (it.get("code") or it.get("item_code") or "").strip()
                desc = (it.get("description") or "").strip()
                unit = (it.get("unit") or "").strip()
                try:
                    qty = float(it.get("quantity") or 0.0)
                except Exception:
                    qty = 0.0
                try:
                    up = float(it.get("unit_price") or 0.0)
                except Exception:
                    up = 0.0

                subtotal += qty * up
                items.append({
                    "code": code,
                    "description": desc,
                    "unit": unit,
                    "quantity": qty,
                    "unit_price": up,
                })

            itbis_rate = float(tpl.get("itbis_rate", 0.18) or 0.0)
            apply_itbis = q.get("apply_itbis")
            if apply_itbis is None:
                apply_itbis = itbis_rate > 0
            itbis_val = subtotal * itbis_rate if apply_itbis else 0.0
            total_amount = subtotal + itbis_val

            logo_local = (comp.get("logo_path") or "").strip()
            data = {
                "company_id": comp.get("id"),
                "quotation_date": q.get("date") or q.get("quotation_date"),
                "client_name": q.get("client_name") or q.get("third_party_name") or "",
                "client_rnc": q.get("client_rnc") or q.get("rnc") or "",
                "notes": q.get("notes") or "",
                "currency": q.get("currency") or "RD$",
                "total_amount": total_amount,
                "itbis_rate": itbis_rate,
                "apply_itbis": bool(apply_itbis),
                "logo_path": logo_local,
                "excel_path": "",
                "pdf_path": "",
            }

            gen_xlsx(data, items, save_path, company_name)
            QMessageBox.information(self, "Excel", f"Archivo Excel generado:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "Excel", f"No se pudo generar el Excel:\n{e}")

    def _compute_quotation_due_date_if_missing(self, quotation: Dict[str, Any]) -> None:
        if not isinstance(quotation, dict):
            return

        if quotation.get("due_date"):
            return

        base = (quotation.get("date")
                or quotation.get("quotation_date")
                or quotation.get("created_at")
                or "").strip()
        if not base:
            return

        try:
            d = datetime.strptime(base[:10], "%Y-%m-%d")
        except Exception:
            try:
                d = datetime.fromisoformat(base[:10])
            except Exception:
                return

        quotation["due_date"] = (d + timedelta(days=30)).strftime("%Y-%m-%d")

    def _build_injectable_payloads(self):
        logic_ctrl = None
        try:
            if hasattr(self.parent(), 'logic'):
                logic_ctrl = self.parent().logic
        except Exception:
            pass

        company = _prepare_company_data_for_preview(self.raw_company, self.raw_template, logic_controller=logic_ctrl)
        tpl = dict(self.raw_template or {})
        quotation = dict(self.raw_quotation or {})

        tpl["itbis_rate"] = tpl.get("itbis_rate", 0.18)

        quotation["items"] = quotation.get("items", [])

        if quotation.get("apply_itbis") is None:
            quotation["apply_itbis"] = True

        try:
            subtotal = float(quotation.get("subtotal") or 0.0)
        except Exception:
            subtotal = 0.0
        if subtotal <= 0:
            for it in quotation.get("items", []):
                try:
                    subtotal += float(it.get("quantity", 0)) * float(it.get("unit_price", 0))
                except Exception:
                    pass
        try:
            itbis_rate = float(tpl.get("itbis_rate", 0.18) or 0.0)
        except Exception:
            itbis_rate = 0.18

        apply_itbis = bool(quotation.get("apply_itbis"))
        itbis_val = round(subtotal * itbis_rate, 2) if apply_itbis else 0.0
        total_amount = round(subtotal + itbis_val, 2)

        quotation["subtotal"] = round(subtotal, 2)
        quotation["itbis"] = round(itbis_val, 2)
        quotation["total_amount"] = round(total_amount, 2)

        if company.get("logo_path"):
            if tpl.get("show_logo") is False:
                print("[QT-LOGO] tpl.show_logo estaba False, se fuerza a True porque hay logo_path.")
            tpl["show_logo"] = True

        _ensure_units(quotation, logic_controller=logic_ctrl)

        try:
            if not quotation.get("due_date") and company.get("invoice_due_date"):
                quotation["due_date"] = company.get("invoice_due_date")
                print(f"[QT-BUILD] Applied company.invoice_due_date -> quotation.due_date = {quotation['due_date']}")
        except Exception:
            pass

        return company, tpl, quotation