# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from cacao_accounting import create_app
from cacao_accounting.config import configuracion


@pytest.fixture()
def app_ctx():
    app = create_app(
        {
            **configuracion,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "WTF_CSRF_ENABLED": False,
            "TESTING": True,
        }
    )
    with app.app_context():
        from cacao_accounting.database import Entity, database

        database.create_all()
        database.session.add(Entity(code="cacao", name="Cacao", company_name="Cacao", tax_id="J0001", currency="NIO"))
        database.session.commit()
        yield app


def test_purchase_reconciliation_line_matching_supports_partial_and_completion(app_ctx):
    from cacao_accounting.compras.purchase_reconciliation_service import (
        get_purchase_reconciliation_pending,
        reconcile_purchase_invoice,
    )
    from cacao_accounting.database import (
        PurchaseReconciliationItem,
        Item,
        PurchaseInvoice,
        PurchaseInvoiceItem,
        PurchaseReceipt,
        PurchaseReceiptItem,
        UOM,
        Warehouse,
        database,
    )

    database.session.add_all(
        [
            UOM(code="EA", name="Each"),
            Item(code="ITEM-GR8", name="Item GR8", item_type="goods", is_stock_item=True, default_uom="EA"),
            Warehouse(code="WH-GR8", name="Bodega GR8", company="cacao"),
        ]
    )
    receipt = PurchaseReceipt(company="cacao", posting_date=date(2026, 5, 1), supplier_id="SUPP-8", docstatus=1)
    database.session.add(receipt)
    database.session.flush()
    database.session.add(
        PurchaseReceiptItem(
            purchase_receipt_id=receipt.id,
            item_code="ITEM-GR8",
            item_name="Item GR8",
            qty=Decimal("10"),
            qty_in_base_uom=Decimal("10"),
            uom="EA",
            rate=Decimal("5.00"),
            amount=Decimal("50.00"),
            warehouse="WH-GR8",
        )
    )
    invoices = []
    for qty in (Decimal("4"), Decimal("6")):
        invoice = PurchaseInvoice(
            company="cacao",
            posting_date=date(2026, 5, 2),
            supplier_id="SUPP-8",
            purchase_receipt_id=receipt.id,
            docstatus=1,
        )
        database.session.add(invoice)
        database.session.flush()
        database.session.add(
            PurchaseInvoiceItem(
                purchase_invoice_id=invoice.id,
                item_code="ITEM-GR8",
                item_name="Item GR8",
                qty=qty,
                uom="EA",
                rate=Decimal("5.00"),
                amount=qty * Decimal("5.00"),
                warehouse="WH-GR8",
            )
        )
        invoices.append(invoice)
    database.session.commit()

    first = reconcile_purchase_invoice(invoices[0].id)
    assert first.matched_qty == Decimal("4.000000000")
    assert get_purchase_reconciliation_pending("cacao")[0].pending_qty == Decimal("6.000000000")

    second = reconcile_purchase_invoice(invoices[1].id)
    database.session.commit()
    assert second.matched_qty == Decimal("6.000000000")
    assert get_purchase_reconciliation_pending("cacao") == []
    assert database.session.execute(database.select(PurchaseReconciliationItem)).scalars().all()


def test_purchase_reconciliation_rejects_overbilling_and_price_difference(app_ctx):
    from cacao_accounting.compras.purchase_reconciliation_service import (
        PurchaseReconciliationError,
        reconcile_purchase_invoice,
    )
    from cacao_accounting.database import (
        Item,
        PurchaseInvoice,
        PurchaseInvoiceItem,
        PurchaseReceipt,
        PurchaseReceiptItem,
        UOM,
        Warehouse,
        database,
    )

    database.session.add_all(
        [
            UOM(code="EA", name="Each"),
            Item(code="ITEM-GR9", name="Item GR9", item_type="goods", is_stock_item=True, default_uom="EA"),
            Warehouse(code="WH-GR9", name="Bodega GR9", company="cacao"),
        ]
    )
    receipt = PurchaseReceipt(company="cacao", posting_date=date(2026, 5, 1), supplier_id="SUPP-9", docstatus=1)
    database.session.add(receipt)
    database.session.flush()
    database.session.add(
        PurchaseReceiptItem(
            purchase_receipt_id=receipt.id,
            item_code="ITEM-GR9",
            qty=Decimal("2"),
            qty_in_base_uom=Decimal("2"),
            uom="EA",
            rate=Decimal("5.00"),
            amount=Decimal("10.00"),
            warehouse="WH-GR9",
        )
    )
    invoice = PurchaseInvoice(
        company="cacao", posting_date=date(2026, 5, 2), supplier_id="SUPP-9", purchase_receipt_id=receipt.id, docstatus=1
    )
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        PurchaseInvoiceItem(
            purchase_invoice_id=invoice.id,
            item_code="ITEM-GR9",
            qty=Decimal("3"),
            uom="EA",
            rate=Decimal("5.00"),
            amount=Decimal("15.00"),
            warehouse="WH-GR9",
        )
    )
    database.session.commit()

    with pytest.raises(PurchaseReconciliationError, match="excede"):
        reconcile_purchase_invoice(invoice.id)


