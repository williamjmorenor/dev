# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Servicios de conciliacion GR/IR por lineas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from cacao_accounting.database import (
    GRIRReconciliation,
    GRIRReconciliationItem,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    database,
)


class GRIRServiceError(ValueError):
    """Error controlado de conciliacion GR/IR."""


@dataclass(frozen=True)
class GRIRResult:
    """Resultado resumido de una conciliacion GR/IR."""

    reconciliation_id: str
    matched_qty: Decimal
    matched_amount: Decimal
    price_difference: Decimal
    status: str


@dataclass(frozen=True)
class GRIRPendingRow:
    """Fila pendiente de conciliacion GR/IR."""

    purchase_receipt_id: str
    purchase_receipt_item_id: str
    item_code: str
    warehouse: str | None
    uom: str | None
    pending_qty: Decimal
    pending_amount: Decimal
    status: str


def _decimal_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _line_qty(line: Any) -> Decimal:
    return _decimal_value(getattr(line, "qty_in_base_uom", None) or getattr(line, "qty", None))


def _line_amount(line: Any) -> Decimal:
    amount = _decimal_value(getattr(line, "amount", None))
    if amount:
        return amount
    return _line_qty(line) * _decimal_value(getattr(line, "rate", None) or getattr(line, "valuation_rate", None))


def _line_rate(line: Any) -> Decimal:
    qty = _line_qty(line)
    if qty <= 0:
        raise GRIRServiceError("La linea GR/IR requiere cantidad positiva.")
    return _line_amount(line) / qty


def _matched_qty_for_receipt_item(receipt_item_id: str) -> Decimal:
    matched = database.session.execute(
        select(func.coalesce(func.sum(GRIRReconciliationItem.matched_qty), 0)).filter_by(
            purchase_receipt_item_id=receipt_item_id,
            status="reconciled",
        )
    ).scalar_one()
    return _decimal_value(matched)


def _matched_amount_for_receipt_item(receipt_item_id: str) -> Decimal:
    matched = database.session.execute(
        select(func.coalesce(func.sum(GRIRReconciliationItem.matched_amount), 0)).filter_by(
            purchase_receipt_item_id=receipt_item_id,
            status="reconciled",
        )
    ).scalar_one()
    return _decimal_value(matched)


def _receipt_items(receipt_id: str) -> list[PurchaseReceiptItem]:
    return list(
        database.session.execute(select(PurchaseReceiptItem).filter_by(purchase_receipt_id=receipt_id)).scalars().all()
    )


def _invoice_items(invoice_id: str) -> list[PurchaseInvoiceItem]:
    return list(
        database.session.execute(select(PurchaseInvoiceItem).filter_by(purchase_invoice_id=invoice_id)).scalars().all()
    )


def _find_receipt_item_for_invoice_line(
    receipt_items: list[PurchaseReceiptItem],
    invoice_item: PurchaseInvoiceItem,
) -> PurchaseReceiptItem:
    candidates = [
        receipt_item
        for receipt_item in receipt_items
        if receipt_item.item_code == invoice_item.item_code
        and receipt_item.uom == invoice_item.uom
        and (invoice_item.warehouse is None or receipt_item.warehouse == invoice_item.warehouse)
    ]
    if not candidates:
        raise GRIRServiceError("No existe linea de recepcion compatible para la linea de factura.")
    if len(candidates) > 1 and invoice_item.warehouse is None:
        raise GRIRServiceError("La linea de factura requiere almacen para conciliar GR/IR sin ambiguedad.")
    return candidates[0]


