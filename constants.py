# Constantes compartidas
NCF_TYPES = {
    "Crédito Fiscal (B01)": "B01",
    "Consumidor Final (B02)": "B02",
    "Gubernamental (B15)": "B15",
    "Régimen Especial (B14)": "B14",
    "Nota de Crédito (B04)": "B04",
}
ITBIS_RATE = 0.18
DEFAULT_CURRENCY = "RD$"

# Invoice Types
# INGRESO_TYPES: Types that represent income/revenue (to be included in revenue calculations)
# Exclude "gasto" (expenses) from revenue totals
INGRESO_TYPES = ["emitida"]  # Issued invoices are income
EXPENSE_TYPES = ["gasto"]  # Expense invoices should be excluded from revenue