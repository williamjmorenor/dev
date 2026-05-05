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

    entries = post_document_to_gl(invoice)
    database.session.commit()

    posted_entries = (
        database.session.execute(
            database.select(GLEntry).filter_by(voucher_type="sales_invoice", voucher_id=invoice.id)
        )
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

    entries = post_document_to_gl(payment)
    database.session.commit()

    posted_entries = (
        database.session.execute(
            database.select(GLEntry).filter_by(voucher_type="payment_entry", voucher_id=payment.id)
        )
        .scalars()
        .all()
    )

    assert len(posted_entries) == 2
    assert sum(entry.debit for entry in posted_entries) == sum(entry.credit for entry in posted_entries)
    assert any(entry.debit == Decimal("50.00") and entry.account_id == payable_account.id for entry in posted_entries)
    assert any(entry.credit == Decimal("50.00") and entry.account_id == bank_account.id for entry in posted_entries)
