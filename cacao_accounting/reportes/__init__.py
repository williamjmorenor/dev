# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Reportes operativos de subledgers, aging, Kardex y reconciliaciones."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, render_template, request
from flask_login import login_required

from cacao_accounting.decorators import modulo_activo
from cacao_accounting.reportes.services import (
    AgingFilters,
    KardexFilters,
    OperationalReportFilters,
    SubledgerFilters,
    get_aging_report,
    get_ar_ap_subledger,
    get_batch_report,
    get_gross_margin,
    get_inventory_valuation,
    get_kardex,
    get_purchases_by_item,
    get_purchases_by_supplier,
    get_reconciliation_report,
    get_sales_by_customer,
    get_sales_by_item,
    get_serial_report,
    get_stock_balance,
)
from cacao_accounting.version import APPNAME

reportes = Blueprint("reportes", __name__, template_folder="templates")


def _date_arg(name: str) -> date | None:
    value = request.args.get(name)
    return date.fromisoformat(value) if value else None


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
    return _render_operational_report("Compras por Proveedor", get_purchases_by_supplier(_operational_filters()))


@reportes.route("/reports/purchases-by-item")
@login_required
@modulo_activo("purchases")
def purchases_by_item():
    return _render_operational_report("Compras por Item", get_purchases_by_item(_operational_filters()))


@reportes.route("/reports/sales-by-customer")
@login_required
@modulo_activo("sales")
def sales_by_customer():
    return _render_operational_report("Ventas por Cliente", get_sales_by_customer(_operational_filters()))


@reportes.route("/reports/sales-by-item")
@login_required
@modulo_activo("sales")
def sales_by_item():
    return _render_operational_report("Ventas por Item", get_sales_by_item(_operational_filters()))


@reportes.route("/reports/gross-margin")
@login_required
@modulo_activo("sales")
def gross_margin():
    return _render_operational_report("Margen Bruto", get_gross_margin(_operational_filters()))


@reportes.route("/reports/stock-balance")
@login_required
@modulo_activo("inventory")
def stock_balance():
    return _render_operational_report("Stock Balance", get_stock_balance(_operational_filters()))


@reportes.route("/reports/inventory-valuation")
@login_required
@modulo_activo("inventory")
def inventory_valuation():
    return _render_operational_report("Valoracion de Inventario", get_inventory_valuation(_operational_filters()))


@reportes.route("/reports/batches")
@login_required
@modulo_activo("inventory")
def batches():
    return _render_operational_report("Lotes", get_batch_report(_operational_filters()))


@reportes.route("/reports/serials")
@login_required
@modulo_activo("inventory")
def serials():
    return _render_operational_report("Seriales", get_serial_report(_operational_filters()))
