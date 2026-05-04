# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Servicios de flujo documental y parcialidades."""

from decimal import Decimal
from typing import Any

from cacao_accounting.database import DocumentRelation, database
from cacao_accounting.document_flow.registry import get_document_type, get_flow, is_allowed_flow, normalize_doctype
from cacao_accounting.document_flow.repository import (
    consumed_qty_for_source,
    decimal_or_zero,
    get_document,
    get_document_company,
    get_document_item,
    get_document_items,
    get_item_parent_id,
    save_relation,
)


class DocumentFlowError(ValueError):
    """Error controlado del motor de flujo documental."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _to_json_number(value: Any) -> float:
    """Convierte Decimal/None a float para JSON y templates."""

    return float(decimal_or_zero(value))


def _line_payload(source_type: str, source_id: str, item: Any, target_type: str | None = None) -> dict[str, Any]:
    """Construye la respuesta estandar para una linea origen."""

    qty = decimal_or_zero(getattr(item, "qty", 0))
    consumed = consumed_qty_for_source(source_type, source_id, item.id, target_type)
    pending = qty - consumed
    if pending < Decimal("0"):
        pending = Decimal("0")
    rate = decimal_or_zero(getattr(item, "rate", 0))
    amount = pending * rate
    return {
        "source_type": normalize_doctype(source_type),
        "source_id": source_id,
        "source_item_id": item.id,
        "item_code": getattr(item, "item_code", ""),
        "item_name": getattr(item, "item_name", "") or "",
        "source_qty": _to_json_number(qty),
        "consumed_qty": _to_json_number(consumed),
        "pending_qty": _to_json_number(pending),
        "qty": _to_json_number(pending),
        "uom": getattr(item, "uom", "") or "",
        "rate": _to_json_number(rate),
        "amount": _to_json_number(amount),
    }


def get_source_items(source_type: str, source_id: str, target_type: str | None = None) -> list[dict[str, Any]]:
    """Devuelve lineas disponibles desde un documento origen."""

    source_key = normalize_doctype(source_type)
    target_key = normalize_doctype(target_type) if target_type else None
    if target_key and not is_allowed_flow(source_key, target_key):
        raise DocumentFlowError(f"Relacion no permitida: {source_key} -> {target_key}", 400)
    source = get_document(source_key, source_id)
    if not source:
        raise DocumentFlowError("Documento origen no encontrado.", 404)
    if getattr(source, "docstatus", 0) == 2:
        return []
    source_items = get_document_items(source_key, source_id)
    return [
        payload
        for payload in (_line_payload(source_key, source_id, item, target_key) for item in source_items)
        if decimal_or_zero(payload["pending_qty"]) > 0
    ]


def get_document_flow_items(target_type: str, source_values: list[str]) -> list[dict[str, Any]]:
    """Devuelve lineas pendientes para uno o mas documentos origen."""

    target_key = normalize_doctype(target_type)
    items: list[dict[str, Any]] = []
    for value in source_values:
        if ":" not in value:
            raise DocumentFlowError("El parametro source debe usar formato doctype:id.", 400)
        source_type, source_id = value.split(":", 1)
        items.extend(get_source_items(source_type, source_id, target_key))
    return items


def pending_qty(source_type: str, source_id: str, source_item_id: str, target_type: str) -> Decimal:
    """Calcula la cantidad pendiente para una linea origen hacia un target."""

    source_item = get_document_item(source_type, source_item_id)
    if not source_item:
        raise DocumentFlowError("Linea origen no encontrada.", 404)
    qty = decimal_or_zero(getattr(source_item, "qty", 0))
    consumed = consumed_qty_for_source(source_type, source_id, source_item_id, target_type)
    pending = qty - consumed
    return pending if pending > 0 else Decimal("0")


def _assert_same_company(source_type: str, source_id: str, target_type: str, target_id: str) -> None:
    """Valida aislamiento por compania."""

    source_company = get_document_company(source_type, source_id)
    target_company = get_document_company(target_type, target_id)
    if source_company and target_company and source_company != target_company:
        raise DocumentFlowError("El documento origen y destino pertenecen a companias distintas.", 409)


def _update_source_cache(source_type: str, source_id: str, source_item_id: str, target_type: str) -> None:
    """Actualiza campos cache de consumo cuando existen en la linea origen."""

    source_key = normalize_doctype(source_type)
    target_key = normalize_doctype(target_type)
    source_item = get_document_item(source_key, source_item_id)
    if not source_item:
        return
    consumed = consumed_qty_for_source(source_key, source_id, source_item_id, target_key)
    if source_key == "purchase_order" and target_key == "purchase_receipt":
        source_item.received_qty = consumed
    elif source_key == "purchase_order" and target_key == "purchase_invoice":
        source_item.billed_qty = consumed
    elif source_key == "sales_order" and target_key == "delivery_note":
        source_item.delivered_qty = consumed
    elif source_key == "sales_order" and target_key == "sales_invoice":
        source_item.billed_qty = consumed


def refresh_source_caches_for_target(target_type: str, target_id: str) -> None:
    """Recalcula caches de origen afectados por un documento destino."""

    target_key = normalize_doctype(target_type)
    relations = database.session.execute(
        database.select(DocumentRelation).filter_by(target_type=target_key, target_id=target_id)
    ).scalars()
    for relation in relations:
        _update_source_cache(relation.source_type, relation.source_id, relation.source_item_id, target_key)


def create_document_relation(
    *,
    source_type: str,
    source_id: str,
    source_item_id: str,
    target_type: str,
    target_id: str,
    target_item_id: str,
    qty: Any,
    uom: str | None = None,
    rate: Any = None,
    amount: Any = None,
) -> DocumentRelation:
    """Crea una relacion entre lineas validando parcialidad y compania."""

    source_key = normalize_doctype(source_type)
    target_key = normalize_doctype(target_type)
    if not is_allowed_flow(source_key, target_key):
        raise DocumentFlowError(f"Relacion no permitida: {source_key} -> {target_key}", 400)

    source_spec = get_document_type(source_key)
    source_item = get_document_item(source_key, source_item_id)
    target_item = get_document_item(target_key, target_item_id)
    if not source_item or not target_item:
        raise DocumentFlowError("Linea origen o destino no encontrada.", 404)

    real_source_id = get_item_parent_id(source_spec, source_item)
    if real_source_id != source_id:
        raise DocumentFlowError("La linea origen no pertenece al documento indicado.", 409)
    _assert_same_company(source_key, source_id, target_key, target_id)

    qty_decimal = decimal_or_zero(qty)
    if qty_decimal <= 0:
        raise DocumentFlowError("La cantidad relacionada debe ser mayor que cero.", 409)
    available = pending_qty(source_key, source_id, source_item_id, target_key)
    if qty_decimal > available:
        raise DocumentFlowError("La cantidad relacionada excede el pendiente disponible.", 409)

    flow = get_flow(source_key, target_key)
    relation = DocumentRelation(
        source_type=source_key,
        source_id=source_id,
        source_item_id=source_item_id,
        target_type=target_key,
        target_id=target_id,
        target_item_id=target_item_id,
        qty=qty_decimal,
        uom=uom or getattr(target_item, "uom", None),
        rate=decimal_or_zero(rate),
        amount=decimal_or_zero(amount),
        relation_type=flow.relation_type,
    )
    save_relation(relation)
    _update_source_cache(source_key, source_id, source_item_id, target_key)
    return relation
