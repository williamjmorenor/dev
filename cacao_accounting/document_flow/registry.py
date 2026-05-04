# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Registro de documentos y relaciones permitidas."""

from dataclasses import dataclass
from typing import Any

from cacao_accounting.database import (
    DeliveryNote,
    DeliveryNoteItem,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    SalesInvoice,
    SalesInvoiceItem,
    SalesOrder,
    SalesOrderItem,
)


@dataclass(frozen=True)
class DocumentType:
    """Contrato minimo para consultar un documento header + items."""

    key: str
    header_model: Any
    item_model: Any
    parent_field: str
    party_field: str | None = None


@dataclass(frozen=True)
class FlowSpec:
    """Relacion permitida entre dos tipos documentales."""

    source_type: str
    target_type: str
    relation_type: str


DOCUMENT_TYPES: dict[str, DocumentType] = {
    "purchase_order": DocumentType(
        key="purchase_order",
        header_model=PurchaseOrder,
        item_model=PurchaseOrderItem,
        parent_field="purchase_order_id",
        party_field="supplier_id",
    ),
    "purchase_receipt": DocumentType(
        key="purchase_receipt",
        header_model=PurchaseReceipt,
        item_model=PurchaseReceiptItem,
        parent_field="purchase_receipt_id",
        party_field="supplier_id",
    ),
    "purchase_invoice": DocumentType(
        key="purchase_invoice",
        header_model=PurchaseInvoice,
        item_model=PurchaseInvoiceItem,
        parent_field="purchase_invoice_id",
        party_field="supplier_id",
    ),
    "sales_order": DocumentType(
        key="sales_order",
        header_model=SalesOrder,
        item_model=SalesOrderItem,
        parent_field="sales_order_id",
        party_field="customer_id",
    ),
    "delivery_note": DocumentType(
        key="delivery_note",
        header_model=DeliveryNote,
        item_model=DeliveryNoteItem,
        parent_field="delivery_note_id",
        party_field="customer_id",
    ),
    "sales_invoice": DocumentType(
        key="sales_invoice",
        header_model=SalesInvoice,
        item_model=SalesInvoiceItem,
        parent_field="sales_invoice_id",
        party_field="customer_id",
    ),
}


ALLOWED_FLOWS: dict[tuple[str, str], FlowSpec] = {
    ("purchase_order", "purchase_receipt"): FlowSpec("purchase_order", "purchase_receipt", "receipt"),
    ("purchase_order", "purchase_invoice"): FlowSpec("purchase_order", "purchase_invoice", "billing"),
    ("purchase_receipt", "purchase_invoice"): FlowSpec("purchase_receipt", "purchase_invoice", "billing"),
    ("purchase_invoice", "purchase_invoice"): FlowSpec("purchase_invoice", "purchase_invoice", "return"),
    ("sales_request", "sales_quotation"): FlowSpec("sales_request", "sales_quotation", "quotation"),
    ("sales_quotation", "sales_order"): FlowSpec("sales_quotation", "sales_order", "order"),
    ("sales_order", "delivery_note"): FlowSpec("sales_order", "delivery_note", "delivery"),
    ("sales_order", "sales_invoice"): FlowSpec("sales_order", "sales_invoice", "billing"),
    ("delivery_note", "sales_invoice"): FlowSpec("delivery_note", "sales_invoice", "billing"),
    ("sales_invoice", "sales_invoice"): FlowSpec("sales_invoice", "sales_invoice", "return"),
}


def normalize_doctype(value: str) -> str:
    """Normaliza nombres recibidos desde URLs o formularios."""

    return value.strip().lower().replace("-", "_").replace(" ", "_")


def get_document_type(value: str) -> DocumentType:
    """Devuelve el contrato de un tipo documental conocido."""

    key = normalize_doctype(value)
    return DOCUMENT_TYPES[key]


def get_flow(source_type: str, target_type: str) -> FlowSpec:
    """Devuelve la relacion permitida entre dos tipos documentales."""

    return ALLOWED_FLOWS[(normalize_doctype(source_type), normalize_doctype(target_type))]


def is_allowed_flow(source_type: str, target_type: str) -> bool:
    """Indica si existe una relacion activa entre source y target."""

    return (normalize_doctype(source_type), normalize_doctype(target_type)) in ALLOWED_FLOWS
