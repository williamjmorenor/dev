# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Servicios de reportes operativos derivados de GL, stock ledger y conciliaciones."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from cacao_accounting.compras.purchase_reconciliation_service import get_purchase_reconciliation_pending
from cacao_accounting.database import (
    Batch,
    GLEntry,
    PaymentReference,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    Reconciliation,
    ReconciliationItem,
    SalesInvoice,
    SalesInvoiceItem,
    SerialNumber,
    StockBin,
    StockLedgerEntry,
    StockValuationLayer,
    database,
)
from cacao_accounting.document_flow.service import compute_outstanding_amount


@dataclass(frozen=True)
class SubledgerFilters:
    """Filtros para subledger AR/AP."""

    company: str
    party_type: str
    party_id: str | None = None
    as_of_date: date | None = None


@dataclass(frozen=True)
class AgingFilters:
    """Filtros para reporte aging."""

    company: str
    party_type: str
    as_of_date: date
    party_id: str | None = None


@dataclass(frozen=True)
class KardexFilters:
    """Filtros para Kardex."""

    company: str
    item_code: str | None = None
    warehouse: str | None = None
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True)
class OperationalReportFilters:
    """Filtros comunes para reportes operativos."""

    company: str
    date_from: date | None = None
    date_to: date | None = None
    party_id: str | None = None
    item_code: str | None = None
    warehouse: str | None = None


@dataclass(frozen=True)
class ReportRow:
    """Fila generica de reporte."""

    values: dict[str, Any]


@dataclass(frozen=True)
class PaginatedReport:
    """Reporte paginado simple."""

    rows: list[ReportRow]
    totals: dict[str, Decimal]


@dataclass(frozen=True)
class AgingReport:
    """Reporte aging con buckets fijos."""

    rows: list[ReportRow]
    totals: dict[str, Decimal]


def _decimal_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _payment_allocations(reference_type: str, reference_id: str, as_of_date: date | None) -> Decimal:
    query = select(PaymentReference).filter_by(reference_type=reference_type, reference_id=reference_id)
    if as_of_date is not None:
        query = query.where(PaymentReference.allocation_date <= as_of_date)
    return sum(
        (_decimal_value(reference.allocated_amount) for reference in database.session.execute(query).scalars().all()),
        Decimal("0"),
    )


def get_ar_ap_subledger(filters: SubledgerFilters) -> PaginatedReport:
    """Devuelve subledger AR/AP basado en documentos y aplicaciones de pago."""
    if filters.party_type == "customer":
        document_type = "sales_invoice"
        document_model = SalesInvoice
        query = select(SalesInvoice).filter_by(company=filters.company)
        if filters.party_id:
            query = query.filter_by(customer_id=filters.party_id)
    elif filters.party_type == "supplier":
        document_type = "purchase_invoice"
        document_model = PurchaseInvoice
        query = select(PurchaseInvoice).filter_by(company=filters.company)
        if filters.party_id:
            query = query.filter_by(supplier_id=filters.party_id)
    else:
        raise ValueError("El subledger solo soporta customer o supplier.")

    if filters.as_of_date is not None:
        query = query.where(document_model.posting_date <= filters.as_of_date)

    rows: list[ReportRow] = []
    total_original = Decimal("0")
    total_paid = Decimal("0")
    total_outstanding = Decimal("0")
    for document in database.session.execute(query.order_by(document_model.posting_date)).scalars():
        original = _decimal_value(document.grand_total)
        paid = _payment_allocations(document_type, document.id, filters.as_of_date)
        outstanding = compute_outstanding_amount(document, as_of_date=filters.as_of_date)
        total_original += original
        total_paid += paid
        total_outstanding += outstanding
        rows.append(
            ReportRow(
                values={
                    "document_type": document_type,
                    "document_id": document.id,
                    "document_no": getattr(document, "document_no", None) or document.id,
                    "posting_date": document.posting_date,
                    "party_id": getattr(document, "customer_id", None) or getattr(document, "supplier_id", None),
                    "original_amount": original,
                    "paid_amount": paid,
                    "outstanding_amount": outstanding,
                }
            )
        )

    return PaginatedReport(
        rows=rows,
        totals={
            "original_amount": total_original,
            "paid_amount": total_paid,
            "outstanding_amount": total_outstanding,
        },
    )


