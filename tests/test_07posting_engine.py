# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

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
        database.session.add(
            Entity(
                code="cacao",
                name="Cacao",
                company_name="Cacao",
                tax_id="J0001",
                currency="NIO",
            )
        )
        database.session.commit()
        yield app


def test_gl_entry_constraint_rejects_unbalanced_records(app_ctx):
    from cacao_accounting.database import GLEntry, database

    entry = GLEntry(
        posting_date=date(2026, 5, 4),
        company="cacao",
        ledger_id=None,
        account_id=None,
        debit=Decimal("100.00"),
        credit=Decimal("100.00"),
        voucher_type="sales_invoice",
        voucher_id="test-1",
        document_no="TEST-001",
        naming_series_id=None,
    )
    database.session.add(entry)

    with pytest.raises(IntegrityError):
        database.session.commit()


def test_post_sales_invoice_creates_balanced_gl_entries(app_ctx):
    from cacao_accounting.contabilidad.posting import post_document_to_gl
    from cacao_accounting.database import (
        Accounts,
        GLEntry,
        PartyAccount,
        SalesInvoice,
        SalesInvoiceItem,
        database,
    )

    receivable_account = Accounts(
        entity="cacao",
        code="AR-001",
        name="Cuentas por cobrar",
        active=True,
        enabled=True,
        classification="asset",
        account_type="receivable",
    )
    income_account = Accounts(
        entity="cacao",
        code="IN-001",
        name="Ventas",
        active=True,
        enabled=True,
        classification="income",
        account_type="income",
    )
    database.session.add_all([receivable_account, income_account])
    database.session.flush()

    party_account = PartyAccount(
        party_id="CUST-001",
        company="cacao",
        receivable_account_id=receivable_account.id,
    )
    invoice = SalesInvoice(
        company="cacao",
        posting_date=date(2026, 5, 4),
        customer_id="CUST-001",
        customer_name="Cliente prueba",
        docstatus=1,
        document_no="cacao-SI-2026-05-00001",
        naming_series_id=None,
        total=Decimal("100.00"),
        grand_total=Decimal("100.00"),
    )
    database.session.add_all([party_account, invoice])
    database.session.flush()

    item = SalesInvoiceItem(
        sales_invoice_id=invoice.id,
        item_code="ITEM-001",
        item_name="Servicio de prueba",
        qty=Decimal("1"),
        rate=Decimal("100.00"),
        amount=Decimal("100.00"),
        income_account_id=income_account.id,
    )
    database.session.add(item)
    database.session.commit()

    post_document_to_gl(invoice)
    database.session.commit()

    posted_entries = (
        database.session.execute(database.select(GLEntry).filter_by(voucher_type="sales_invoice", voucher_id=invoice.id))
        .scalars()
        .all()
    )

    assert len(posted_entries) == 2
    assert sum(entry.debit for entry in posted_entries) == sum(entry.credit for entry in posted_entries)
    assert any(entry.debit == Decimal("100.00") and entry.account_id == receivable_account.id for entry in posted_entries)
    assert any(entry.credit == Decimal("100.00") and entry.account_id == income_account.id for entry in posted_entries)
    assert all(entry.voucher_type == "sales_invoice" for entry in posted_entries)
    assert all(entry.voucher_id == invoice.id for entry in posted_entries)


def test_post_payment_entry_creates_balanced_gl_entries(app_ctx):
    from cacao_accounting.contabilidad.posting import post_document_to_gl
    from cacao_accounting.database import Accounts, GLEntry, PartyAccount, PaymentEntry, database

    bank_account = Accounts(
        entity="cacao",
        code="BANK-001",
        name="Cuenta Banco",
        active=True,
        enabled=True,
        classification="asset",
        account_type="bank",
    )
    payable_account = Accounts(
        entity="cacao",
        code="AP-001",
        name="Cuentas por pagar",
        active=True,
        enabled=True,
        classification="liability",
        account_type="payable",
    )
    database.session.add_all([bank_account, payable_account])
    database.session.flush()

    party_account = PartyAccount(
        party_id="SUPP-001",
        company="cacao",
        payable_account_id=payable_account.id,
    )
    payment = PaymentEntry(
        company="cacao",
        posting_date=date(2026, 5, 4),
        payment_type="pay",
        party_type="supplier",
        party_id="SUPP-001",
        party_name="Proveedor prueba",
        paid_amount=Decimal("50.00"),
        paid_from_account_id=bank_account.id,
        docstatus=1,
    )
    database.session.add_all([party_account, payment])
    database.session.commit()

    post_document_to_gl(payment)
    database.session.commit()

    posted_entries = (
        database.session.execute(database.select(GLEntry).filter_by(voucher_type="payment_entry", voucher_id=payment.id))
        .scalars()
        .all()
    )

    assert len(posted_entries) == 2
    assert sum(entry.debit for entry in posted_entries) == sum(entry.credit for entry in posted_entries)
    assert any(entry.debit == Decimal("50.00") and entry.account_id == payable_account.id for entry in posted_entries)
    assert any(entry.credit == Decimal("50.00") and entry.account_id == bank_account.id for entry in posted_entries)


