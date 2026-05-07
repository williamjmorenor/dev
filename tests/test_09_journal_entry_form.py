# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

from __future__ import annotations

import json
from datetime import date

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
        from cacao_accounting.database import Entity, Modules, User, database

        database.create_all()
        database.session.add_all(
            [
                Entity(code="cacao", name="Cacao", company_name="Cacao", tax_id="J0001", currency="NIO", enabled=True),
                Modules(module="accounting", default=True, enabled=True),
                User(user="admin", name="Admin", password=b"x", classification="admin", active=True),
            ]
        )
        database.session.commit()
        yield app


def _login(client, user_id: str) -> None:
    with client.session_transaction() as session:
        session["_user_id"] = user_id
        session["_fresh"] = True


def test_create_journal_draft_preserves_lines_and_does_not_post_gl(app_ctx):
    from cacao_accounting.contabilidad.journal_service import create_journal_draft
    from cacao_accounting.database import Accounts, ComprobanteContableDetalle, GLEntry, database

    debit_account = Accounts(entity="cacao", code="EXP-001", name="Gasto", active=True, enabled=True, group=False)
    credit_account = Accounts(entity="cacao", code="CASH-001", name="Caja", active=True, enabled=True, group=False)
    database.session.add_all([debit_account, credit_account])
    database.session.commit()

    journal = create_journal_draft(
        {
            "company": "cacao",
            "posting_date": "2026-05-06",
            "memo": "Registro manual",
            "lines": [
                {
                    "account": debit_account.id,
                    "cost_center": "MAIN",
                    "project": "PRJ",
                    "debit": "100.00",
                    "credit": "0",
                    "remarks": "Debe",
                },
                {
                    "account": credit_account.id,
                    "party_type": "supplier",
                    "party": "SUP-001",
                    "debit": "0",
                    "credit": "100.00",
                    "reference_type": "purchase_invoice",
                    "reference_name": "PI-001",
                },
            ],
        },
        user_id="user-1",
    )

    lines = (
        database.session.execute(database.select(ComprobanteContableDetalle).filter_by(transaction_id=journal.id))
        .scalars()
        .all()
    )
    gl_entries = database.session.execute(database.select(GLEntry).filter_by(voucher_id=journal.id)).scalars().all()

    assert journal.status == "draft"
    assert len(lines) == 2
    assert lines[0].account == "EXP-001"
    assert lines[0].cost_center == "MAIN"
    assert lines[0].project == "PRJ"
    assert lines[1].third_type == "supplier"
    assert gl_entries == []


def test_journal_service_rejects_unbalanced_and_double_sided_lines(app_ctx):
    from cacao_accounting.contabilidad.journal_service import JournalValidationError, create_journal_draft

    with pytest.raises(JournalValidationError, match="positivos"):
        create_journal_draft(
            {
                "company": "cacao",
                "posting_date": "2026-05-06",
                "lines": [{"account": "EXP-001", "debit": "10", "credit": "5"}],
            },
            user_id="user-1",
        )

    with pytest.raises(JournalValidationError, match="balanceado"):
        create_journal_draft(
            {
                "company": "cacao",
                "posting_date": "2026-05-06",
                "lines": [
                    {"account": "EXP-001", "debit": "10", "credit": "0"},
                    {"account": "CASH-001", "debit": "0", "credit": "9"},
                ],
            },
            user_id="user-1",
        )


def test_journal_new_route_renders_new_backend_form(app_ctx):
    from cacao_accounting.database import User

    user = User.query.filter_by(user="admin").first()
    client = app_ctx.test_client()
    _login(client, user.id)

    response = client.get("/accounting/journal/new")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "journalEntryForm" in html
    assert "smartSelect" in html
    assert 'doctype: "company"' in html
    assert 'entity_type: "journal_entry"' in html
    assert "/accounting/gl/new" not in html


