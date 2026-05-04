# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Pruebas del motor de relaciones documentales."""

from datetime import date
from decimal import Decimal

import pytest

from cacao_accounting import create_app
from cacao_accounting.config import configuracion


@pytest.fixture()
def app_ctx():
    """Aplicacion aislada con base SQLite en memoria."""

    app = create_app({**configuracion, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        from cacao_accounting.database import database

        database.create_all()
        yield app


def _seed_purchase_order(app_ctx):
    from cacao_accounting.database import Entity, Item, PurchaseOrder, PurchaseOrderItem, UOM, database

    entity = Entity(code="cacao", name="Cacao", company_name="Cacao", tax_id="J0001", currency="NIO")
    uom = UOM(code="UND", name="Unidad")
    item = Item(code="ART-001", name="Chocolate", item_type="goods", is_stock_item=True, default_uom="UND")
    order = PurchaseOrder(id="PO-001", company="cacao", posting_date=date(2026, 5, 3), docstatus=1)
    order_item = PurchaseOrderItem(
        purchase_order_id="PO-001",
        item_code="ART-001",
        item_name="Chocolate",
        qty=Decimal("10"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("50"),
    )
    database.session.add_all([entity, uom, item, order, order_item])
    database.session.flush()
    return order_item


def test_document_flow_tracks_partial_pending_qty(app_ctx):
    from cacao_accounting.database import PurchaseReceipt, PurchaseReceiptItem, database
    from cacao_accounting.document_flow import create_document_relation
    from cacao_accounting.document_flow.service import get_source_items

    order_item = _seed_purchase_order(app_ctx)
    receipt = PurchaseReceipt(id="PR-001", company="cacao", posting_date=date(2026, 5, 4), docstatus=0)
    receipt_item = PurchaseReceiptItem(
        purchase_receipt_id="PR-001",
        item_code="ART-001",
        item_name="Chocolate",
        qty=Decimal("4"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("20"),
    )
    database.session.add_all([receipt, receipt_item])
    database.session.flush()

    create_document_relation(
        source_type="purchase_order",
        source_id="PO-001",
        source_item_id=order_item.id,
        target_type="purchase_receipt",
        target_id="PR-001",
        target_item_id=receipt_item.id,
        qty=Decimal("4"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("20"),
    )

    items = get_source_items("purchase_order", "PO-001", "purchase_receipt")

    assert items[0]["source_qty"] == 10
    assert items[0]["consumed_qty"] == 4
    assert items[0]["pending_qty"] == 6
    assert order_item.received_qty == Decimal("4")


def test_document_flow_blocks_overconsumption(app_ctx):
    from cacao_accounting.database import PurchaseReceipt, PurchaseReceiptItem, database
    from cacao_accounting.document_flow import DocumentFlowError, create_document_relation

    order_item = _seed_purchase_order(app_ctx)
    receipt = PurchaseReceipt(id="PR-002", company="cacao", posting_date=date(2026, 5, 4), docstatus=0)
    receipt_item = PurchaseReceiptItem(
        purchase_receipt_id="PR-002",
        item_code="ART-001",
        item_name="Chocolate",
        qty=Decimal("11"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("55"),
    )
    database.session.add_all([receipt, receipt_item])
    database.session.flush()

    with pytest.raises(DocumentFlowError) as exc_info:
        create_document_relation(
            source_type="purchase_order",
            source_id="PO-001",
            source_item_id=order_item.id,
            target_type="purchase_receipt",
            target_id="PR-002",
            target_item_id=receipt_item.id,
            qty=Decimal("11"),
            uom="UND",
            rate=Decimal("5"),
            amount=Decimal("55"),
        )

    assert exc_info.value.status_code == 409


def test_document_flow_releases_pending_qty_when_target_is_reverted(app_ctx):
    from cacao_accounting.database import DocumentRelation, PurchaseReceipt, PurchaseReceiptItem, database
    from cacao_accounting.document_flow import create_document_relation, revert_relations_for_target
    from cacao_accounting.document_flow.service import get_source_items

    order_item = _seed_purchase_order(app_ctx)
    receipt = PurchaseReceipt(id="PR-003", company="cacao", posting_date=date(2026, 5, 4), docstatus=1)
    receipt_item = PurchaseReceiptItem(
        purchase_receipt_id="PR-003",
        item_code="ART-001",
        item_name="Chocolate",
        qty=Decimal("4"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("20"),
    )
    database.session.add_all([receipt, receipt_item])
    database.session.flush()
    create_document_relation(
        source_type="purchase_order",
        source_id="PO-001",
        source_item_id=order_item.id,
        target_type="purchase_receipt",
        target_id="PR-003",
        target_item_id=receipt_item.id,
        qty=Decimal("4"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("20"),
    )

    receipt.docstatus = 2
    reverted = revert_relations_for_target("purchase_receipt", "PR-003")
    items = get_source_items("purchase_order", "PO-001", "purchase_receipt")
    relation = database.session.execute(database.select(DocumentRelation)).scalar_one()

    assert reverted == 1
    assert relation.status == "reverted"
    assert items[0]["pending_qty"] == 10
    assert order_item.received_qty == Decimal("0")


def test_document_flow_closes_manual_line_balance(app_ctx):
    from cacao_accounting.document_flow import DocumentFlowError, close_line_balance, create_document_relation
    from cacao_accounting.database import PurchaseReceipt, PurchaseReceiptItem, database
    from cacao_accounting.document_flow.service import get_source_items

    order_item = _seed_purchase_order(app_ctx)
    state = close_line_balance(
        source_type="purchase_order",
        source_id="PO-001",
        source_item_id=order_item.id,
        target_type="purchase_receipt",
        qty=Decimal("3"),
        reason="Proveedor no enviara saldo",
    )
    receipt = PurchaseReceipt(id="PR-004", company="cacao", posting_date=date(2026, 5, 4), docstatus=0)
    receipt_item = PurchaseReceiptItem(
        purchase_receipt_id="PR-004",
        item_code="ART-001",
        item_name="Chocolate",
        qty=Decimal("8"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("40"),
    )
    database.session.add_all([receipt, receipt_item])
    database.session.flush()

    with pytest.raises(DocumentFlowError):
        create_document_relation(
            source_type="purchase_order",
            source_id="PO-001",
            source_item_id=order_item.id,
            target_type="purchase_receipt",
            target_id="PR-004",
            target_item_id=receipt_item.id,
            qty=Decimal("8"),
            uom="UND",
            rate=Decimal("5"),
            amount=Decimal("40"),
        )

    items = get_source_items("purchase_order", "PO-001", "purchase_receipt")

    assert state["closed_qty"] == 3
    assert state["pending_qty"] == 7
    assert items[0]["closed_qty"] == 3
    assert items[0]["pending_qty"] == 7


def test_document_status_uses_single_operational_badge(app_ctx):
    from cacao_accounting.database import PurchaseReceipt, PurchaseReceiptItem, database
    from cacao_accounting.document_flow import close_line_balance, create_document_relation
    from cacao_accounting.document_flow.status import calculate_document_status

    order_item = _seed_purchase_order(app_ctx)

    open_status = calculate_document_status("purchase_order", "PO-001")
    assert open_status.label == "Pendiente Recibir"
    assert open_status.badge_class == "text-bg-primary"

    receipt = PurchaseReceipt(id="PR-005", company="cacao", posting_date=date(2026, 5, 4), docstatus=0)
    receipt_item = PurchaseReceiptItem(
        purchase_receipt_id="PR-005",
        item_code="ART-001",
        item_name="Chocolate",
        qty=Decimal("4"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("20"),
    )
    database.session.add_all([receipt, receipt_item])
    database.session.flush()
    create_document_relation(
        source_type="purchase_order",
        source_id="PO-001",
        source_item_id=order_item.id,
        target_type="purchase_receipt",
        target_id="PR-005",
        target_item_id=receipt_item.id,
        qty=Decimal("4"),
        uom="UND",
        rate=Decimal("5"),
        amount=Decimal("20"),
    )

    partial_status = calculate_document_status("purchase_order", "PO-001")
    assert partial_status.label == "Recibido Parcialmente"

    close_line_balance(
        source_type="purchase_order",
        source_id="PO-001",
        source_item_id=order_item.id,
        target_type="purchase_receipt",
        qty=Decimal("6"),
        reason="Cierre operacional",
    )

    billing_status = calculate_document_status("purchase_order", "PO-001")
    assert billing_status.label == "Pendiente Facturar"

    close_line_balance(
        source_type="purchase_order",
        source_id="PO-001",
        source_item_id=order_item.id,
        target_type="purchase_invoice",
        qty=Decimal("10"),
        reason="Cierre de facturacion",
    )

    completed_status = calculate_document_status("purchase_order", "PO-001")
    assert completed_status.label == "Completado"
    assert completed_status.badge_class == "text-bg-success"
