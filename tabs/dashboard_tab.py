"""
DashboardTab - Modern dashboard view with summary cards and analytics.

Replicates the React/Tailwind design:
- 4 summary cards (Ingresos, Facturas Pendientes, etc.)
- Functional chart showing monthly sales
- Recent activity list

Data Filtering: ONLY counts invoices where type is "emitida" (Issued) or in INGRESO_TYPES.
Explicitly excludes "gasto" (Expense) type invoices.
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from constants import INGRESO_TYPES, EXPENSE_TYPES

# Try to import pyqtgraph for charts
try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False
    print("[DASHBOARD] pyqtgraph not available - using placeholder chart")


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


class SalesChart(QFrame):
    """
    Chart widget showing sales per month using pyqtgraph.
    Displays monthly revenue data for the current year.
    
    Data filtering: Only includes invoices with type in INGRESO_TYPES.
    """
    
    def __init__(self, title: str = "Resumen de Ingresos", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("SalesChart")
        self._setup_ui(title)
    
    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #1e293b; font-size: 16px; font-weight: 600;")
        layout.addWidget(title_label)
        
        # Chart widget
        if HAS_PYQTGRAPH:
            # Configure pyqtgraph
            pg.setConfigOptions(antialias=True)
            
            # Create plot widget
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground('w')
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Style the plot
            self.plot_widget.setLabel('left', 'Ingresos', units='$')
            self.plot_widget.setLabel('bottom', 'Mes')
            
            # Configure axes
            current_year = datetime.now().year
            ax = self.plot_widget.getAxis('bottom')
            ax.setTicks([[(i, datetime(current_year, i, 1).strftime('%b')) for i in range(1, 13)]])
            
            layout.addWidget(self.plot_widget, 1)
        else:
            # Fallback to placeholder
            placeholder = QLabel("📊 Instalar pyqtgraph para visualizar gráficos\n\npip install pyqtgraph")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 40px;")
            layout.addWidget(placeholder, 1)
            self.plot_widget = None
        
        self.setStyleSheet("""
            QFrame#SalesChart {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(256)
    
    def update_chart(self, monthly_data: Dict[int, float]):
        """
        Update chart with monthly sales data.
        
        Args:
            monthly_data: Dictionary mapping month (1-12) to total sales
        """
        if not HAS_PYQTGRAPH or not self.plot_widget:
            return
        
        # Clear existing plots
        self.plot_widget.clear()
        
        # Prepare data
        months = list(range(1, 13))
        sales = [monthly_data.get(m, 0.0) for m in months]
        
        # Create bar chart
        bargraph = pg.BarGraphItem(
            x=months,
            height=sales,
            width=0.6,
            brush='#4f46e5',  # indigo-600
            pen='#4338ca'     # indigo-700
        )
        self.plot_widget.addItem(bargraph)
        
        # Set reasonable y-axis range
        max_sale = max(sales) if sales else 0
        if max_sale > 0:
            # If there's any non-zero data, scale to show it nicely
            self.plot_widget.setYRange(0, max_sale * 1.1)
        else:
            # All sales are zero or no data - use a modest default range
            # 100 is more appropriate than 1000 for a clean empty chart
            self.plot_widget.setYRange(0, 100)
        self.plot_widget.setXRange(0, 13)


