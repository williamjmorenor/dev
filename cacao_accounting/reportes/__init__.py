# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Reportes operativos de subledgers, aging, Kardex y reconciliaciones."""

from __future__ import annotations

import csv
from dataclasses import replace
from datetime import date
from decimal import Decimal
from decimal import DecimalException
from io import BytesIO, StringIO

from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from openpyxl import Workbook

from cacao_accounting.decorators import modulo_activo
from cacao_accounting.reportes.services import (
    AgingFilters,
    FinancialReportFilters,
    KardexFilters,
    OperationalReportFilters,
    SubledgerFilters,
    get_account_movement_detail,
    get_aging_report,
    get_ar_ap_subledger,
    get_batch_report,
    get_balance_sheet_report,
    get_gross_margin,
    get_income_statement_report,
    get_inventory_valuation,
    get_kardex,
    get_purchases_by_item,
    get_purchases_by_supplier,
    get_reconciliation_report,
    get_sales_by_customer,
    get_sales_by_item,
    get_serial_report,
    get_stock_balance,
    get_trial_balance_report,
)
from cacao_accounting.version import APPNAME

try:  # pragma: no cover - fallback defensivo para contextos sin Flask-Babel inicializado.
    from flask_babel import gettext as _babel_gettext
except ImportError:  # pragma: no cover

    def _(value: str) -> str:
        return value

else:

    def _(value: str) -> str:
        try:
            return _babel_gettext(value)
        except (KeyError, RuntimeError):
            return value


reportes = Blueprint("reportes", __name__, template_folder="templates")

_COLUMN_LABELS = {
    "posting_date": "Posting Date",
    "accounting_period": "Period",
    "document_no": "Voucher",
    "voucher_type": "Type",
    "account_code": "Account",
    "account_name": "Account Name",
    "debit": "Debit",
    "credit": "Credit",
    "running_balance": "Final Balance",
    "currency": "Currency",
    "ledger": "Ledger",
    "company": "Company",
    "opening_balance": "Opening Balance",
    "ending_balance": "Final Balance",
    "cost_center": "Cost Center",
    "unit": "Unit",
    "project": "Project",
    "party_type": "Party Type",
    "party_id": "Party",
    "created_by": "User",
    "created_at": "Creation Date",
    "line_comment": "Reference",
    "voucher_status": "Status",
    "section": "Section",
    "amount": "Amount",
}
_MONEY_COLUMNS = {
    "debit",
    "credit",
    "difference",
    "opening_balance",
    "ending_balance",
    "running_balance",
    "amount",
    "assets",
    "liabilities",
    "equity",
    "period_profit",
    "income",
    "cost",
    "expense",
    "gross_profit",
    "net_profit",
}
_RIGHT_ALIGN_COLUMNS = _MONEY_COLUMNS | {"level"}
_ALWAYS_VISIBLE_COLUMNS = {"debit", "credit", "difference", "account_code", "account_name", "section", "amount"}
_EMPTY_CELL_VALUE = "—"


def _format_number(value: object) -> str:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except DecimalException:
        return _EMPTY_CELL_VALUE
    formatted = f"{abs(amount):,.2f}"
    return f"({formatted})" if amount < 0 else formatted


def _column_label(column: str, ledger_currency: str | None) -> str:
    label = _(_COLUMN_LABELS.get(column, column.replace("_", " ").title()))
    if column in _MONEY_COLUMNS and ledger_currency:
        return f"{label} ({ledger_currency})"
    return label


def _format_cell(column: str, value: object, ledger_currency: str | None) -> str:
    if value is None or value == "":
        return _EMPTY_CELL_VALUE
    if column in _MONEY_COLUMNS:
        return _format_number(value)
    if column == "posting_date" and isinstance(value, date):
        return value.isoformat()
    if column == "voucher_status":
        return _("Cancelado") if str(value).lower() == "cancelled" else _("Contabilizado")
    if column == "section":
        section_labels = {
            "assets": _("ACTIVOS"),
            "liabilities": _("PASIVOS"),
            "equity": _("PATRIMONIO"),
            "income": _("INGRESOS"),
            "cost": _("COSTOS"),
            "expense": _("GASTOS"),
            "gross_profit": _("UTILIDAD BRUTA"),
            "net_profit": _("UTILIDAD NETA"),
        }
        return section_labels.get(str(value), str(value))
    return str(value)


