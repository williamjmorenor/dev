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