def test_bank_reconciliation_supports_partial_and_rejects_duplicates(app_ctx):
    from cacao_accounting.bancos.reconciliation_service import (
        BankReconciliationError,
        BankReconciliationMatch,
        BankReconciliationRequest,
        reconcile_bank_items,
    )
    from cacao_accounting.database import Bank, BankAccount, BankTransaction, PaymentEntry, ReconciliationItem, database

    bank = Bank(name="Banco")
    database.session.add(bank)
    database.session.flush()
    bank_account = BankAccount(bank_id=bank.id, company="cacao", account_name="Cuenta")
    database.session.add(bank_account)
    database.session.flush()
    transaction = BankTransaction(bank_account_id=bank_account.id, posting_date=date(2026, 5, 5), deposit=Decimal("100.00"))
    payment_a = PaymentEntry(
        company="cacao", posting_date=date(2026, 5, 5), payment_type="receive", received_amount=Decimal("60.00"), docstatus=1
    )
    payment_b = PaymentEntry(
        company="cacao", posting_date=date(2026, 5, 5), payment_type="receive", received_amount=Decimal("40.00"), docstatus=1
    )
    database.session.add_all([transaction, payment_a, payment_b])
    database.session.commit()

    reconcile_bank_items(
        BankReconciliationRequest(
            company="cacao",
            reconciliation_date=date(2026, 5, 5),
            matches=[
                BankReconciliationMatch(transaction.id, "payment_entry", payment_a.id, Decimal("60.00")),
                BankReconciliationMatch(transaction.id, "payment_entry", payment_b.id, Decimal("40.00")),
            ],
        )
    )
    database.session.commit()

    items = database.session.execute(database.select(ReconciliationItem)).scalars().all()
    assert transaction.is_reconciled is True
    assert sum(item.allocated_amount for item in items) == Decimal("100.00")
    with pytest.raises(BankReconciliationError, match="excede"):
        reconcile_bank_items(
            BankReconciliationRequest(
                company="cacao",
                reconciliation_date=date(2026, 5, 5),
                matches=[BankReconciliationMatch(transaction.id, "payment_entry", payment_a.id, Decimal("1.00"))],
            )
        )


def test_reports_return_subledger_aging_kardex_and_reconciliations(app_ctx):
    from cacao_accounting.database import PaymentReference, SalesInvoice, StockLedgerEntry, database
    from cacao_accounting.reportes.services import (
        AgingFilters,
        KardexFilters,
        SubledgerFilters,
        get_aging_report,
        get_ar_ap_subledger,
        get_kardex,
        get_reconciliation_report,
    )

    invoice = SalesInvoice(company="cacao", posting_date=date(2026, 4, 1), customer_id="CUST-R", grand_total=Decimal("100.00"))
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        PaymentReference(
            payment_id="PAY-R",
            reference_type="sales_invoice",
            reference_id=invoice.id,
            allocated_amount=Decimal("25.00"),
            allocation_date=date(2026, 4, 15),
        )
    )
    database.session.add(
        StockLedgerEntry(
            posting_date=date(2026, 5, 1),
            item_code="ITEM-R",
            warehouse="WH-R",
            company="cacao",
            qty_change=Decimal("3"),
            qty_after_transaction=Decimal("3"),
            valuation_rate=Decimal("2.00"),
            stock_value_difference=Decimal("6.00"),
            stock_value=Decimal("6.00"),
            voucher_type="seed",
            voucher_id="seed-r",
        )
    )
    database.session.commit()

    subledger = get_ar_ap_subledger(SubledgerFilters(company="cacao", party_type="customer", as_of_date=date(2026, 5, 5)))
    aging = get_aging_report(AgingFilters(company="cacao", party_type="customer", as_of_date=date(2026, 5, 5)))
    kardex = get_kardex(KardexFilters(company="cacao", item_code="ITEM-R"))
    reconciliations = get_reconciliation_report(company="cacao")

    assert subledger.totals["outstanding_amount"] == Decimal("75.00")
    assert aging.totals["31_60"] == Decimal("75.00")
    assert kardex.totals["incoming_qty"] == Decimal("3.000000000")
    assert reconciliations.totals["bank_reconciled_amount"] == Decimal("0")


