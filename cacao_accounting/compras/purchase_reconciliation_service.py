# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Servicio de conciliacion de recepciones de compra con facturas de proveedor.

Framework desacoplado de conciliacion de compras (process-first, event-driven).
Soporta matching 2-way (OC vs Factura) y 3-way (OC vs Recepcion vs Factura).
Los parametros son configurables por compania mediante PurchaseMatchingConfig.

Nota de diseño: la terminologia GR/IR (Goods Receipt / Invoice Receipt) es
propia de SAP y queda prohibida en este proyecto.  Se utiliza el termino
generico "Conciliacion de Compras" o "Purchase Reconciliation".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import func, select

from cacao_accounting.database import (
    PurchaseEconomicEvent,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    PurchaseMatchingConfig,
    PurchaseReceipt,
    PurchaseReceiptItem,
    PurchaseReconciliation,
    PurchaseReconciliationItem,
    database,
)

# ---------------------------------------------------------------------------
# Enums publicos para estados y tipos
# ---------------------------------------------------------------------------


class MatchingType(str, Enum):
    """Tipo de matching de compras soportado."""

    TWO_WAY = "2-way"
    THREE_WAY = "3-way"


class MatchingResult(str, Enum):
    """Resultado de la evaluacion del motor de matching."""

    MATCH_OK = "MATCH_OK"
    MATCH_PARTIAL = "MATCH_PARTIAL"
    MATCH_FAILED = "MATCH_FAILED"


class ToleranceType(str, Enum):
    """Tipo de tolerancia: porcentaje o valor absoluto."""

    PERCENTAGE = "percentage"
    ABSOLUTE = "absolute"


class EventType(str, Enum):
    """Tipos de eventos economicos inmutables generados por el flujo de compras."""

    GOODS_RECEIVED = "GOODS_RECEIVED"
    INVOICE_RECEIVED = "INVOICE_RECEIVED"
    MATCH_COMPLETED = "MATCH_COMPLETED"
    MATCH_FAILED = "MATCH_FAILED"
    MATCH_CANCELLED = "MATCH_CANCELLED"


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------


class PurchaseReconciliationError(ValueError):
    """Error controlado del motor de conciliacion de compras."""


# Alias de compatibilidad — no usar en codigo nuevo
GRIRServiceError = PurchaseReconciliationError


# ---------------------------------------------------------------------------
# Dataclasses de resultado
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PurchaseReconciliationResult:
    """Resultado resumido de una conciliacion de compras."""

    reconciliation_id: str
    matched_qty: Decimal
    matched_amount: Decimal
    price_difference: Decimal
    status: str
    matching_result: str


@dataclass(frozen=True)
class PurchasePendingRow:
    """Fila pendiente de conciliacion de compras."""

    purchase_receipt_id: str
    purchase_receipt_item_id: str
    item_code: str
    warehouse: str | None
    uom: str | None
    pending_qty: Decimal
    pending_amount: Decimal
    status: str


@dataclass(frozen=True)
class MatchingConfig:
    """Configuracion del motor de matching extraida de PurchaseMatchingConfig."""

    matching_type: str
    price_tolerance_type: str
    price_tolerance_value: Decimal
    qty_tolerance_type: str
    qty_tolerance_value: Decimal
    require_purchase_order: bool
    bridge_account_required: bool
    auto_reconcile: bool
    allow_price_difference: bool


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


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
        raise PurchaseReconciliationError("La linea de conciliacion requiere cantidad positiva.")
    return _line_amount(line) / qty


def _matched_qty_for_receipt_item(receipt_item_id: str) -> Decimal:
    matched = database.session.execute(
        select(func.coalesce(func.sum(PurchaseReconciliationItem.matched_qty), 0))
        .filter_by(
            purchase_receipt_item_id=receipt_item_id,
        )
        .where(PurchaseReconciliationItem.status != "cancelled")
    ).scalar_one()
    return _decimal_value(matched)


