"""
DashboardTab - Modern dashboard view with summary cards and analytics.

Replicates the React/Tailwind design:
- 4 summary cards (Ingresos, Facturas Pendientes, etc.)
- Chart area with pyqtgraph
- Recent activity list

BUSINESS LOGIC:
- STRICT filtering: Only count invoices where type is "emitida" or in INGRESO_TYPES
- EXCLUDE any records marked as "gasto" (expense)
- Revenue calculations must NEVER include expenses
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta
from calendar import month_name
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Import pyqtgraph for charting
try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    print("[DashboardTab] Warning: pyqtgraph not available, charts disabled")

# Import INGRESO_TYPES for strict revenue filtering
# These are the ONLY invoice types that count as revenue
INVOICE_TYPE_INGRESOS: Set[str] = {
    "INGRESO",
    "FACTURA",
    "FACTURA PRIVADA",
    "EMITIDA",
    "VENTA",
    "CREDITO FISCAL",
    "CONSUMIDOR FINAL",
    "GUBERNAMENTAL",
    "REGIMEN ESPECIAL",
    "EXPORTACION",
}

# Prefixes from NCF that correspond to income invoices
NCF_PREFIX_INGRESOS: Set[str] = {
    "B01",  # Crédito Fiscal
    "B02",  # Consumidor Final
    "B14",  # Régimen Especial
    "B15",  # Gubernamental
    "B16",  # Exportación
}

# Combined set for filtering
INGRESO_TYPES: Set[str] = INVOICE_TYPE_INGRESOS | NCF_PREFIX_INGRESOS


class DashboardCard(QFrame):
    """
    A styled card widget for displaying summary information.
    Replicates the Tailwind Card component with rounded corners and shadow.
    """
    
    def __init__(
        self,
        title: str,
        value: str,
        icon: str = "",
        subtitle: str = "",
        color: str = "#4f46e5",  # indigo-600
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("DashboardCard")
        self._setup_ui(title, value, icon, subtitle, color)
        self._apply_styles()
    
    def _setup_ui(self, title: str, value: str, icon: str, subtitle: str, color: str):
        """Build the card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        # Header row with icon
        header = QHBoxLayout()
        
        # Title (muted text)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.title_label.setStyleSheet(f"color: #64748b; font-size: 13px; font-weight: 500;")
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        # Icon (optional)
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"color: {color}; font-size: 24px;")
            header.addWidget(icon_label)
        
        layout.addLayout(header)
        
        # Value (large bold text)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.value_label.setFont(font)
        self.value_label.setStyleSheet("color: #1e293b;")
        layout.addWidget(self.value_label)
        
        # Subtitle (optional)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
            layout.addWidget(subtitle_label)
        
        layout.addStretch()
    
    def _apply_styles(self):
        """Apply card styling."""
        self.setStyleSheet("""
            DashboardCard, QFrame#DashboardCard {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    
    def set_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)


class IncomeChart(QFrame):
    """
    Revenue/Income chart widget using pyqtgraph.
    Shows monthly sales data for the current year.
    
    CRITICAL: Only displays data from INGRESO_TYPES (revenue), NO expenses.
    """
    
    def __init__(self, title: str = "Chart", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("IncomeChart")
        self.title = title
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #1e293b; font-size: 16px; font-weight: 600;")
        layout.addWidget(title_label)
        
        if PYQTGRAPH_AVAILABLE:
            # Create plot widget
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground('w')
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setLabel('left', 'Ingresos', units='$')
            self.plot_widget.setLabel('bottom', 'Mes')
            
            # Style the plot
            self.plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#94a3b8', width=1))
            self.plot_widget.getAxis('left').setPen(pg.mkPen(color='#94a3b8', width=1))
            self.plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#64748b'))
            self.plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#64748b'))
            
            layout.addWidget(self.plot_widget, 1)
        else:
            # Fallback if pyqtgraph not available
            placeholder = QLabel("📊 Instale pyqtgraph para visualizar gráficos\n\npip install pyqtgraph")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 40px;")
            layout.addWidget(placeholder, 1)
        
        self.setStyleSheet("""
            QFrame#IncomeChart {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(256)
    
    def update_data(self, monthly_data: List[Tuple[str, float]]):
        """
        Update chart with monthly income data.
        
        Args:
            monthly_data: List of (month_name, total_amount) tuples
        """
        if not PYQTGRAPH_AVAILABLE:
            return
        
        # Clear previous data
        self.plot_widget.clear()
        
        if not monthly_data:
            return
        
        # Extract months and values
        months = [item[0] for item in monthly_data]
        values = [item[1] for item in monthly_data]
        
        # Create x-axis positions
        x = list(range(len(months)))
        
        # Create bar graph
        bar_graph = pg.BarGraphItem(
            x=x,
            height=values,
            width=0.6,
            brush=pg.mkBrush('#4f46e5'),  # indigo-600
            pen=pg.mkPen(color='#4f46e5', width=1)
        )
        self.plot_widget.addItem(bar_graph)
        
        # Set x-axis ticks
        axis = self.plot_widget.getAxis('bottom')
        ticks = [(i, month) for i, month in enumerate(months)]
        axis.setTicks([ticks])
        
        # Set y-axis range with some padding
        if max(values) > 0:
            self.plot_widget.setYRange(0, max(values) * 1.1)


class ActivityList(QFrame):
    """
    Recent activity list widget.
    Shows recent invoices, quotations, etc.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ActivityList")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Title
        title_label = QLabel("Actividad Reciente")
        title_label.setStyleSheet("color: #1e293b; font-size: 16px; font-weight: 600;")
        layout.addWidget(title_label)
        
        # Activity items container
        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(8)
        layout.addLayout(self.items_layout)
        
        layout.addStretch()
        
        self.setStyleSheet("""
            QFrame#ActivityList {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(256)
    
    def clear_items(self):
        """Clear all activity items."""
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def set_activities(self, activities: List[Dict[str, Any]]):
        """
        Set activity items from a list of activity dictionaries.
        
        Args:
            activities: List of dicts with 'icon', 'text', 'time' keys
        """
        self.clear_items()
        
        for activity in activities[:10]:  # Limit to 10 items
            icon = activity.get('icon', '📄')
            text = activity.get('text', 'Activity')
            time = activity.get('time', '')
            
            item_widget = self._create_activity_item(icon, text, time)
            self.items_layout.addWidget(item_widget)
        
        # Add placeholder if no activities
        if not activities:
            placeholder = QLabel("No hay actividad reciente")
            placeholder.setStyleSheet("color: #94a3b8; font-size: 13px; padding: 20px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_layout.addWidget(placeholder)
    
    def _create_activity_item(self, icon: str, text: str, time: str) -> QWidget:
        """Create a single activity item widget."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")
        icon_label.setFixedWidth(24)
        layout.addWidget(icon_label)
        
        # Text
        text_label = QLabel(text)
        text_label.setStyleSheet("color: #334155; font-size: 13px;")
        layout.addWidget(text_label, 1)
        
        # Time
        time_label = QLabel(time)
        time_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(time_label)
        
        widget.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                border-radius: 8px;
            }
            QWidget:hover {
                background-color: #f1f5f9;
            }
        """)
        
        return widget
    
    def add_activity(self, icon: str, text: str, time: str):
        """Add a new activity item to the list."""
        item = self._create_activity_item(icon, text, time)
        self.items_layout.insertWidget(0, item)
        
        # Keep only last 10 items
        while self.items_layout.count() > 10:
            item = self.items_layout.takeAt(self.items_layout.count() - 1)
            if item.widget():
                item.widget().deleteLater()


class DashboardTab(QWidget):
    """
    Main dashboard tab with summary cards and analytics.
    
    Layout:
    - Row 1: 4 summary cards (grid)
    - Row 2: Chart area + Activity list (2:1 ratio)
    
    BUSINESS LOGIC:
    - STRICT revenue filtering: Only invoices in INGRESO_TYPES
    - EXCLUDE all "gasto" (expense) invoices
    - Chart shows monthly income for current year
    """
    
    def __init__(self, logic=None, get_current_company_callable=None, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.get_current_company = get_current_company_callable
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Build the dashboard UI."""
        # Scroll area for dashboard content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        # Content widget
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)
        
        # Summary cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        
        self.card_ingresos = DashboardCard(
            title="Ingresos Totales",
            value="$0.00",
            icon="💰",
            subtitle="Este mes",
            color="#22c55e"
        )
        cards_layout.addWidget(self.card_ingresos)
        
        self.card_pendientes = DashboardCard(
            title="Facturas Pendientes",
            value="$0.00",
            icon="📋",
            subtitle="Por cobrar",
            color="#f59e0b"
        )
        cards_layout.addWidget(self.card_pendientes)
        
        self.card_cotizaciones = DashboardCard(
            title="Cotizaciones",
            value="0",
            icon="📝",
            subtitle="Este mes",
            color="#4f46e5"
        )
        cards_layout.addWidget(self.card_cotizaciones)
        
        self.card_clientes = DashboardCard(
            title="Clientes Activos",
            value="0",
            icon="👥",
            subtitle="Total",
            color="#06b6d4"
        )
        cards_layout.addWidget(self.card_clientes)
        
        layout.addLayout(cards_layout)
        
        # Chart and Activity row
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(24)
        
        # Chart area (2/3 width)
        self.chart = IncomeChart("Resumen de Ingresos")
        bottom_layout.addWidget(self.chart, 2)
        
        # Activity list (1/3 width)
        self.activity_list = ActivityList()
        bottom_layout.addWidget(self.activity_list, 1)
        
        layout.addLayout(bottom_layout)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _is_revenue_invoice(self, invoice: Dict[str, Any]) -> bool:
        """
        CRITICAL: Determine if an invoice is revenue (not expense).
        
        Returns True ONLY if:
        1. invoice_type is "emitida" (case-insensitive), OR
        2. invoice_type is in INGRESO_TYPES, OR
        3. NCF prefix (first 3 chars) is in INGRESO_TYPES
        
        EXPLICITLY EXCLUDES:
        - Any invoice with type "gasto" or "GASTO"
        - Any invoice not matching the above criteria
        
        Args:
            invoice: Invoice dictionary
            
        Returns:
            True if invoice is revenue, False otherwise
        """
        # Get invoice type and NCF
        invoice_type = invoice.get('invoice_type', '').strip()
        invoice_category = invoice.get('invoice_category', '').strip()
        invoice_number = invoice.get('invoice_number', '').strip()
        
        # EXPLICIT EXCLUSION: Reject any "gasto" (expense)
        if invoice_type.upper() == 'GASTO' or invoice_category.upper() == 'GASTO':
            return False
        
        # CHECK 1: Is type "emitida"?
        if invoice_type.upper() == 'EMITIDA':
            return True
        
        # CHECK 2: Is type in INGRESO_TYPES?
        if invoice_type.upper() in INGRESO_TYPES:
            return True
        
        # CHECK 3: Is NCF prefix in INGRESO_TYPES?
        if len(invoice_number) >= 3:
            ncf_prefix = invoice_number[:3].upper()
            if ncf_prefix in INGRESO_TYPES:
                return True
        
        # Default: Not a revenue invoice
        return False
    
    def _load_data(self):
        """
        Load dashboard data from the database.
        
        CRITICAL: Apply strict revenue filtering - NO expenses allowed.
        """
        if not self.logic or not self.get_current_company:
            return
        
        try:
            company = self.get_current_company()
            if not company:
                return
            
            company_id = company.get('id')
            current_date = datetime.now()
            current_year = current_date.year
            current_month = current_date.month
            
            # Get all invoices (we'll filter ourselves)
            if hasattr(self.logic, 'get_facturas'):
                # Get ALL invoices (not just issued) so we can apply our own filtering
                all_invoices = self.logic.get_facturas(company_id, only_issued=False) or []
                
                # STRICT FILTERING: Only revenue invoices
                revenue_invoices = [inv for inv in all_invoices if self._is_revenue_invoice(inv)]
                
                # Calculate total revenue (ALL TIME)
                total_ingresos = sum(
                    float(inv.get('total_amount', 0) or 0)
                    for inv in revenue_invoices
                )
                self.card_ingresos.set_value(f"${total_ingresos:,.2f}")
                
                # Pending invoices (revenue only, unpaid)
                pending_total = sum(
                    float(inv.get('total_amount', 0) or 0)
                    for inv in revenue_invoices
                    if inv.get('status', '').lower() != 'paid'
                )
                self.card_pendientes.set_value(f"${pending_total:,.2f}")
                
                # Update chart with monthly data (revenue only)
                self._update_chart(revenue_invoices, current_year)
                
                # Update activity list with recent revenue invoices
                self._update_activity_list(revenue_invoices)
            
            # Load quotation count
            if hasattr(self.logic, 'get_quotations'):
                # Filter quotations for current month
                cotizaciones = self.logic.get_quotations(company_id) or []
                current_month_quotations = [
                    q for q in cotizaciones
                    if self._is_current_month(q.get('quotation_date', ''), current_year, current_month)
                ]
                self.card_cotizaciones.set_value(str(len(current_month_quotations)))
            
            # Client count (simplified)
            if hasattr(self.logic, 'get_third_parties'):
                clients = self.logic.get_third_parties(company_id) or []
                self.card_clientes.set_value(str(len(clients)))
            elif hasattr(self.logic, 'search_third_parties'):
                # Fallback: show N/A when method not available
                self.card_clientes.set_value("N/A")
                
        except Exception as e:
            print(f"[DashboardTab] Error loading data: {e}")
            import traceback
            traceback.print_exc()
    
    def _is_current_month(self, date_str: str, year: int, month: int) -> bool:
        """Check if a date string is in the current month/year."""
        if not date_str:
            return False
        try:
            date_obj = datetime.fromisoformat(date_str.replace(' ', 'T'))
            return date_obj.year == year and date_obj.month == month
        except:
            return False
    
    def _update_chart(self, invoices: List[Dict[str, Any]], year: int):
        """
        Update the income chart with monthly data.
        
        Args:
            invoices: List of REVENUE invoices (already filtered)
            year: Year to display
        """
        # Initialize monthly totals
        monthly_totals = {i: 0.0 for i in range(1, 13)}
        
        # Aggregate invoices by month
        for inv in invoices:
            date_str = inv.get('invoice_date', '')
            if not date_str:
                continue
            
            try:
                # Parse date
                date_obj = datetime.fromisoformat(date_str.replace(' ', 'T'))
                
                # Only count current year
                if date_obj.year == year:
                    month_num = date_obj.month
                    amount = float(inv.get('total_amount', 0) or 0)
                    monthly_totals[month_num] += amount
            except Exception as e:
                print(f"[DashboardTab] Error parsing date '{date_str}': {e}")
                continue
        
        # Prepare data for chart (month names + values)
        month_names_es = [
            'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
            'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
        ]
        
        chart_data = [
            (month_names_es[i-1], monthly_totals[i])
            for i in range(1, 13)
        ]
        
        # Update chart
        self.chart.update_data(chart_data)
    
    def _update_activity_list(self, invoices: List[Dict[str, Any]]):
        """
        Update activity list with recent invoices.
        
        Args:
            invoices: List of REVENUE invoices (already filtered)
        """
        # Sort by date (most recent first)
        sorted_invoices = sorted(
            invoices,
            key=lambda x: x.get('invoice_date', ''),
            reverse=True
        )
        
        # Create activity items
        activities = []
        for inv in sorted_invoices[:10]:  # Top 10
            date_str = inv.get('invoice_date', '')
            invoice_num = inv.get('invoice_number', 'N/A')
            client = inv.get('client_name', inv.get('third_party_name', 'Cliente'))
            amount = float(inv.get('total_amount', 0) or 0)
            
            # Format relative time
            time_ago = self._format_time_ago(date_str)
            
            activities.append({
                'icon': '📄',
                'text': f"Factura {invoice_num[:15]} - ${amount:,.0f}",
                'time': time_ago
            })
        
        self.activity_list.set_activities(activities)
    
    def _format_time_ago(self, date_str: str) -> str:
        """Format a date as relative time (e.g., '2 días')."""
        if not date_str:
            return ''
        
        try:
            date_obj = datetime.fromisoformat(date_str.replace(' ', 'T'))
            now = datetime.now()
            delta = now - date_obj
            
            if delta.days == 0:
                if delta.seconds < 3600:
                    mins = delta.seconds // 60
                    return f"Hace {mins} min" if mins > 0 else "Ahora"
                else:
                    hours = delta.seconds // 3600
                    return f"Hace {hours}h"
            elif delta.days == 1:
                return "Ayer"
            elif delta.days < 7:
                return f"Hace {delta.days} días"
            elif delta.days < 30:
                weeks = delta.days // 7
                return f"Hace {weeks} sem"
            elif delta.days < 365:
                months = delta.days // 30
                return f"Hace {months} mes" if months == 1 else f"Hace {months} meses"
            else:
                years = delta.days // 365
                return f"Hace {years} año" if years == 1 else f"Hace {years} años"
        except:
            return ''
    
    def refresh(self):
        """Refresh dashboard data."""
        self._load_data()
    
    def on_company_change(self):
        """Handle company selection change."""
        self._load_data()