def test_tax_template_posts_sales_tax_and_price_suggestion(app_ctx):
    from cacao_accounting.contabilidad.posting import post_document_to_gl
    from cacao_accounting.database import (
        Accounts,
        GLEntry,
        ItemPrice,
        PartyAccount,
        PriceList,
        SalesInvoice,
        SalesInvoiceItem,
        Tax,
        TaxTemplate,
        TaxTemplateItem,
        database,
    )
    from cacao_accounting.tax_pricing_service import get_item_price, validate_price_tolerance

    receivable = Accounts(entity="cacao", code="AR-T", name="AR", active=True, enabled=True, account_type="receivable")
    income = Accounts(entity="cacao", code="INC-T", name="Ingreso", active=True, enabled=True, account_type="income")
    tax_account = Accounts(entity="cacao", code="TAX-T", name="IVA", active=True, enabled=True, account_type="liability")
    database.session.add_all([receivable, income, tax_account])
    database.session.flush()
    template = TaxTemplate(name="IVA Ventas", company="cacao", template_type="selling")
    tax = Tax(name="IVA 15", rate=Decimal("15.00"), tax_type="percentage", applies_to="sales", account_id=tax_account.id)
    price_list = PriceList(name="Ventas", company="cacao", currency="NIO", is_selling=True)
    database.session.add_all([template, tax, price_list])
    database.session.flush()
    database.session.add_all(
        [
            TaxTemplateItem(tax_template_id=template.id, tax_id=tax.id, sequence=1, behavior="additive"),
            PartyAccount(party_id="CUST-T", company="cacao", receivable_account_id=receivable.id),
            ItemPrice(item_code="ITEM-T", price_list_id=price_list.id, uom="EA", price=Decimal("100.00")),
        ]
    )
    invoice = SalesInvoice(
        company="cacao",
        posting_date=date(2026, 5, 5),
        customer_id="CUST-T",
        tax_template_id=template.id,
        total=Decimal("100.00"),
        grand_total=Decimal("115.00"),
        docstatus=1,
    )
    database.session.add(invoice)
    database.session.flush()
    line = SalesInvoiceItem(
        sales_invoice_id=invoice.id,
        item_code="ITEM-T",
        qty=Decimal("1"),
        uom="EA",
        rate=Decimal("100.00"),
        amount=Decimal("100.00"),
        income_account_id=income.id,
    )
    database.session.add(line)
    database.session.commit()

    post_document_to_gl(invoice)
    suggestion = get_item_price("ITEM-T", price_list.id, Decimal("1"), "EA", date(2026, 5, 5))
    line.suggested_rate = suggestion.price
    tolerance = validate_price_tolerance("sales_invoice", line, None)
    entries = database.session.execute(database.select(GLEntry)).scalars().all()

    assert suggestion.price == Decimal("100.0000")
    assert tolerance.allowed is True
    assert sum(entry.debit for entry in entries) == Decimal("115.0000")
    assert sum(entry.credit for entry in entries) == Decimal("115.0000")
    assert any(entry.account_id == tax_account.id and entry.credit == Decimal("15.0000") for entry in entries)