def test_journal_post_creates_draft_without_gl_entries(app_ctx):
    from cacao_accounting.database import Accounts, Book, ComprobanteContable, GLEntry, User, database

    debit_account = Accounts(entity="cacao", code="EXP-002", name="Gasto", active=True, enabled=True, group=False)
    credit_account = Accounts(entity="cacao", code="CASH-002", name="Caja", active=True, enabled=True, group=False)
    fiscal_book = Book(entity="cacao", code="FISC", name="Fiscal", status="activo", is_primary=True)
    ifrs_book = Book(entity="cacao", code="IFRS", name="IFRS", status="activo")
    database.session.add_all([debit_account, credit_account, fiscal_book, ifrs_book])
    database.session.commit()

    user = User.query.filter_by(user="admin").first()
    client = app_ctx.test_client()
    _login(client, user.id)
    payload = {
        "company": "cacao",
        "posting_date": "2026-05-06",
        "books": ["FISC", "IFRS"],
        "memo": "Desde vista",
        "lines": [
            {"account": debit_account.id, "debit": "25.00", "credit": "0"},
            {"account": credit_account.id, "debit": "0", "credit": "25.00"},
        ],
    }

    response = client.post("/accounting/journal/new", data={"journal_payload": json.dumps(payload)})
    journal = database.session.execute(database.select(ComprobanteContable).filter_by(memo="Desde vista")).scalar_one()
    gl_entries = database.session.execute(database.select(GLEntry).filter_by(voucher_id=journal.id)).scalars().all()

    assert response.status_code == 302
    assert journal.status == "draft"
    assert journal.book == "FISC"
    assert journal.book_codes == '["FISC", "IFRS"]'
    assert gl_entries == []


def test_journal_books_endpoint_returns_only_active_books(app_ctx):
    from cacao_accounting.database import Book, User, database

    database.session.add_all(
        [
            Book(entity="cacao", code="FISC", name="Fiscal", status="activo", is_primary=True),
            Book(entity="cacao", code="IFRS", name="IFRS", status=None),
            Book(entity="cacao", code="TAX", name="Tax", status="inactivo"),
        ]
    )
    database.session.commit()

    user = User.query.filter_by(user="admin").first()
    client = app_ctx.test_client()
    _login(client, user.id)

    response = client.get("/accounting/journal/books?company=cacao")
    payload = response.get_json()

    assert response.status_code == 200
    assert [item["value"] for item in payload["results"]] == ["FISC", "IFRS"]


def test_submit_journal_posts_only_selected_books(app_ctx):
    from cacao_accounting.contabilidad.journal_service import create_journal_draft, submit_journal
    from cacao_accounting.database import Accounts, Book, GLEntry, database

    debit_account = Accounts(entity="cacao", code="EXP-003", name="Gasto", active=True, enabled=True, group=False)
    credit_account = Accounts(entity="cacao", code="CASH-003", name="Caja", active=True, enabled=True, group=False)
    fiscal_book = Book(entity="cacao", code="FISC", name="Fiscal", status="activo", is_primary=True)
    ifrs_book = Book(entity="cacao", code="IFRS", name="IFRS", status="activo")
    database.session.add_all(
        [
            debit_account,
            credit_account,
            fiscal_book,
            ifrs_book,
            Book(entity="cacao", code="TAX", name="Tax", status="inactivo"),
        ]
    )
    database.session.commit()

    journal = create_journal_draft(
        {
            "company": "cacao",
            "posting_date": "2026-05-06",
            "books": ["IFRS"],
            "lines": [
                {"account": debit_account.id, "debit": "10.00", "credit": "0"},
                {"account": credit_account.id, "debit": "0", "credit": "10.00"},
            ],
        },
        user_id="user-1",
    )

    entries = submit_journal(journal.id)

    assert len(entries) == 2
    posted_entries = database.session.execute(database.select(GLEntry).filter_by(voucher_id=journal.id)).scalars().all()
    assert len(posted_entries) == 2
    assert {entry.ledger_id for entry in posted_entries} == {ifrs_book.id}