def reconcile_gr_ir_invoice(purchase_invoice_id: str) -> GRIRResult:
    """Reconcilia una factura de compra contra su recepcion por lineas."""

    duplicate = database.session.execute(
        select(GRIRReconciliation.id)
        .filter_by(purchase_invoice_id=purchase_invoice_id)
        .where(GRIRReconciliation.status != "cancelled")
        .limit(1)
    ).scalar_one_or_none()
    if duplicate:
        raise GRIRServiceError("La factura de compra ya tiene una conciliacion GR/IR activa.")

    invoice = database.session.get(PurchaseInvoice, purchase_invoice_id)
    if not invoice or not invoice.purchase_receipt_id:
        raise GRIRServiceError("La factura de compra no referencia una recepcion.")
    receipt = database.session.get(PurchaseReceipt, invoice.purchase_receipt_id)
    if not receipt:
        raise GRIRServiceError("La recepcion de compra referenciada no existe.")
    if receipt.company != invoice.company:
        raise GRIRServiceError("La factura y la recepcion deben pertenecer a la misma compania.")
    if getattr(receipt, "docstatus", 0) != 1:
        raise GRIRServiceError("La recepcion de compra debe estar aprobada.")

    receipt_items = _receipt_items(receipt.id)
    invoice_items = _invoice_items(invoice.id)
    if not receipt_items or not invoice_items:
        raise GRIRServiceError("La conciliacion GR/IR requiere lineas de recepcion y factura.")

    reconciliation = GRIRReconciliation(
        company=invoice.company,
        purchase_receipt_id=receipt.id,
        purchase_invoice_id=invoice.id,
        matched_amount=Decimal("0"),
        matched_date=invoice.posting_date,
        status="reconciled",
    )
    database.session.add(reconciliation)
    database.session.flush()

    total_qty = Decimal("0")
    total_amount = Decimal("0")
    total_difference = Decimal("0")
    for invoice_item in invoice_items:
        receipt_item = _find_receipt_item_for_invoice_line(receipt_items, invoice_item)
        invoice_qty = _line_qty(invoice_item)
        receipt_qty = _line_qty(receipt_item)
        pending_qty = receipt_qty - _matched_qty_for_receipt_item(receipt_item.id)
        if invoice_qty <= 0:
            raise GRIRServiceError("La cantidad facturada GR/IR debe ser positiva.")
        if invoice_qty > pending_qty:
            raise GRIRServiceError("La factura excede la cantidad pendiente recibida.")

        receipt_rate = _line_rate(receipt_item)
        invoice_rate = _line_rate(invoice_item)
        matched_amount = invoice_qty * receipt_rate
        invoiced_amount = invoice_qty * invoice_rate
        price_difference = invoiced_amount - matched_amount
        if price_difference != 0:
            raise GRIRServiceError("La diferencia de precio GR/IR requiere cuenta de ajuste configurada.")

        status = "reconciled" if invoice_qty == pending_qty else "partial"
        database.session.add(
            GRIRReconciliationItem(
                gr_ir_reconciliation_id=reconciliation.id,
                purchase_receipt_item_id=receipt_item.id,
                purchase_invoice_item_id=invoice_item.id,
                item_code=invoice_item.item_code,
                warehouse=receipt_item.warehouse,
                uom=invoice_item.uom,
                received_qty=receipt_qty,
                invoiced_qty=invoice_qty,
                matched_qty=invoice_qty,
                received_amount=invoice_qty * receipt_rate,
                invoiced_amount=invoiced_amount,
                matched_amount=matched_amount,
                price_difference=price_difference,
                status="reconciled",
            )
        )
        total_qty += invoice_qty
        total_amount += matched_amount
        total_difference += price_difference
        if status == "partial":
            reconciliation.status = "partial"

    reconciliation.matched_amount = total_amount
    return GRIRResult(
        reconciliation_id=reconciliation.id,
        matched_qty=total_qty,
        matched_amount=total_amount,
        price_difference=total_difference,
        status=str(reconciliation.status),
    )


def cancel_gr_ir_for_invoice(purchase_invoice_id: str) -> None:
    """Marca como canceladas las conciliaciones GR/IR asociadas a una factura."""

    reconciliations = (
        database.session.execute(
            select(GRIRReconciliation)
            .filter_by(purchase_invoice_id=purchase_invoice_id)
            .where(GRIRReconciliation.status != "cancelled")
        )
        .scalars()
        .all()
    )
    for reconciliation in reconciliations:
        reconciliation.status = "cancelled"
        for item in (
            database.session.execute(select(GRIRReconciliationItem).filter_by(gr_ir_reconciliation_id=reconciliation.id))
            .scalars()
            .all()
        ):
            item.status = "cancelled"


def get_gr_ir_pending(company: str, as_of_date: date | None = None) -> list[GRIRPendingRow]:
    """Devuelve saldos GR/IR pendientes por linea de recepcion."""

    query = (
        select(PurchaseReceipt, PurchaseReceiptItem)
        .join(
            PurchaseReceiptItem,
            PurchaseReceiptItem.purchase_receipt_id == PurchaseReceipt.id,
        )
        .filter(PurchaseReceipt.company == company)
    )
    if as_of_date is not None:
        query = query.where(PurchaseReceipt.posting_date <= as_of_date)

    rows: list[GRIRPendingRow] = []
    for receipt, item in database.session.execute(query).all():
        item_qty = _line_qty(item)
        item_amount = _line_amount(item)
        pending_qty = item_qty - _matched_qty_for_receipt_item(item.id)
        pending_amount = item_amount - _matched_amount_for_receipt_item(item.id)
        if pending_qty <= 0 and pending_amount <= 0:
            continue
        rows.append(
            GRIRPendingRow(
                purchase_receipt_id=receipt.id,
                purchase_receipt_item_id=item.id,
                item_code=item.item_code,
                warehouse=item.warehouse,
                uom=item.uom,
                pending_qty=pending_qty,
                pending_amount=pending_amount,
                status="partial" if pending_qty < item_qty else "open",
            )
        )
    return rows