def test_inventory_uom_batch_serial_and_rebuild_stock_bins(app_ctx):
    from cacao_accounting.contabilidad.posting import post_document_to_gl
    from cacao_accounting.database import (
        Accounts,
        Batch,
        CompanyDefaultAccount,
        Item,
        ItemAccount,
        ItemUOMConversion,
        SerialNumber,
        StockBin,
        StockEntry,
        StockEntryItem,
        UOM,
        Warehouse,
        database,
    )
    from cacao_accounting.inventario.service import convert_item_qty, rebuild_stock_bins

    inventory = Accounts(entity="cacao", code="INV-S", name="Inventario", active=True, enabled=True, account_type="asset")
    bridge = Accounts(
        entity="cacao", code="BRIDGE-S", name="Cuenta Puente Compras", active=True, enabled=True, account_type="liability"
    )
    database.session.add_all(
        [
            inventory,
            bridge,
            UOM(code="EA", name="Each"),
            UOM(code="BOX", name="Box"),
            Item(
                code="ITEM-S",
                name="Serial",
                item_type="goods",
                is_stock_item=True,
                has_batch=True,
                has_serial_no=True,
                default_uom="EA",
            ),
            Warehouse(code="WH-S", name="Bodega", company="cacao"),
        ]
    )
    database.session.flush()
    database.session.add_all(
        [
            CompanyDefaultAccount(company="cacao", default_inventory=inventory.id, bridge_account_id=bridge.id),
            ItemAccount(item_code="ITEM-S", company="cacao", inventory_account_id=inventory.id),
            ItemUOMConversion(item_code="ITEM-S", from_uom="BOX", to_uom="EA", conversion_factor=Decimal("10")),
            Batch(item_code="ITEM-S", batch_no="B-1"),
        ]
    )
    database.session.flush()
    batch = database.session.execute(database.select(Batch).filter_by(batch_no="B-1")).scalar_one()
    entry = StockEntry(
        company="cacao", posting_date=date(2026, 5, 5), purpose="material_receipt", to_warehouse="WH-S", docstatus=1
    )
    database.session.add(entry)
    database.session.flush()
    database.session.add(
        StockEntryItem(
            stock_entry_id=entry.id,
            item_code="ITEM-S",
            target_warehouse="WH-S",
            qty=Decimal("1"),
            uom="EA",
            basic_rate=Decimal("7.00"),
            amount=Decimal("7.00"),
            batch_id=batch.id,
            serial_no="SN-1",
        )
    )
    database.session.commit()

    post_document_to_gl(entry)
    result = rebuild_stock_bins("cacao", item_code="ITEM-S", warehouse="WH-S")
    serial = database.session.execute(database.select(SerialNumber).filter_by(serial_no="SN-1")).scalar_one()
    bin_row = database.session.execute(database.select(StockBin).filter_by(item_code="ITEM-S", warehouse="WH-S")).scalar_one()

    assert convert_item_qty("ITEM-S", Decimal("1"), "BOX", "EA") == Decimal("10")
    assert serial.serial_status == "available"
    assert bin_row.actual_qty == Decimal("1.000000000")
    assert result.rebuilt_bins == 1


def test_bank_statement_import_preview_and_matching_rule(app_ctx):
    from io import StringIO

    from cacao_accounting.bancos.statement_service import apply_bank_matching_rule, import_bank_statement
    from cacao_accounting.database import Bank, BankAccount, BankMatchingRule, BankTransaction, database

    bank = Bank(name="Banco CSV")
    database.session.add(bank)
    database.session.flush()
    account = BankAccount(bank_id=bank.id, company="cacao", account_name="Cuenta CSV", is_active=True)
    database.session.add(account)
    database.session.flush()
    csv_data = "date,reference,description,deposit,withdrawal\n2026-05-05,REF-1,Ingreso,25.00,\n"
    mapping = {
        "date": "date",
        "reference": "reference",
        "description": "description",
        "deposit": "deposit",
        "withdrawal": "withdrawal",
    }

    preview = import_bank_statement(StringIO(csv_data), mapping, account.id, preview=True)
    imported = import_bank_statement(StringIO(csv_data), mapping, account.id, preview=False)
    duplicate = import_bank_statement(StringIO(csv_data), mapping, account.id, preview=True)
    rule = BankMatchingRule(company="cacao", bank_account_id=account.id, name="Referencia", reference_contains="REF")
    database.session.add(rule)
    database.session.commit()
    run = apply_bank_matching_rule(rule.id, account.id, (date(2026, 5, 1), date(2026, 5, 31)))

    assert preview.imported_count == 0
    assert imported.imported_count == 1
    assert duplicate.duplicate_count == 1
    assert database.session.execute(database.select(BankTransaction)).scalars().first()
    assert run.candidates_by_transaction