def test_post_sales_invoice_posts_once_per_active_book(app_ctx):
    from cacao_accounting.contabilidad.posting import post_document_to_gl
    from cacao_accounting.database import Accounts, Book, GLEntry, PartyAccount, SalesInvoice, SalesInvoiceItem, database

    receivable_account = Accounts(
        entity="cacao",
        code="AR-ML",
        name="Cuentas por cobrar ML",
        active=True,
        enabled=True,
        classification="asset",
        account_type="receivable",
    )
    income_account = Accounts(
        entity="cacao",
        code="IN-ML",
        name="Ventas ML",
        active=True,
        enabled=True,
        classification="income",
        account_type="income",
    )
    fiscal_book = Book(entity="cacao", code="FISC", name="Fiscal", is_primary=True)
    ifrs_book = Book(entity="cacao", code="IFRS", name="IFRS", is_primary=False)
    database.session.add_all([receivable_account, income_account, fiscal_book, ifrs_book])
    database.session.flush()
    database.session.add(PartyAccount(party_id="CUST-ML", company="cacao", receivable_account_id=receivable_account.id))
    invoice = SalesInvoice(
        company="cacao",
        posting_date=date(2026, 5, 4),
        customer_id="CUST-ML",
        docstatus=1,
        total=Decimal("25.00"),
        grand_total=Decimal("25.00"),
    )
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        SalesInvoiceItem(
            sales_invoice_id=invoice.id,
            item_code="ITEM-ML",
            item_name="Servicio multi libro",
            qty=Decimal("1"),
            rate=Decimal("25.00"),
            amount=Decimal("25.00"),
            income_account_id=income_account.id,
        )
    )
    database.session.commit()

    post_document_to_gl(invoice)
    database.session.commit()

    entries = (
        database.session.execute(database.select(GLEntry).filter_by(voucher_type="sales_invoice", voucher_id=invoice.id))
        .scalars()
        .all()
    )
    assert len(entries) == 4
    assert {entry.ledger_id for entry in entries} == {fiscal_book.id, ifrs_book.id}
    for ledger_id in {fiscal_book.id, ifrs_book.id}:
        ledger_entries = [entry for entry in entries if entry.ledger_id == ledger_id]
        assert sum(entry.debit for entry in ledger_entries) == sum(entry.credit for entry in ledger_entries)


def test_post_document_to_gl_rejects_duplicate_posting(app_ctx):
    from cacao_accounting.contabilidad.posting import PostingError, post_document_to_gl
    from cacao_accounting.database import Accounts, PartyAccount, SalesInvoice, SalesInvoiceItem, database

    receivable_account = Accounts(
        entity="cacao",
        code="AR-IDEMP",
        name="Cuentas por cobrar idempotencia",
        active=True,
        enabled=True,
        classification="asset",
        account_type="receivable",
    )
    income_account = Accounts(
        entity="cacao",
        code="IN-IDEMP",
        name="Ventas idempotencia",
        active=True,
        enabled=True,
        classification="income",
        account_type="income",
    )
    database.session.add_all([receivable_account, income_account])
    database.session.flush()
    database.session.add(PartyAccount(party_id="CUST-IDEMP", company="cacao", receivable_account_id=receivable_account.id))
    invoice = SalesInvoice(
        company="cacao",
        posting_date=date(2026, 5, 4),
        customer_id="CUST-IDEMP",
        docstatus=1,
        total=Decimal("10.00"),
        grand_total=Decimal("10.00"),
    )
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        SalesInvoiceItem(
            sales_invoice_id=invoice.id,
            item_code="ITEM-IDEMP",
            item_name="Servicio idempotente",
            qty=Decimal("1"),
            rate=Decimal("10.00"),
            amount=Decimal("10.00"),
            income_account_id=income_account.id,
        )
    )
    database.session.commit()

    post_document_to_gl(invoice)
    database.session.commit()

    with pytest.raises(PostingError):
        post_document_to_gl(invoice)