def _matched_amount_for_receipt_item(receipt_item_id: str) -> Decimal:
    matched = database.session.execute(
        select(func.coalesce(func.sum(PurchaseReconciliationItem.matched_amount), 0))
        .filter_by(
            purchase_receipt_item_id=receipt_item_id,
        )
        .where(PurchaseReconciliationItem.status != "cancelled")
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
        ri
        for ri in receipt_items
        if ri.item_code == invoice_item.item_code
        and ri.uom == invoice_item.uom
        and (invoice_item.warehouse is None or ri.warehouse == invoice_item.warehouse)
    ]
    if not candidates:
        raise PurchaseReconciliationError("No existe linea de recepcion compatible para la linea de factura.")
    if len(candidates) > 1 and invoice_item.warehouse is None:
        raise PurchaseReconciliationError("La linea de factura requiere almacen para conciliar sin ambiguedad.")
    return candidates[0]


def _within_tolerance(difference: Decimal, reference: Decimal, tolerance_type: str, tolerance_value: Decimal) -> bool:
    """Evalua si una diferencia esta dentro de la tolerancia configurada.

    Nota: con tolerancia porcentual y referencia == 0, solo se acepta
    diferencia == 0 (no se puede calcular porcentaje sobre base cero).
    """
    if tolerance_value <= 0:
        return difference == 0
    match tolerance_type:
        case ToleranceType.PERCENTAGE:
            if reference == 0:
                # No se puede calcular % sobre base cero: solo acepta diferencia exacta
                return difference == 0
            return abs(difference / reference * 100) <= tolerance_value
        case _:
            return abs(difference) <= tolerance_value


# ---------------------------------------------------------------------------
# Servicio de configuracion de matching
# ---------------------------------------------------------------------------


def get_matching_config(company: str) -> MatchingConfig:
    """Devuelve la configuracion de matching para la compania dada.

    Si no existe configuracion, retorna los valores por defecto (modo estricto).
    """
    config = database.session.execute(select(PurchaseMatchingConfig).filter_by(company=company)).scalar_one_or_none()

    if config is None:
        return MatchingConfig(
            matching_type=MatchingType.THREE_WAY,
            price_tolerance_type=ToleranceType.PERCENTAGE,
            price_tolerance_value=Decimal("0"),
            qty_tolerance_type=ToleranceType.PERCENTAGE,
            qty_tolerance_value=Decimal("0"),
            require_purchase_order=True,
            bridge_account_required=True,
            auto_reconcile=True,
            allow_price_difference=False,
        )

    return MatchingConfig(
        matching_type=str(config.matching_type),
        price_tolerance_type=str(config.price_tolerance_type),
        price_tolerance_value=_decimal_value(config.price_tolerance_value),
        qty_tolerance_type=str(config.qty_tolerance_type),
        qty_tolerance_value=_decimal_value(config.qty_tolerance_value),
        require_purchase_order=bool(config.require_purchase_order),
        bridge_account_required=bool(config.bridge_account_required),
        auto_reconcile=bool(config.auto_reconcile),
        allow_price_difference=bool(config.allow_price_difference),
    )


def seed_matching_config_for_company(company: str) -> PurchaseMatchingConfig:
    """Crea la configuracion de matching en modo estricto para una compania nueva.

    El usuario puede relajar las tolerancias desde la pantalla de configuracion.
    """
    existing = database.session.execute(select(PurchaseMatchingConfig).filter_by(company=company)).scalar_one_or_none()
    if existing is not None:
        return existing

    config = PurchaseMatchingConfig(
        company=company,
        matching_type=MatchingType.THREE_WAY,
        price_tolerance_type=ToleranceType.PERCENTAGE,
        price_tolerance_value=Decimal("0"),
        qty_tolerance_type=ToleranceType.PERCENTAGE,
        qty_tolerance_value=Decimal("0"),
        require_purchase_order=True,
        bridge_account_required=True,
        auto_reconcile=True,
        allow_price_difference=False,
    )
    database.session.add(config)
    return config


# ---------------------------------------------------------------------------
# Motor de eventos economicos
# ---------------------------------------------------------------------------