def get_aging_report(filters: AgingFilters) -> AgingReport:
    """Devuelve aging AR/AP con buckets fijos."""
    subledger = get_ar_ap_subledger(
        SubledgerFilters(
            company=filters.company,
            party_type=filters.party_type,
            party_id=filters.party_id,
            as_of_date=filters.as_of_date,
        )
    )
    bucket_totals = {
        "0_30": Decimal("0"),
        "31_60": Decimal("0"),
        "61_90": Decimal("0"),
        "over_90": Decimal("0"),
    }
    rows: list[ReportRow] = []
    for row in subledger.rows:
        outstanding = _decimal_value(row.values["outstanding_amount"])
        if outstanding <= 0:
            continue
        days = (filters.as_of_date - row.values["posting_date"]).days
        bucket = "0_30"
        if days > 90:
            bucket = "over_90"
        elif days > 60:
            bucket = "61_90"
        elif days > 30:
            bucket = "31_60"
        bucket_totals[bucket] += outstanding
        values = dict(row.values)
        values["days"] = days
        values["bucket"] = bucket
        rows.append(ReportRow(values=values))
    return AgingReport(rows=rows, totals=bucket_totals)


def get_kardex(filters: KardexFilters) -> PaginatedReport:
    """Devuelve Kardex desde StockLedgerEntry."""
    query = select(StockLedgerEntry).filter_by(company=filters.company, is_cancelled=False)
    if filters.item_code:
        query = query.filter_by(item_code=filters.item_code)
    if filters.warehouse:
        query = query.filter_by(warehouse=filters.warehouse)
    if filters.date_from:
        query = query.where(StockLedgerEntry.posting_date >= filters.date_from)
    if filters.date_to:
        query = query.where(StockLedgerEntry.posting_date <= filters.date_to)

    rows: list[ReportRow] = []
    total_in = Decimal("0")
    total_out = Decimal("0")
    total_value = Decimal("0")
    for entry in database.session.execute(
        query.order_by(StockLedgerEntry.posting_date, StockLedgerEntry.created, StockLedgerEntry.id)
    ).scalars():
        qty = _decimal_value(entry.qty_change)
        incoming = qty if qty > 0 else Decimal("0")
        outgoing = abs(qty) if qty < 0 else Decimal("0")
        value_change = _decimal_value(entry.stock_value_difference)
        total_in += incoming
        total_out += outgoing
        total_value += value_change
        rows.append(
            ReportRow(
                values={
                    "posting_date": entry.posting_date,
                    "item_code": entry.item_code,
                    "warehouse": entry.warehouse,
                    "voucher_type": entry.voucher_type,
                    "voucher_id": entry.voucher_id,
                    "incoming_qty": incoming,
                    "outgoing_qty": outgoing,
                    "balance_qty": _decimal_value(entry.qty_after_transaction),
                    "valuation_rate": _decimal_value(entry.valuation_rate),
                    "value_change": value_change,
                    "stock_value": _decimal_value(entry.stock_value),
                }
            )
        )
    return PaginatedReport(
        rows=rows,
        totals={"incoming_qty": total_in, "outgoing_qty": total_out, "value_change": total_value},
    )


def get_reconciliation_report(company: str, as_of_date: date | None = None) -> PaginatedReport:
    """Devuelve reconciliaciones bancarias y conciliaciones de compras pendientes."""
    query = (
        select(Reconciliation, ReconciliationItem)
        .join(
            ReconciliationItem,
            ReconciliationItem.reconciliation_id == Reconciliation.id,
        )
        .filter(Reconciliation.company == company)
    )
    if as_of_date:
        query = query.where(Reconciliation.recon_date <= as_of_date)

    rows = [
        ReportRow(
            values={
                "reconciliation_id": reconciliation.id,
                "recon_date": reconciliation.recon_date,
                "recon_type": reconciliation.recon_type,
                "source_type": item.source_type or item.reference_type,
                "source_id": item.source_id or item.reference_id,
                "target_type": item.target_type,
                "target_id": item.target_id,
                "amount": _decimal_value(item.allocated_amount or item.amount),
                "status": item.status,
            }
        )
        for reconciliation, item in database.session.execute(query).all()
    ]
    bank_total = sum((_decimal_value(row.values["amount"]) for row in rows), Decimal("0"))
    purchase_pending = get_purchase_reconciliation_pending(company=company, as_of_date=as_of_date)
    for pending in purchase_pending:
        rows.append(
            ReportRow(
                values={
                    "reconciliation_id": pending.purchase_receipt_id,
                    "recon_date": as_of_date,
                    "recon_type": "purchase_reconciliation",
                    "source_type": "purchase_receipt_item",
                    "source_id": pending.purchase_receipt_item_id,
                    "target_type": None,
                    "target_id": None,
                    "amount": pending.pending_amount,
                    "status": pending.status,
                }
            )
        )
    return PaginatedReport(
        rows=rows,
        totals={
            "bank_reconciled_amount": bank_total,
            "purchase_pending_amount": sum((row.pending_amount for row in purchase_pending), Decimal("0")),
        },
    )