def test_cancel_document_creates_gl_reversals(app_ctx):
    from cacao_accounting.contabilidad.posting import cancel_document, post_document_to_gl
    from cacao_accounting.database import Accounts, GLEntry, PartyAccount, SalesInvoice, SalesInvoiceItem, database

    receivable_account = Accounts(
        entity="cacao",
        code="AR-REV",
        name="Cuentas por cobrar reverso",
        active=True,
        enabled=True,
        classification="asset",
        account_type="receivable",
    )
    income_account = Accounts(
        entity="cacao",
        code="IN-REV",
        name="Ventas reverso",
        active=True,
        enabled=True,
        classification="income",
        account_type="income",
    )
    database.session.add_all([receivable_account, income_account])
    database.session.flush()
    database.session.add(PartyAccount(party_id="CUST-REV", company="cacao", receivable_account_id=receivable_account.id))
    invoice = SalesInvoice(
        company="cacao",
        posting_date=date(2026, 5, 4),
        customer_id="CUST-REV",
        docstatus=1,
        total=Decimal("80.00"),
        grand_total=Decimal("80.00"),
    )
    database.session.add(invoice)
    database.session.flush()
    database.session.add(
        SalesInvoiceItem(
            sales_invoice_id=invoice.id,
            item_code="ITEM-REV",
            item_name="Servicio reversible",
            qty=Decimal("1"),
            rate=Decimal("80.00"),
            amount=Decimal("80.00"),
            income_account_id=income_account.id,
        )
    )
    database.session.commit()

    post_document_to_gl(invoice)
    database.session.commit()
    reversals = cancel_document(invoice)
    database.session.commit()

    entries = (
        database.session.execute(database.select(GLEntry).filter_by(voucher_type="sales_invoice", voucher_id=invoice.id))
        .scalars()
        .all()
    )
    assert invoice.docstatus == 2
    assert len(reversals) == 2
    assert sum(entry.debit for entry in entries) == sum(entry.credit for entry in entries)
    assert sum(entry.is_reversal for entry in entries) == 2
    assert all(entry.is_cancelled for entry in entries if not entry.is_reversal)


def test_post_payment_entry_uses_bank_account_gl_fallback(app_ctx):
    from cacao_accounting.contabilidad.posting import post_document_to_gl
    from cacao_accounting.database import Accounts, Bank, BankAccount, GLEntry, PartyAccount, PaymentEntry, database

    bank_gl_account = Accounts(
        entity="cacao",
        code="BANK-FB",
        name="Banco fallback",
        active=True,
        enabled=True,
        classification="asset",
        account_type="bank",
    )
    receivable_account = Accounts(
        entity="cacao",
        code="AR-FB",
        name="Cuentas por cobrar fallback",
        active=True,
        enabled=True,
        classification="asset",
        account_type="receivable",
    )
    bank = Bank(name="Banco prueba")
    database.session.add_all([bank_gl_account, receivable_account, bank])
    database.session.flush()
    bank_account = BankAccount(
        bank_id=bank.id,
        company="cacao",
        account_name="Cuenta fallback",
        gl_account_id=bank_gl_account.id,
    )
    database.session.add(bank_account)
    database.session.flush()
    payment = PaymentEntry(
        company="cacao",
        posting_date=date(2026, 5, 4),
        payment_type="receive",
        party_type="customer",
        party_id="CUST-FB",
        bank_account_id=bank_account.id,
        received_amount=Decimal("45.00"),
        docstatus=1,
    )
    database.session.add_all(
        [PartyAccount(party_id="CUST-FB", company="cacao", receivable_account_id=receivable_account.id), payment]
    )
    database.session.commit()

    post_document_to_gl(payment)
    database.session.commit()

    entries = (
        database.session.execute(database.select(GLEntry).filter_by(voucher_type="payment_entry", voucher_id=payment.id))
        .scalars()
        .all()
    )
    assert any(entry.debit == Decimal("45.00") and entry.account_id == bank_gl_account.id for entry in entries)
    assert any(entry.credit == Decimal("45.00") and entry.party_id == "CUST-FB" for entry in entries)