def emit_economic_event(
    event_type: str,
    company: str,
    document_type: str,
    document_id: str,
    payload: dict[str, Any] | None = None,
) -> PurchaseEconomicEvent:
    """Emite un evento economico inmutable al log de eventos."""
    event = PurchaseEconomicEvent(
        event_type=event_type,
        company=company,
        document_type=document_type,
        document_id=document_id,
        payload=json.dumps(payload or {}),
        processing_status="pending",
    )
    database.session.add(event)
    return event


def mark_event_processed(event: PurchaseEconomicEvent) -> None:
    """Marca un evento como procesado."""
    event.processing_status = "processed"
    event.processed_at = datetime.utcnow()


# ---------------------------------------------------------------------------
# Motor de matching principal
# ---------------------------------------------------------------------------


def _evaluate_matching_result(
    total_invoiced_qty: Decimal,
    total_received_qty: Decimal,
    total_price_difference: Decimal,
    total_invoiced_amount: Decimal,
    config: MatchingConfig,
) -> str:
    """Evalua el resultado del matching segun la configuracion de tolerancias."""
    qty_ok = _within_tolerance(
        total_invoiced_qty - total_received_qty,
        total_received_qty,
        config.qty_tolerance_type,
        config.qty_tolerance_value,
    )
    price_ok = _within_tolerance(
        total_price_difference,
        total_invoiced_amount,
        config.price_tolerance_type,
        config.price_tolerance_value,
    )

    if qty_ok and price_ok:
        return MatchingResult.MATCH_OK
    if qty_ok or price_ok:
        return MatchingResult.MATCH_PARTIAL
    return MatchingResult.MATCH_FAILED


