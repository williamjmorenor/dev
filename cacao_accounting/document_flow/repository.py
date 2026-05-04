# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Consultas para el motor de flujo documental."""

from decimal import Decimal
from typing import Any

from cacao_accounting.database import DocumentRelation, database
from cacao_accounting.document_flow.registry import DocumentType, get_document_type, normalize_doctype


def decimal_or_zero(value: Any) -> Decimal:
    """Convierte valores numericos de SQLAlchemy/formularios a Decimal."""

    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def get_document(doctype: str, document_id: str) -> Any | None:
    """Obtiene un documento por tipo e id."""

    spec = get_document_type(doctype)
    return database.session.get(spec.header_model, document_id)


def get_document_company(doctype: str, document_id: str) -> str | None:
    """Obtiene la compania del documento."""

    document = get_document(doctype, document_id)
    return getattr(document, "company", None) if document else None


def get_document_items(doctype: str, document_id: str) -> list[Any]:
    """Devuelve las lineas de un documento."""

    spec = get_document_type(doctype)
    parent_column = getattr(spec.item_model, spec.parent_field)
    return list(
        database.session.execute(
            database.select(spec.item_model).where(parent_column == document_id).order_by(spec.item_model.created)
        ).scalars()
    )


def get_document_item(doctype: str, item_id: str) -> Any | None:
    """Obtiene una linea por tipo documental."""

    spec = get_document_type(doctype)
    return database.session.get(spec.item_model, item_id)


def get_item_parent_id(spec: DocumentType, item: Any) -> str:
    """Devuelve el id del header al que pertenece una linea."""

    return str(getattr(item, spec.parent_field))


def iter_active_relations_for_source(
    source_type: str,
    source_id: str,
    source_item_id: str,
    target_type: str | None = None,
) -> list[DocumentRelation]:
    """Devuelve relaciones cuyo target no esta cancelado."""

    source_key = normalize_doctype(source_type)
    target_key = normalize_doctype(target_type) if target_type else None
    query = database.select(DocumentRelation).filter_by(
        source_type=source_key,
        source_id=source_id,
        source_item_id=source_item_id,
    )
    if target_key:
        query = query.filter_by(target_type=target_key)

    active: list[DocumentRelation] = []
    relations = database.session.execute(query).scalars().all()
    for relation in relations:
        target = get_document(relation.target_type, relation.target_id)
        if target and getattr(target, "docstatus", 0) != 2:
            active.append(relation)
    return active


def consumed_qty_for_source(
    source_type: str,
    source_id: str,
    source_item_id: str,
    target_type: str | None = None,
) -> Decimal:
    """Suma la cantidad consumida por relaciones activas."""

    return sum(
        (
            decimal_or_zero(relation.qty)
            for relation in iter_active_relations_for_source(source_type, source_id, source_item_id, target_type)
        ),
        Decimal("0"),
    )


def save_relation(relation: DocumentRelation) -> DocumentRelation:
    """Agrega una relacion a la sesion actual."""

    database.session.add(relation)
    return relation