def test_submit_journal_without_selected_books_posts_all_active_books(app_ctx):
    from cacao_accounting.contabilidad.journal_service import create_journal_draft, submit_journal
    from cacao_accounting.database import Accounts, Book, GLEntry, database

    debit_account = Accounts(entity="cacao", code="EXP-004", name="Gasto", active=True, enabled=True, group=False)
    credit_account = Accounts(entity="cacao", code="CASH-004", name="Caja", active=True, enabled=True, group=False)
    fiscal_book = Book(entity="cacao", code="FISC", name="Fiscal", status="activo", is_primary=True)
    ifrs_book = Book(entity="cacao", code="IFRS", name="IFRS", status="activo")
    database.session.add_all(
        [
            debit_account,
            credit_account,
            fiscal_book,
            ifrs_book,
            Book(entity="cacao", code="TAX", name="Tax", status="inactivo"),
        ]
    )
    database.session.commit()

    journal = create_journal_draft(
        {
            "company": "cacao",
            "posting_date": "2026-05-06",
            "books": [],
            "lines": [
                {"account": debit_account.id, "debit": "15.00", "credit": "0"},
                {"account": credit_account.id, "debit": "0", "credit": "15.00"},
            ],
        },
        user_id="user-1",
    )

    submit_journal(journal.id)

    posted_entries = database.session.execute(database.select(GLEntry).filter_by(voucher_id=journal.id)).scalars().all()
    assert len(posted_entries) == 4
    assert {entry.ledger_id for entry in posted_entries} == {fiscal_book.id, ifrs_book.id}


def test_entity_creation_uses_setup_defaults_and_creates_required_book_cost_center_and_series(app_ctx):
    from cacao_accounting.database import (
        AccountingPeriod,
        Book,
        CompanyDefaultAccount,
        CostCenter,
        Currency,
        Entity,
        NamingSeries,
        User,
        database,
    )

    database.session.add(Currency(code="NIO", name="Córdoba", decimals=2, active=True, default=True))
    database.session.commit()

    user = database.session.execute(database.select(User).filter_by(user="admin")).scalar_one()
    client = app_ctx.test_client()
    _login(client, user.id)

    response = client.post(
        "/accounting/entity/new",
        data={
            "id": "mapco",
            "razon_social": "Mapping Company",
            "nombre_comercial": "Mapping Company",
            "id_fiscal": "J-MAP",
            "pais": "NI",
            "idioma": "es",
            "moneda": "NIO",
            "tipo_entidad": "Sociedad Anonima",
            "catalogo": "preexistente",
            "catalogo_origen": "base_es.csv",
        },
    )

    assert response.status_code == 302

    entity = database.session.execute(database.select(Entity).filter_by(code="mapco")).scalar_one()
    book = database.session.execute(database.select(Book).filter_by(entity="mapco", code="FISC")).scalar_one()
    cost_center = database.session.execute(database.select(CostCenter).filter_by(entity="mapco", code="MAIN")).scalar_one()
    period = database.session.execute(
        database.select(AccountingPeriod).filter_by(entity="mapco", name=str(date.today().year))
    ).scalar_one_or_none()
    series = database.session.execute(
        database.select(NamingSeries).filter_by(company="mapco", entity_type="journal_entry")
    ).scalar_one_or_none()
    defaults = database.session.execute(database.select(CompanyDefaultAccount).filter_by(company="mapco")).scalar_one_or_none()

    assert entity.country == "NI"
    assert entity.currency == "NIO"
    assert book.currency == "NIO"
    assert cost_center.default is True
    assert period is not None
    assert series is not None
    assert defaults is not None