def reconcile_purchase_invoice(purchase_invoice_id: str) -> PurchaseReconciliationResult:
    """Concilia una factura de compra contra su recepcion por lineas.

    Utiliza la configuracion de matching de la compania (2-way o 3-way)
    y respeta las tolerancias configuradas.
    """
    duplicate = database.session.execute(
        select(PurchaseReconciliation.id)
        .filter_by(purchase_invoice_id=purchase_invoice_id)
        .where(PurchaseReconciliation.status != "cancelled")
        .limit(1)
    ).scalar_one_or_none()
    if duplicate:
        raise PurchaseReconciliationError("La factura de compra ya tiene una conciliacion activa.")

    invoice = database.session.get(PurchaseInvoice, purchase_invoice_id)
    if not invoice or not invoice.purchase_receipt_id:
        raise PurchaseReconciliationError("La factura de compra no referencia una recepcion.")
    receipt = database.session.get(PurchaseReceipt, invoice.purchase_receipt_id)
    if not receipt:
        raise PurchaseReconciliationError("La recepcion de compra referenciada no existe.")
    if receipt.company != invoice.company:
        raise PurchaseReconciliationError("La factura y la recepcion deben pertenecer a la misma compania.")
    if getattr(receipt, "docstatus", 0) != 1:
        raise PurchaseReconciliationError("La recepcion de compra debe estar aprobada.")

    config = get_matching_config(str(invoice.company))

    receipt_items = _receipt_items(receipt.id)
    invoice_items = _invoice_items(invoice.id)
    if not receipt_items or not invoice_items:
        raise PurchaseReconciliationError("La conciliacion requiere lineas de recepcion y factura.")

    reconciliation = PurchaseReconciliation(
        company=invoice.company,
        purchase_receipt_id=receipt.id,
        purchase_invoice_id=invoice.id,
        matching_type=config.matching_type,
        matched_amount=Decimal("0"),
        matched_date=invoice.posting_date,
        status="pending_invoice",
    )
    database.session.add(reconciliation)
    database.session.flush()

    total_qty = Decimal("0")
    total_amount = Decimal("0")
    total_difference = Decimal("0")
    total_invoiced_qty = Decimal("0")
    total_received_qty = Decimal("0")

    for invoice_item in invoice_items:
        receipt_item = _find_receipt_item_for_invoice_line(receipt_items, invoice_item)
        invoice_qty = _line_qty(invoice_item)
        receipt_qty = _line_qty(receipt_item)
        pending_qty = receipt_qty - _matched_qty_for_receipt_item(receipt_item.id)
        if invoice_qty <= 0:
            raise PurchaseReconciliationError("La cantidad facturada debe ser positiva.")
        if invoice_qty > pending_qty:
            raise PurchaseReconciliationError("La factura excede la cantidad pendiente recibida.")

        receipt_rate = _line_rate(receipt_item)
        invoice_rate = _line_rate(invoice_item)
        matched_amount = invoice_qty * receipt_rate
        invoiced_amount = invoice_qty * invoice_rate
        price_difference = invoiced_amount - matched_amount

        if price_difference != 0 and not config.allow_price_difference:
            raise PurchaseReconciliationError("La diferencia de precio requiere cuenta de ajuste configurada.")

        # Item is always "reconciled" once created — partial/full is tracked on the header
        database.session.add(
            PurchaseReconciliationItem(
                purchase_reconciliation_id=reconciliation.id,
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
        total_invoiced_qty += invoice_qty
        total_received_qty += receipt_qty

    matching_result = _evaluate_matching_result(
        total_invoiced_qty,
        total_received_qty,
        total_difference,
        total_amount + total_difference,
        config,
    )

    match matching_result:
        case MatchingResult.MATCH_OK:
            reconciliation.status = "reconciled"
            event_type = EventType.MATCH_COMPLETED
        case MatchingResult.MATCH_PARTIAL:
            reconciliation.status = "partial"
            event_type = EventType.MATCH_COMPLETED
        case _:
            reconciliation.status = "disputed"
            event_type = EventType.MATCH_FAILED

    reconciliation.matched_amount = total_amount

    emit_economic_event(
        event_type=event_type,
        company=str(invoice.company),
        document_type="purchase_reconciliation",
        document_id=reconciliation.id,
        payload={
            "purchase_invoice_id": purchase_invoice_id,
            "purchase_receipt_id": receipt.id,
            "matched_qty": str(total_qty),
            "matched_amount": str(total_amount),
            "price_difference": str(total_difference),
            "matching_result": matching_result,
            "matching_type": config.matching_type,
        },
    )

    return PurchaseReconciliationResult(
        reconciliation_id=reconciliation.id,
        matched_qty=total_qty,
        matched_amount=total_amount,
        price_difference=total_difference,
        status=str(reconciliation.status),
        matching_result=matching_result,
    )


def cancel_purchase_reconciliation(purchase_invoice_id: str) -> None:
    """Marca como canceladas las conciliaciones asociadas a una factura."""

    reconciliations = (
        database.session.execute(
            select(PurchaseReconciliation)
            .filter_by(purchase_invoice_id=purchase_invoice_id)
            .where(PurchaseReconciliation.status != "cancelled")
        )
        .scalars()
        .all()
    )
    for reconciliation in reconciliations:
        reconciliation.status = "cancelled"
        for item in (
            database.session.execute(
                select(PurchaseReconciliationItem).filter_by(purchase_reconciliation_id=reconciliation.id)
            )
            .scalars()
            .all()
        ):
            item.status = "cancelled"

        emit_economic_event(
            event_type=EventType.MATCH_CANCELLED,
            company=str(reconciliation.company),
            document_type="purchase_reconciliation",
            document_id=reconciliation.id,
            payload={"purchase_invoice_id": purchase_invoice_id},
        )


def get_purchase_reconciliation_pending(company: str, as_of_date: date | None = None) -> list[PurchasePendingRow]:
    """Devuelve saldos pendientes de conciliacion por linea de recepcion."""

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

    rows: list[PurchasePendingRow] = []
    for receipt, item in database.session.execute(query).all():
        item_qty = _line_qty(item)
        item_amount = _line_amount(item)
        pending_qty = item_qty - _matched_qty_for_receipt_item(item.id)
        pending_amount = item_amount - _matched_amount_for_receipt_item(item.id)
        if pending_qty <= 0 and pending_amount <= 0:
            continue
        rows.append(
            PurchasePendingRow(
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