def test_post_stock_entry_creates_stock_ledger_bin_valuation_and_gl(app_ctx):
    from cacao_accounting.contabilidad.posting import post_document_to_gl
    from cacao_accounting.database import (
        Accounts,
        CompanyDefaultAccount,
        GLEntry,
        Item,
        ItemAccount,
        StockBin,
        StockEntry,
        StockEntryItem,
        StockLedgerEntry,
        StockValuationLayer,
        UOM,
        Warehouse,
        database,
    )

    inventory_account = Accounts(
        entity="cacao",
        code="INV-ST",
        name="Inventario",
        active=True,
        enabled=True,
        classification="asset",
        account_type="inventory",
    )
    gr_ir_account = Accounts(
        entity="cacao",
        code="GRIR-ST",
        name="GR IR",
        active=True,
        enabled=True,
        classification="liability",
        account_type="liability",
    )
    uom = UOM(code="UND", name="Unidad")
    item = Item(code="ITEM-ST", name="Item stock", item_type="goods", is_stock_item=True, default_uom="UND")
    warehouse = Warehouse(code="WH-ST", name="Bodega stock", company="cacao")
    database.session.add_all([inventory_account, gr_ir_account, uom, item, warehouse])
    database.session.flush()
    database.session.add_all(
        [
            ItemAccount(item_code="ITEM-ST", company="cacao", inventory_account_id=inventory_account.id),
            CompanyDefaultAccount(company="cacao", gr_ir_account_id=gr_ir_account.id),
        ]
    )
    entry = StockEntry(
        company="cacao",
        posting_date=date(2026, 5, 4),
        purpose="material_receipt",
        to_warehouse="WH-ST",
        docstatus=1,
    )
    database.session.add(entry)
    database.session.flush()
    database.session.add(
        StockEntryItem(
            stock_entry_id=entry.id,
            item_code="ITEM-ST",
            target_warehouse="WH-ST",
            qty=Decimal("3"),
            qty_in_base_uom=Decimal("3"),
            uom="UND",
            basic_rate=Decimal("12.00"),
            valuation_rate=Decimal("12.00"),
            amount=Decimal("36.00"),
        )
    )
    database.session.commit()

    post_document_to_gl(entry)
    database.session.commit()

    gl_entries = (
        database.session.execute(database.select(GLEntry).filter_by(voucher_type="stock_entry", voucher_id=entry.id))
        .scalars()
        .all()
    )
    stock_entries = (
        database.session.execute(database.select(StockLedgerEntry).filter_by(voucher_type="stock_entry", voucher_id=entry.id))
        .scalars()
        .all()
    )
    bin_row = database.session.execute(
        database.select(StockBin).filter_by(item_code="ITEM-ST", warehouse="WH-ST")
    ).scalar_one()
    valuation_layers = (
        database.session.execute(
            database.select(StockValuationLayer).filter_by(voucher_type="stock_entry", voucher_id=entry.id)
        )
        .scalars()
        .all()
    )
    assert len(gl_entries) == 2
    assert sum(line.debit for line in gl_entries) == sum(line.credit for line in gl_entries)
    assert len(stock_entries) == 1
    assert stock_entries[0].qty_change == Decimal("3.000000000")
    assert bin_row.actual_qty == Decimal("3.000000000")
    assert len(valuation_layers) == 1


def test_stock_transfer_creates_stock_ledger_without_gl(app_ctx):
    from cacao_accounting.contabilidad.posting import post_document_to_gl
    from cacao_accounting.database import (
        Item,
        StockEntry,
        StockEntryItem,
        StockLedgerEntry,
        UOM,
        Warehouse,
        database,
    )

    database.session.add_all(
        [
            UOM(code="EA", name="Each"),
            Item(code="ITEM-TR", name="Item traslado", item_type="goods", is_stock_item=True, default_uom="EA"),
            Warehouse(code="WH-A", name="Bodega A", company="cacao"),
            Warehouse(code="WH-B", name="Bodega B", company="cacao"),
        ]
    )
    entry = StockEntry(
        company="cacao",
        posting_date=date(2026, 5, 4),
        purpose="material_transfer",
        from_warehouse="WH-A",
        to_warehouse="WH-B",
        docstatus=1,
    )
    database.session.add(entry)
    database.session.flush()
    database.session.add(
        StockEntryItem(
            stock_entry_id=entry.id,
            item_code="ITEM-TR",
            source_warehouse="WH-A",
            target_warehouse="WH-B",
            qty=Decimal("2"),
            qty_in_base_uom=Decimal("2"),
            uom="EA",
            basic_rate=Decimal("5.00"),
            valuation_rate=Decimal("5.00"),
            amount=Decimal("10.00"),
        )
    )
    database.session.commit()

    entries = post_document_to_gl(entry)
    database.session.commit()

    stock_entries = (
        database.session.execute(database.select(StockLedgerEntry).filter_by(voucher_type="stock_entry", voucher_id=entry.id))
        .scalars()
        .all()
    )
    assert entries == []
    assert len(stock_entries) == 2
    assert sorted(line.qty_change for line in stock_entries) == [Decimal("-2.000000000"), Decimal("2.000000000")]