def _build_context_summary(report, report_filters: FinancialReportFilters) -> dict[str, str]:
    ledger_label = report_filters.ledger or "—"
    if report_filters.ledger and report.ledger_currency:
        ledger_label = f"{report_filters.ledger} ({report.ledger_currency})"
    status_value = report_filters.status or "submitted"
    status_label = _("Cancelado") if status_value == "cancelled" else _("Contabilizado")
    return {
        "company": report_filters.company,
        "ledger": ledger_label,
        "period": report_filters.accounting_period or "—",
        "status": status_label,
        "records": str(report.total_rows),
    }


def _is_report_balanced(raw_totals: dict[str, Decimal]) -> bool:
    difference = raw_totals.get("difference")
    if difference is None:
        return False
    try:
        return Decimal(str(difference)) == Decimal("0")
    except DecimalException:
        return False


def _date_arg(name: str) -> date | None:
    value = request.args.get(name)
    return date.fromisoformat(value) if value else None


def _int_arg(name: str, default: int) -> int:
    value = request.args.get(name, default=str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_arg(name: str) -> bool:
    return request.args.get(name, "").lower() in {"1", "true", "yes", "on"}


def _financial_filters() -> FinancialReportFilters:
    return FinancialReportFilters(
        company=request.args.get("company", "cacao"),
        ledger=request.args.get("ledger") or None,
        accounting_period=request.args.get("accounting_period") or None,
        voucher_number=request.args.get("voucher_number") or None,
        account_code=request.args.get("account_code") or None,
        account_from=request.args.get("account_from") or None,
        account_to=request.args.get("account_to") or None,
        cost_center_code=request.args.get("cost_center_code") or None,
        unit_code=request.args.get("unit_code") or None,
        project_code=request.args.get("project_code") or None,
        party_type=request.args.get("party_type") or None,
        party_id=request.args.get("party_id") or None,
        voucher_type=request.args.get("voucher_type") or None,
        status=request.args.get("status") or "submitted",
        include_running_balance=_bool_arg("include_running_balance"),
        page=max(_int_arg("page", 1), 1),
        page_size=max(_int_arg("page_size", 100), 1),
        sort_by=request.args.get("sort_by", "posting_date"),
        sort_dir=request.args.get("sort_dir", "asc"),
        export_all=False,
    )


def _report_to_matrix(report) -> tuple[list[str], list[list[object]]]:
    columns = report.columns or (list(report.rows[0].values.keys()) if report.rows else [])
    data_rows = [[row.values.get(column) for column in columns] for row in report.rows]
    return columns, data_rows


def _export_financial_report(report, report_code: str, title: str):
    export_format = request.args.get("export")
    if export_format not in {"csv", "xlsx"}:
        return None

    columns, rows = _report_to_matrix(report)
    if export_format == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        writer.writerows(rows)
        return send_file(
            BytesIO(buffer.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{report_code}.csv",
        )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = report_code[:31]
    if columns:
        sheet.append(columns)
        sheet.freeze_panes = "A2"
    for row in rows:
        sheet.append(row)
    for total_name, total_value in report.totals.items():
        sheet.append([f"TOTAL {total_name}", total_value])
    content = BytesIO()
    workbook.save(content)
    content.seek(0)
    return send_file(
        content,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{report_code}.xlsx",
    )


def _render_financial_report(report_code: str, report_title: str, report, report_filters: FinancialReportFilters):
    export_response = _export_financial_report(report, report_code, report_title)
    if export_response is not None:
        return export_response
    columns = report.columns or []
    display_columns = [
        column
        for column in columns
        if any((row.values.get(column) not in (None, "", "—") for row in report.rows)) or column in _ALWAYS_VISIBLE_COLUMNS
    ]
    if not display_columns:
        display_columns = columns
    display_headers = {column: _column_label(column, report.ledger_currency) for column in display_columns}
    display_rows = [
        {column: _format_cell(column, row.values.get(column), report.ledger_currency) for column in display_columns}
        for row in report.rows
    ]
    display_totals = {key: _format_cell(key, value, report.ledger_currency) for key, value in report.totals.items()}
    return render_template(
        "reportes/financial_report.html",
        titulo=f"{report_title} - {APPNAME}",
        report_code=report_code,
        report_title=report_title,
        rows=report.rows,
        columns=display_columns,
        display_headers=display_headers,
        display_rows=display_rows,
        totals=display_totals,
        total_rows=report.total_rows,
        page=report.page,
        page_size=report.page_size,
        ledger_currency=report.ledger_currency,
        context_summary=_build_context_summary(report, report_filters),
        right_align_columns=_RIGHT_ALIGN_COLUMNS,
        is_balanced=_is_report_balanced(report.totals),
    )


@reportes.route("/reports/account-movement")
@login_required
@modulo_activo("accounting")
def account_movement():
    """Reporte unificado de detalle de movimiento contable."""
    filters = _financial_filters()
    report = get_account_movement_detail(filters)
    if request.args.get("export") in {"csv", "xlsx"}:
        export_report = get_account_movement_detail(replace(filters, export_all=True, page=1))
        return _render_financial_report("account-movement", _("Detalle de Movimiento Contable"), export_report, filters)
    return _render_financial_report("account-movement", _("Detalle de Movimiento Contable"), report, filters)


@reportes.route("/reports/trial-balance")
@login_required
@modulo_activo("accounting")
def trial_balance():
    """Reporte de balanza de comprobación."""
    filters = _financial_filters()
    report = get_trial_balance_report(filters)
    return _render_financial_report("trial-balance", _("Balanza de Comprobación"), report, filters)


@reportes.route("/reports/income-statement")
@login_required
@modulo_activo("accounting")
def income_statement():
    """Reporte de estado de resultado."""
    filters = _financial_filters()
    report = get_income_statement_report(filters)
    return _render_financial_report("income-statement", _("Estado de Resultado"), report, filters)


@reportes.route("/reports/balance-sheet")
@login_required
@modulo_activo("accounting")
def balance_sheet():
    """Reporte de balance general."""
    filters = _financial_filters()
    report = get_balance_sheet_report(filters)
    return _render_financial_report("balance-sheet", _("Balance General"), report, filters)


@reportes.route("/reports/subledger")
@login_required
@modulo_activo("accounting")
def subledger():
    """Reporte AR/AP por documento."""
    company = request.args.get("company", "cacao")
    party_type = request.args.get("party_type", "customer")
    report = get_ar_ap_subledger(
        SubledgerFilters(
            company=company,
            party_type=party_type,
            party_id=request.args.get("party_id") or None,
            as_of_date=_date_arg("as_of_date"),
        )
    )
    return render_template(
        "reportes/report_table.html",
        titulo="Subledger AR/AP - " + APPNAME,
        report_title="Subledger AR/AP",
        rows=report.rows,
        totals=report.totals,
    )


@reportes.route("/reports/aging")
@login_required
@modulo_activo("accounting")
def aging():
    """Reporte aging AR/AP."""
    company = request.args.get("company", "cacao")
    party_type = request.args.get("party_type", "customer")
    report = get_aging_report(
        AgingFilters(
            company=company,
            party_type=party_type,
            party_id=request.args.get("party_id") or None,
            as_of_date=_date_arg("as_of_date") or date.today(),
        )
    )
    return render_template(
        "reportes/report_table.html",
        titulo="Aging AR/AP - " + APPNAME,
        report_title="Aging AR/AP",
        rows=report.rows,
        totals=report.totals,
    )


@reportes.route("/reports/kardex")
@login_required
@modulo_activo("inventory")
def kardex():
    """Reporte Kardex."""
    report = get_kardex(
        KardexFilters(
            company=request.args.get("company", "cacao"),
            item_code=request.args.get("item_code") or None,
            warehouse=request.args.get("warehouse") or None,
            date_from=_date_arg("date_from"),
            date_to=_date_arg("date_to"),
        )
    )
    return render_template(
        "reportes/report_table.html",
        titulo="Kardex - " + APPNAME,
        report_title="Kardex",
        rows=report.rows,
        totals=report.totals,
    )


@reportes.route("/reports/reconciliations")
@login_required
@modulo_activo("accounting")
def reconciliations():
    """Reporte de reconciliaciones."""
    report = get_reconciliation_report(
        company=request.args.get("company", "cacao"),
        as_of_date=_date_arg("as_of_date"),
    )
    return render_template(
        "reportes/report_table.html",
        titulo="Reconciliaciones - " + APPNAME,
        report_title="Reconciliaciones",
        rows=report.rows,
        totals=report.totals,
    )


def _operational_filters() -> OperationalReportFilters:
    return OperationalReportFilters(
        company=request.args.get("company", "cacao"),
        date_from=_date_arg("date_from"),
        date_to=_date_arg("date_to"),
        party_id=request.args.get("party_id") or None,
        item_code=request.args.get("item_code") or None,
        warehouse=request.args.get("warehouse") or None,
    )


def _render_operational_report(report_name: str, report):
    return render_template(
        "reportes/report_table.html",
        titulo=report_name + " - " + APPNAME,
        report_title=report_name,
        rows=report.rows,
        totals=report.totals,
    )


@reportes.route("/reports/purchases-by-supplier")
@login_required
@modulo_activo("purchases")
def purchases_by_supplier():
    """Genera reporte de compras agrupadas por proveedor."""
    return _render_operational_report("Compras por Proveedor", get_purchases_by_supplier(_operational_filters()))


@reportes.route("/reports/purchases-by-item")
@login_required
@modulo_activo("purchases")
def purchases_by_item():
    """Genera reporte de compras agrupadas por articulo."""
    return _render_operational_report("Compras por Item", get_purchases_by_item(_operational_filters()))


@reportes.route("/reports/sales-by-customer")
@login_required
@modulo_activo("sales")
def sales_by_customer():
    """Genera reporte de ventas agrupadas por cliente."""
    return _render_operational_report("Ventas por Cliente", get_sales_by_customer(_operational_filters()))


@reportes.route("/reports/sales-by-item")
@login_required
@modulo_activo("sales")
def sales_by_item():
    """Genera reporte de ventas agrupadas por articulo."""
    return _render_operational_report("Ventas por Item", get_sales_by_item(_operational_filters()))


@reportes.route("/reports/gross-margin")
@login_required
@modulo_activo("sales")
def gross_margin():
    """Genera reporte de margen bruto por ventas."""
    return _render_operational_report("Margen Bruto", get_gross_margin(_operational_filters()))


@reportes.route("/reports/stock-balance")
@login_required
@modulo_activo("inventory")
def stock_balance():
    """Genera reporte de balance de stock por articulo y bodega."""
    return _render_operational_report("Stock Balance", get_stock_balance(_operational_filters()))


@reportes.route("/reports/inventory-valuation")
@login_required
@modulo_activo("inventory")
def inventory_valuation():
    """Genera reporte de valoracion del inventario."""
    return _render_operational_report("Valoracion de Inventario", get_inventory_valuation(_operational_filters()))


@reportes.route("/reports/batches")
@login_required
@modulo_activo("inventory")
def batches():
    """Genera reporte de lotes de inventario."""
    return _render_operational_report("Lotes", get_batch_report(_operational_filters()))


@reportes.route("/reports/serials")
@login_required
@modulo_activo("inventory")
def serials():
    """Genera reporte de numeros de serie de inventario."""
    return _render_operational_report("Seriales", get_serial_report(_operational_filters()))