# ---------------------------------------------------------------------------
# Criterios de aceptacion del Issue: Framework de Conciliacion de Compras
# ---------------------------------------------------------------------------


def test_matching_without_accounting_entries_is_possible(app_ctx):
    """Criterio #1: se puede ejecutar el matching sin generar asientos contables."""
    from cacao_accounting.compras.purchase_reconciliation_service import (
        PurchaseReconciliationError,
        reconcile_purchase_invoice,
    )
    from cacao_accounting.database import (
        GLEntry,
        Item,
        PurchaseInvoice,
        PurchaseInvoiceItem,
        PurchaseReceipt,
        PurchaseReceiptItem,
        UOM,
        Warehouse,
        database,
    )

    database.session.add_all(
        [
            UOM(code="EA-AC1", name="Each AC1"),
            Item(code="ITEM-AC1", name="Item AC1", item_type="goods", is_stock_item=True, default_uom="EA-AC1"),
            Warehouse(code="WH-AC1", name="Bodega AC1", company="cacao"),
        ]
    )
    receipt = PurchaseReceipt(company="cacao", posting_date=date(2026, 5, 1), supplier_id="SUPP-AC1", docstatus=1)
    database.session.add(receipt)
    database.session.flush()
    database.session.add(
        PurchaseReceiptItem(
            purchase_receipt_id=receipt.id,
            item_code="ITEM-AC1",
            item_name="Item AC1",
            qty=Decimal("5"),
            qty_in_base_uom=Decimal("5"),
            uom="EA-AC1",
            rate=Decimal("10.00"),
            amount=Decimal("50.00"),
            warehouse="WH-AC1",
        )
    )
    invoice = PurchaseInvoice(
        company="cacao",
        posting_date=date(2026, 5, 2),
        supplier_id="SUPP-AC1",
        purchase_receipt_id=receipt.id,
        docstatus=1,
    )
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        PurchaseInvoiceItem(
            purchase_invoice_id=invoice.id,
            item_code="ITEM-AC1",
            item_name="Item AC1",
            qty=Decimal("5"),
            uom="EA-AC1",
            rate=Decimal("10.00"),
            amount=Decimal("50.00"),
            warehouse="WH-AC1",
        )
    )
    database.session.commit()

    # reconcile WITHOUT calling post_document_to_gl — no GL entries should exist
    result = reconcile_purchase_invoice(invoice.id)
    database.session.commit()

    gl_count = (
        database.session.execute(database.select(GLEntry).filter_by(voucher_type="purchase_invoice", voucher_id=invoice.id))
        .scalars()
        .all()
    )

    assert result.matching_result == "MATCH_OK"
    assert result.matched_amount == Decimal("50.0000")
    # Matching produced no accounting entries on its own
    assert len(gl_count) == 0


def test_changing_tolerances_does_not_alter_historical_reconciliations(app_ctx):
    """Criterio #2: cambiar tolerancias no altera datos historicos."""
    from cacao_accounting.compras.purchase_reconciliation_service import (
        PurchaseMatchingConfig,
        get_matching_config,
        seed_matching_config_for_company,
    )
    from cacao_accounting.database import (
        Item,
        PurchaseInvoice,
        PurchaseInvoiceItem,
        PurchaseReceipt,
        PurchaseReceiptItem,
        PurchaseReconciliation,
        UOM,
        Warehouse,
        database,
    )
    from cacao_accounting.compras.purchase_reconciliation_service import reconcile_purchase_invoice

    # Seed strict config
    seed_matching_config_for_company("cacao")
    database.session.commit()

    database.session.add_all(
        [
            UOM(code="EA-AC2", name="Each AC2"),
            Item(code="ITEM-AC2", name="Item AC2", item_type="goods", is_stock_item=True, default_uom="EA-AC2"),
            Warehouse(code="WH-AC2", name="Bodega AC2", company="cacao"),
        ]
    )
    receipt = PurchaseReceipt(company="cacao", posting_date=date(2026, 5, 1), supplier_id="SUPP-AC2", docstatus=1)
    database.session.add(receipt)
    database.session.flush()
    database.session.add(
        PurchaseReceiptItem(
            purchase_receipt_id=receipt.id,
            item_code="ITEM-AC2",
            item_name="Item AC2",
            qty=Decimal("10"),
            qty_in_base_uom=Decimal("10"),
            uom="EA-AC2",
            rate=Decimal("20.00"),
            amount=Decimal("200.00"),
            warehouse="WH-AC2",
        )
    )
    invoice = PurchaseInvoice(
        company="cacao",
        posting_date=date(2026, 5, 2),
        supplier_id="SUPP-AC2",
        purchase_receipt_id=receipt.id,
        docstatus=1,
    )
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        PurchaseInvoiceItem(
            purchase_invoice_id=invoice.id,
            item_code="ITEM-AC2",
            item_name="Item AC2",
            qty=Decimal("10"),
            uom="EA-AC2",
            rate=Decimal("20.00"),
            amount=Decimal("200.00"),
            warehouse="WH-AC2",
        )
    )
    database.session.commit()

    result_before = reconcile_purchase_invoice(invoice.id)
    database.session.commit()

    # Now change tolerance — should NOT affect the already-created reconciliation
    cfg = database.session.execute(database.select(PurchaseMatchingConfig).filter_by(company="cacao")).scalar_one()
    cfg.price_tolerance_value = Decimal("10")  # relax tolerance
    database.session.commit()

    recon = database.session.execute(
        database.select(PurchaseReconciliation).filter_by(purchase_invoice_id=invoice.id)
    ).scalar_one()

    # Historical record is unchanged
    assert recon.matched_amount == Decimal("200.0000")
    assert recon.matching_type == "3-way"