def get_purchases_by_supplier(filters: OperationalReportFilters) -> PaginatedReport:
    """Compras agregadas por proveedor."""
    query = select(PurchaseInvoice).filter_by(company=filters.company)
    if filters.party_id:
        query = query.filter_by(supplier_id=filters.party_id)
    if filters.date_from:
        query = query.where(PurchaseInvoice.posting_date >= filters.date_from)
    if filters.date_to:
        query = query.where(PurchaseInvoice.posting_date <= filters.date_to)
    totals: dict[str, Decimal] = {}
    for invoice in database.session.execute(query).scalars():
        supplier_id = invoice.supplier_id or ""
        totals[supplier_id] = totals.get(supplier_id, Decimal("0")) + _decimal_value(invoice.grand_total or invoice.total)
    rows = [ReportRow({"supplier_id": supplier_id, "amount": amount}) for supplier_id, amount in sorted(totals.items())]
    return PaginatedReport(rows=rows, totals={"amount": sum(totals.values(), Decimal("0"))})


def get_purchases_by_item(filters: OperationalReportFilters) -> PaginatedReport:
    """Compras agregadas por item."""
    query = (
        select(PurchaseInvoice, PurchaseInvoiceItem)
        .join(PurchaseInvoiceItem, PurchaseInvoiceItem.purchase_invoice_id == PurchaseInvoice.id)
        .filter(PurchaseInvoice.company == filters.company)
    )
    if filters.item_code:
        query = query.filter(PurchaseInvoiceItem.item_code == filters.item_code)
    if filters.date_from:
        query = query.where(PurchaseInvoice.posting_date >= filters.date_from)
    if filters.date_to:
        query = query.where(PurchaseInvoice.posting_date <= filters.date_to)
    totals: dict[str, dict[str, Decimal]] = {}
    for _, item in database.session.execute(query).all():
        row = totals.setdefault(item.item_code, {"qty": Decimal("0"), "amount": Decimal("0")})
        row["qty"] += _decimal_value(item.qty)
        row["amount"] += _decimal_value(item.amount)
    rows = [
        ReportRow({"item_code": item_code, "qty": values["qty"], "amount": values["amount"]})
        for item_code, values in sorted(totals.items())
    ]
    return PaginatedReport(
        rows=rows,
        totals={
            "qty": sum((values["qty"] for values in totals.values()), Decimal("0")),
            "amount": sum((values["amount"] for values in totals.values()), Decimal("0")),
        },
    )


def get_sales_by_customer(filters: OperationalReportFilters) -> PaginatedReport:
    """Ventas agregadas por cliente."""
    query = select(SalesInvoice).filter_by(company=filters.company)
    if filters.party_id:
        query = query.filter_by(customer_id=filters.party_id)
    if filters.date_from:
        query = query.where(SalesInvoice.posting_date >= filters.date_from)
    if filters.date_to:
        query = query.where(SalesInvoice.posting_date <= filters.date_to)
    totals: dict[str, Decimal] = {}
    for invoice in database.session.execute(query).scalars():
        customer_id = invoice.customer_id or ""
        totals[customer_id] = totals.get(customer_id, Decimal("0")) + _decimal_value(invoice.grand_total or invoice.total)
    rows = [ReportRow({"customer_id": customer_id, "amount": amount}) for customer_id, amount in sorted(totals.items())]
    return PaginatedReport(rows=rows, totals={"amount": sum(totals.values(), Decimal("0"))})


def get_sales_by_item(filters: OperationalReportFilters) -> PaginatedReport:
    """Ventas agregadas por item."""
    query = (
        select(SalesInvoice, SalesInvoiceItem)
        .join(SalesInvoiceItem, SalesInvoiceItem.sales_invoice_id == SalesInvoice.id)
        .filter(SalesInvoice.company == filters.company)
    )
    if filters.item_code:
        query = query.filter(SalesInvoiceItem.item_code == filters.item_code)
    if filters.date_from:
        query = query.where(SalesInvoice.posting_date >= filters.date_from)
    if filters.date_to:
        query = query.where(SalesInvoice.posting_date <= filters.date_to)
    totals: dict[str, dict[str, Decimal]] = {}
    for _, item in database.session.execute(query).all():
        row = totals.setdefault(item.item_code, {"qty": Decimal("0"), "amount": Decimal("0")})
        row["qty"] += _decimal_value(item.qty)
        row["amount"] += _decimal_value(item.amount)
    rows = [
        ReportRow({"item_code": item_code, "qty": values["qty"], "amount": values["amount"]})
        for item_code, values in sorted(totals.items())
    ]
    return PaginatedReport(
        rows=rows,
        totals={
            "qty": sum((values["qty"] for values in totals.values()), Decimal("0")),
            "amount": sum((values["amount"] for values in totals.values()), Decimal("0")),
        },
    )


