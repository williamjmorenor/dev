# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Trazabilidad documental upstream/downstream."""

from __future__ import annotations

from typing import Any

from cacao_accounting.database import DocumentRelation, database
from cacao_accounting.document_flow.registry import normalize_doctype
from cacao_accounting.document_flow.repository import get_document
from cacao_accounting.document_flow.status import document_status_payload


def _document_payload(document_type: str, document_id: str) -> dict[str, Any]:
    """Serializa datos minimos de un documento para arboles de flujo."""

    doctype = normalize_doctype(document_type)
    document = get_document(doctype, document_id)
    return {
        "document_type": doctype,
        "document_id": document_id,
        "document_no": getattr(document, "document_no", None) or document_id,
        "company": getattr(document, "company", None),
        "status": document_status_payload(doctype, document_id) if document else None,
    }


def document_flow_tree(document_type: str, document_id: str) -> dict[str, Any]:
    """Construye una vista compacta de relaciones documentales."""

    doctype = normalize_doctype(document_type)
    upstream_rows = (
        database.session.execute(
            database.select(DocumentRelation)
            .filter_by(target_type=doctype, target_id=document_id)
            .order_by(DocumentRelation.created)
        )
        .scalars()
        .all()
    )
    downstream_rows = (
        database.session.execute(
            database.select(DocumentRelation)
            .filter_by(source_type=doctype, source_id=document_id)
            .order_by(DocumentRelation.created)
        )
        .scalars()
        .all()
    )
    return {
        "document": _document_payload(doctype, document_id),
        "upstream": [_relation_payload(row, upstream=True) for row in upstream_rows],
        "downstream": [_relation_payload(row, upstream=False) for row in downstream_rows],
    }


def _relation_payload(relation: DocumentRelation, upstream: bool) -> dict[str, Any]:
    """Serializa una relacion de flujo."""

    related_type = relation.source_type if upstream else relation.target_type
    related_id = relation.source_id if upstream else relation.target_id
    return {
        "relation_id": relation.id,
        "relation_type": relation.relation_type,
        "status": relation.status,
        "qty": float(relation.qty or 0),
        "uom": relation.uom,
        "document": _document_payload(related_type, related_id),
    }