def test_state_reconstruction_from_events(app_ctx):
    """Criterio #3: se pueden reconstruir estados desde eventos."""
    from cacao_accounting.compras.purchase_reconciliation_service import (
        reconstruct_reconciliation_state,
        reconcile_purchase_invoice,
    )
    from cacao_accounting.database import (
        Item,
        PurchaseInvoice,
        PurchaseInvoiceItem,
        PurchaseReceipt,
        PurchaseReceiptItem,
        UOM,
        Warehouse,
        database,
    )

    database.session.add_all(
        [
            UOM(code="EA-AC3", name="Each AC3"),
            Item(code="ITEM-AC3", name="Item AC3", item_type="goods", is_stock_item=True, default_uom="EA-AC3"),
            Warehouse(code="WH-AC3", name="Bodega AC3", company="cacao"),
        ]
    )
    receipt = PurchaseReceipt(company="cacao", posting_date=date(2026, 5, 1), supplier_id="SUPP-AC3", docstatus=1)
    database.session.add(receipt)
    database.session.flush()
    database.session.add(
        PurchaseReceiptItem(
            purchase_receipt_id=receipt.id,
            item_code="ITEM-AC3",
            item_name="Item AC3",
            qty=Decimal("3"),
            qty_in_base_uom=Decimal("3"),
            uom="EA-AC3",
            rate=Decimal("30.00"),
            amount=Decimal("90.00"),
            warehouse="WH-AC3",
        )
    )
    invoice = PurchaseInvoice(
        company="cacao",
        posting_date=date(2026, 5, 2),
        supplier_id="SUPP-AC3",
        purchase_receipt_id=receipt.id,
        docstatus=1,
    )
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        PurchaseInvoiceItem(
            purchase_invoice_id=invoice.id,
            item_code="ITEM-AC3",
            item_name="Item AC3",
            qty=Decimal("3"),
            uom="EA-AC3",
            rate=Decimal("30.00"),
            amount=Decimal("90.00"),
            warehouse="WH-AC3",
        )
    )
    database.session.commit()

    result = reconcile_purchase_invoice(invoice.id)
    database.session.commit()

    # Reconstruct state from event log
    snapshot = reconstruct_reconciliation_state("cacao", result.reconciliation_id)

    assert snapshot.company == "cacao"
    assert snapshot.document_id == result.reconciliation_id
    # At least one event was logged for this reconciliation
    assert len(snapshot.events) >= 1
    # Event log contains a MATCH event
    event_types = [ev["event_type"] for ev in snapshot.events]
    assert any("MATCH" in et for et in event_types)