class ChartPlaceholder(QFrame):
    """
    Placeholder widget for chart area (legacy - use SalesChart instead).
    """
    
    def __init__(self, title: str = "Chart", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ChartPlaceholder")
        self._setup_ui(title)
    
    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #1e293b; font-size: 16px; font-weight: 600;")
        layout.addWidget(title_label)
        
        # Placeholder content
        placeholder = QLabel("📊 Chart visualization coming soon...")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 40px;")
        layout.addWidget(placeholder, 1)
        
        self.setStyleSheet("""
            QFrame#ChartPlaceholder {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(256)


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
        
        # Placeholder items
        self._add_placeholder_items()
        
        layout.addStretch()
        
        self.setStyleSheet("""
            QFrame#ActivityList {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(256)
    
    def _add_placeholder_items(self):
        """Add placeholder activity items."""
        items = [
            ("📄", "Nueva factura creada", "Hace 5 minutos"),
            ("📝", "Cotización enviada", "Hace 1 hora"),
            ("✅", "Pago recibido", "Hace 2 horas"),
            ("👤", "Nuevo cliente", "Ayer"),
        ]
        
        for icon, text, time in items:
            item_widget = self._create_activity_item(icon, text, time)
            self.items_layout.addWidget(item_widget)
    
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
        
        # Chart area (2/3 width) - Use SalesChart instead of placeholder
        self.chart = SalesChart("Resumen de Ingresos")
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
    
    def _load_data(self):
        """
        Load dashboard data from the database.
        
        STRICT CLIENT-SIDE FILTERING:
        - Stream ALL documents from invoices collection
        - Filter locally: ONLY count where invoice_type.lower() == 'emitida'
        - Ignore: GASTO or COMPRA records
        """
        if not self.logic or not self.get_current_company:
            return
        
        try:
            company = self.get_current_company()
            if not company:
                return
            
            company_id = company.get('id')
            
            # Load invoice totals with STRICT CLIENT-SIDE FILTERING
            if hasattr(self.logic, 'get_facturas'):
                # Stream ALL invoices from Firestore
                all_facturas = self.logic.get_facturas(company_id) or []
                
                # STRICT FILTERING: Only invoice_type.lower() == 'emitida'
                # Ignore GASTO, COMPRA, or any other type
                income_invoices = []
                for f in all_facturas:
                    inv_type = str(f.get('invoice_type') or f.get('type') or '').strip().lower()
                    if inv_type == 'emitida':
                        income_invoices.append(f)
                
                print(f"[Dashboard] Filtered {len(income_invoices)} 'emitida' invoices from {len(all_facturas)} total")
                
                # Total income (only from 'emitida' invoices)
                total_ingresos = sum(
                    float(f.get('total_amount', 0) or 0)
                    for f in income_invoices
                )
                self.card_ingresos.set_value(f"${total_ingresos:,.2f}")
                
                # Pending invoices (only 'emitida' invoices)
                pending_total = sum(
                    float(f.get('total_amount', 0) or 0)
                    for f in income_invoices
                    if f.get('status', '').lower() != 'paid'
                )
                self.card_pendientes.set_value(f"${pending_total:,.2f}")
                
                # Calculate monthly data for chart (current year only, 'emitida' only)
                self._update_chart_data(income_invoices)
            
            # Load quotation count
            if hasattr(self.logic, 'get_quotations'):
                cotizaciones = self.logic.get_quotations(company_id) or []
                self.card_cotizaciones.set_value(str(len(cotizaciones)))
            
            # Client count (simplified)
            if hasattr(self.logic, 'get_third_parties'):
                clients = self.logic.get_third_parties(company_id) or []
                self.card_clientes.set_value(str(len(clients)))
            elif hasattr(self.logic, 'search_third_parties'):
                # Fallback: show N/A when method not available
                self.card_clientes.set_value("N/A")
                
        except Exception as e:
            print(f"[DashboardTab] Error loading invoice data: {e}")
    
    def _update_chart_data(self, invoices: List[Dict[str, Any]]):
        """
        Update chart with monthly sales data from invoices.
        
        Args:
            invoices: List of income invoices (already filtered)
        """
        # Get current year
        current_year = datetime.now().year
        
        # Initialize monthly totals
        monthly_totals = {month: 0.0 for month in range(1, 13)}
        
        # Aggregate by month
        for invoice in invoices:
            try:
                # Try to parse invoice date
                invoice_date_str = invoice.get('invoice_date') or invoice.get('date')
                if not invoice_date_str:
                    continue
                
                # Parse date (handle multiple formats)
                if isinstance(invoice_date_str, str):
                    # Try ISO format first
                    try:
                        invoice_date = datetime.fromisoformat(invoice_date_str.replace('Z', '+00:00'))
                    except ValueError:
                        # Try common date formats
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                            try:
                                invoice_date = datetime.strptime(invoice_date_str, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            continue
                elif isinstance(invoice_date_str, (datetime, date)):
                    invoice_date = invoice_date_str
                else:
                    continue
                
                # Only count current year
                if invoice_date.year == current_year:
                    month = invoice_date.month
                    amount = float(invoice.get('total_amount', 0) or 0)
                    monthly_totals[month] += amount
            
            except Exception as e:
                print(f"[DashboardTab] Error processing invoice date: {e}")
                continue
        
        # Update chart
        if hasattr(self.chart, 'update_chart'):
            self.chart.update_chart(monthly_totals)
    
    def refresh(self):
        """Refresh dashboard data."""
        self._load_data()
    
    def on_company_change(self):
        """Handle company selection change."""
        self._load_data()