def get_gross_margin(filters: OperationalReportFilters) -> PaginatedReport:
    """Margen bruto basado en GL: ingresos menos COGS."""
    query = select(GLEntry).filter_by(company=filters.company, is_cancelled=False)
    if filters.date_from:
        query = query.where(GLEntry.posting_date >= filters.date_from)
    if filters.date_to:
        query = query.where(GLEntry.posting_date <= filters.date_to)
    income = Decimal("0")
    cogs = Decimal("0")
    for entry in database.session.execute(query).scalars():
        remarks = (entry.remarks or "").lower()
        if "costo" in remarks:
            cogs += _decimal_value(entry.debit) - _decimal_value(entry.credit)
        elif entry.voucher_type == "sales_invoice":
            income += _decimal_value(entry.credit) - _decimal_value(entry.debit)
    margin = income - cogs
    return PaginatedReport(
        rows=[ReportRow({"income": income, "cogs": cogs, "gross_margin": margin})],
        totals={"income": income, "cogs": cogs, "gross_margin": margin},
    )


def get_stock_balance(filters: OperationalReportFilters) -> PaginatedReport:
    """Existencia actual desde StockBin."""
    query = select(StockBin).filter_by(company=filters.company)
    if filters.item_code:
        query = query.filter_by(item_code=filters.item_code)
    if filters.warehouse:
        query = query.filter_by(warehouse=filters.warehouse)
    rows = [
        ReportRow(
            {
                "item_code": bin_row.item_code,
                "warehouse": bin_row.warehouse,
                "actual_qty": _decimal_value(bin_row.actual_qty),
                "valuation_rate": _decimal_value(bin_row.valuation_rate),
                "stock_value": _decimal_value(bin_row.stock_value),
            }
        )
        for bin_row in database.session.execute(query).scalars()
    ]
    return PaginatedReport(
        rows=rows, totals={"stock_value": sum((_decimal_value(row.values["stock_value"]) for row in rows), Decimal("0"))}
    )


def get_inventory_valuation(filters: OperationalReportFilters) -> PaginatedReport:
    """Valoracion de inventario desde capas de valuacion."""
    query = select(StockValuationLayer).filter_by(company=filters.company)
    if filters.item_code:
        query = query.filter_by(item_code=filters.item_code)
    if filters.warehouse:
        query = query.filter_by(warehouse=filters.warehouse)
    rows = [
        ReportRow(
            {
                "item_code": layer.item_code,
                "warehouse": layer.warehouse,
                "remaining_qty": _decimal_value(layer.remaining_qty),
                "remaining_stock_value": _decimal_value(layer.remaining_stock_value),
            }
        )
        for layer in database.session.execute(query).scalars()
    ]
    return PaginatedReport(
        rows=rows,
        totals={
            "remaining_stock_value": sum((_decimal_value(row.values["remaining_stock_value"]) for row in rows), Decimal("0"))
        },
    )


def get_batch_report(filters: OperationalReportFilters) -> PaginatedReport:
    """Reporte de lotes."""
    query = select(Batch)
    if filters.item_code:
        query = query.filter_by(item_code=filters.item_code)
    rows = [
        ReportRow(
            {
                "item_code": batch.item_code,
                "batch_no": batch.batch_no,
                "expiry_date": batch.expiry_date,
                "is_active": batch.is_active,
            }
        )
        for batch in database.session.execute(query).scalars()
    ]
    return PaginatedReport(rows=rows, totals={"count": Decimal(len(rows))})


def get_serial_report(filters: OperationalReportFilters) -> PaginatedReport:
    """Reporte de numeros de serie."""
    query = select(SerialNumber)
    if filters.item_code:
        query = query.filter_by(item_code=filters.item_code)
    if filters.warehouse:
        query = query.filter_by(warehouse=filters.warehouse)
    rows = [
        ReportRow(
            {
                "item_code": serial.item_code,
                "serial_no": serial.serial_no,
                "status": serial.serial_status,
                "warehouse": serial.warehouse,
            }
        )
        for serial in database.session.execute(query).scalars()
    ]
    return PaginatedReport(rows=rows, totals={"count": Decimal(len(rows))})