def test_search_select_supports_journal_doctypes_and_filters(app_ctx):
    from cacao_accounting.database import Book, CostCenter, Project, Unit, User, database

    from cacao_accounting.database import Currency

    database.session.add_all(
        [
            Currency(code="NIO", name="Córdoba", decimals=2, active=True, default=True),
            Book(code="FISC", name="Fiscal", entity="cacao", is_primary=True),
            CostCenter(code="MAIN", name="Principal", entity="cacao", active=True, enabled=True, group=False),
            Unit(code="HQ", name="Central", entity="cacao"),
            Project(code="PRJ", name="Proyecto", entity="cacao", enabled=True, start=date(2026, 1, 1)),
        ]
    )
    database.session.commit()

    user = User.query.filter_by(user="admin").first()
    client = app_ctx.test_client()
    _login(client, user.id)

    assert client.get("/api/search-select?doctype=company&q=Cacao").json["results"][0]["value"] == "cacao"
    assert client.get("/api/search-select?doctype=book&q=Fiscal&company=cacao").json["results"][0]["value"] == "FISC"
    assert client.get("/api/search-select?doctype=cost_center&q=Principal&company=cacao").json["results"][0]["value"] == "MAIN"
    assert client.get("/api/search-select?doctype=unit&q=Central&company=cacao").json["results"][0]["value"] == "HQ"
    assert client.get("/api/search-select?doctype=project&q=Proyecto&company=cacao").json["results"][0]["value"] == "PRJ"
    assert client.get("/api/search-select?doctype=book&q=Fiscal&bad_filter=x").status_code == 400


def test_form_preferences_are_persisted_per_user(app_ctx):
    from cacao_accounting.database import User, database
    from cacao_accounting.form_preferences import get_form_preference

    user_a = User.query.filter_by(user="admin").first()
    user_b = User(user="other", name="Other", password=b"x", classification="admin", active=True)
    database.session.add(user_b)
    database.session.commit()

    client = app_ctx.test_client()
    _login(client, user_a.id)
    payload = {
        "schema_version": 1,
        "columns": [{"field": "account", "label": "Cuenta", "width": 4, "visible": True, "required": True}],
    }

    saved = client.put("/api/form-preferences/accounting.journal_entry/draft", json=payload)
    read_a = client.get("/api/form-preferences/accounting.journal_entry/draft")
    read_b = get_form_preference(user_b.id, "accounting.journal_entry", "draft")

    assert saved.status_code == 200
    assert read_a.json["columns"][0]["width"] == 4
    assert read_b["columns"][0]["width"] == 3


def test_journal_edit_route_rehydrates_draft_and_updates_books(app_ctx):
    from cacao_accounting.contabilidad.journal_service import create_journal_draft
    from cacao_accounting.database import Accounts, Book, User, database

    debit_account = Accounts(entity="cacao", code="EXP-005", name="Gasto", active=True, enabled=True, group=False)
    credit_account = Accounts(entity="cacao", code="CASH-005", name="Caja", active=True, enabled=True, group=False)
    database.session.add_all(
        [
            debit_account,
            credit_account,
            Book(entity="cacao", code="FISC", name="Fiscal", status="activo", is_primary=True),
            Book(entity="cacao", code="IFRS", name="IFRS", status="activo"),
        ]
    )
    database.session.commit()

    journal = create_journal_draft(
        {
            "company": "cacao",
            "posting_date": "2026-05-06",
            "books": ["FISC", "IFRS"],
            "memo": "Borrador editable",
            "lines": [
                {"account": debit_account.id, "debit": "20.00", "credit": "0"},
                {"account": credit_account.id, "debit": "0", "credit": "20.00"},
            ],
        },
        user_id="user-1",
    )

    user = User.query.filter_by(user="admin").first()
    client = app_ctx.test_client()
    _login(client, user.id)

    response = client.get(f"/accounting/journal/edit/{journal.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Borrador editable" in html
    assert '"books": ["FISC", "IFRS"]' in html

    update_payload = {
        "company": "cacao",
        "posting_date": "2026-05-07",
        "books": ["IFRS"],
        "memo": "Borrador actualizado",
        "lines": [
            {"account": debit_account.id, "debit": "30.00", "credit": "0"},
            {"account": credit_account.id, "debit": "0", "credit": "30.00"},
        ],
    }
    update_response = client.post(
        f"/accounting/journal/edit/{journal.id}",
        data={"journal_payload": json.dumps(update_payload)},
        follow_redirects=False,
    )

    updated_journal = database.session.get(type(journal), journal.id)
    assert update_response.status_code == 302
    assert updated_journal.book == "IFRS"
    assert updated_journal.book_codes == '["IFRS"]'
    assert updated_journal.memo == "Borrador actualizado"