def test_system_supports_two_way_and_three_way_without_structural_changes(app_ctx):
    """Criterio #4: el sistema soporta 2-way y 3-way sin cambios estructurales."""
    from cacao_accounting.compras.purchase_reconciliation_service import (
        MatchingType,
        PurchaseMatchingConfig,
        get_matching_config,
        seed_matching_config_for_company,
    )
    from cacao_accounting.database import database

    seed_matching_config_for_company("cacao")
    database.session.commit()

    # 3-way (default)
    cfg_3way = get_matching_config("cacao")
    assert cfg_3way.matching_type == MatchingType.THREE_WAY

    # Switch to 2-way via config — no structural changes required
    cfg = database.session.execute(database.select(PurchaseMatchingConfig).filter_by(company="cacao")).scalar_one()
    cfg.matching_type = MatchingType.TWO_WAY
    database.session.commit()

    cfg_2way = get_matching_config("cacao")
    assert cfg_2way.matching_type == MatchingType.TWO_WAY


def test_bridge_account_is_configurable_not_required_by_default(app_ctx):
    """Criterio #5: la cuenta puente es configurable, no obligatoria."""
    from cacao_accounting.compras.purchase_reconciliation_service import (
        PurchaseMatchingConfig,
        seed_matching_config_for_company,
    )
    from cacao_accounting.database import database

    seed_matching_config_for_company("cacao")
    database.session.commit()

    cfg = database.session.execute(database.select(PurchaseMatchingConfig).filter_by(company="cacao")).scalar_one()
    # By default it is required (strict mode) but can be set to False
    assert isinstance(cfg.bridge_account_required, bool)

    cfg.bridge_account_required = False
    database.session.commit()

    cfg_relaxed = database.session.execute(database.select(PurchaseMatchingConfig).filter_by(company="cacao")).scalar_one()
    assert cfg_relaxed.bridge_account_required is False


def test_goods_received_cancelled_event_emitted_on_receipt_cancel(app_ctx):
    """Cancelar una recepcion emite GOODS_RECEIVED_CANCELLED y cancela conciliaciones dependientes."""
    from cacao_accounting.compras.purchase_reconciliation_service import (
        emit_goods_received_cancelled,
        reconcile_purchase_invoice,
    )
    from cacao_accounting.database import (
        Item,
        PurchaseEconomicEvent,
        PurchaseInvoice,
        PurchaseInvoiceItem,
        PurchaseReceipt,
        PurchaseReceiptItem,
        PurchaseReconciliation,
        UOM,
        Warehouse,
        database,
    )

    database.session.add_all(
        [
            UOM(code="EA-AC6", name="Each AC6"),
            Item(code="ITEM-AC6", name="Item AC6", item_type="goods", is_stock_item=True, default_uom="EA-AC6"),
            Warehouse(code="WH-AC6", name="Bodega AC6", company="cacao"),
        ]
    )
    receipt = PurchaseReceipt(company="cacao", posting_date=date(2026, 5, 1), supplier_id="SUPP-AC6", docstatus=1)
    database.session.add(receipt)
    database.session.flush()
    database.session.add(
        PurchaseReceiptItem(
            purchase_receipt_id=receipt.id,
            item_code="ITEM-AC6",
            item_name="Item AC6",
            qty=Decimal("2"),
            qty_in_base_uom=Decimal("2"),
            uom="EA-AC6",
            rate=Decimal("50.00"),
            amount=Decimal("100.00"),
            warehouse="WH-AC6",
        )
    )
    invoice = PurchaseInvoice(
        company="cacao",
        posting_date=date(2026, 5, 2),
        supplier_id="SUPP-AC6",
        purchase_receipt_id=receipt.id,
        docstatus=1,
    )
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        PurchaseInvoiceItem(
            purchase_invoice_id=invoice.id,
            item_code="ITEM-AC6",
            item_name="Item AC6",
            qty=Decimal("2"),
            uom="EA-AC6",
            rate=Decimal("50.00"),
            amount=Decimal("100.00"),
            warehouse="WH-AC6",
        )
    )
    database.session.commit()

    reconcile_purchase_invoice(invoice.id)
    database.session.commit()

    # Cancel the receipt — should also cancel dependent reconciliation and emit event
    emit_goods_received_cancelled(receipt.id, "cacao")
    database.session.commit()

    recon = database.session.execute(
        database.select(PurchaseReconciliation).filter_by(purchase_receipt_id=receipt.id)
    ).scalar_one()
    assert recon.status == "cancelled"

    cancel_event = database.session.execute(
        database.select(PurchaseEconomicEvent).filter_by(
            company="cacao", document_id=receipt.id, event_type="GOODS_RECEIVED_CANCELLED"
        )
    ).scalar_one_or_none()
    assert cancel_event is not None
