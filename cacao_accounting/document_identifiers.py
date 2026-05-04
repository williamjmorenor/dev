# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Servicios para resolver series e identificadores documentales."""

from __future__ import annotations

from datetime import date
from typing import cast

from cacao_accounting.database import AccountingPeriod, NamingSeries, Sequence, SeriesSequenceMap, database
from cacao_accounting.database.helpers import generate_identifier, get_active_naming_series


class IdentifierConfigurationError(ValueError):
    """Error controlado para configuraciones de series e identificadores."""


def parse_posting_date(posting_date_raw: date | str | None) -> date:
    """Normaliza la fecha contable para usarla en series y validaciones."""

    if isinstance(posting_date_raw, date):
        return posting_date_raw
    if not posting_date_raw:
        raise IdentifierConfigurationError("Debe indicar la fecha de contabilizacion.")

    try:
        return date.fromisoformat(str(posting_date_raw))
    except ValueError as exc:
        raise IdentifierConfigurationError("La fecha de contabilizacion es invalida.") from exc


def validate_accounting_period(company: str | None, posting_date: date) -> None:
    """Valida que la fecha contable no caiga en un periodo cerrado."""

    if not company:
        raise IdentifierConfigurationError("Debe indicar la compania del documento.")

    closed_period = database.session.execute(
        database.select(AccountingPeriod)
        .filter_by(entity=company, is_closed=True)
        .where(AccountingPeriod.start <= posting_date)
        .where(AccountingPeriod.end >= posting_date)
    ).scalar_one_or_none()

    if closed_period:
        raise IdentifierConfigurationError("No puede registrar documentos en un periodo contable cerrado.")


def _pick_naming_series(entity_type: str, company: str, naming_series_id: str | None) -> NamingSeries:
    """Selecciona la serie activa por doctype y compania."""

    if naming_series_id:
        selected = database.session.get(NamingSeries, naming_series_id)
        if not selected or not selected.is_active:
            raise IdentifierConfigurationError("La serie seleccionada no existe o esta inactiva.")
        if selected.entity_type != entity_type:
            raise IdentifierConfigurationError("La serie seleccionada no coincide con el tipo de documento.")
        if selected.company not in (None, company):
            raise IdentifierConfigurationError("La serie seleccionada no pertenece a la compania indicada.")
        return selected

    candidates = get_active_naming_series(entity_type=entity_type, company=company)
    if not candidates:
        return _create_default_series(entity_type=entity_type, company=company)

    exact_company_matches = [series for series in candidates if series.company == company]
    if exact_company_matches:
        return sorted(exact_company_matches, key=lambda row: row.name)[0]

    return sorted(candidates, key=lambda row: row.name)[0]


def _default_entity_code(entity_type: str) -> str:
    """Devuelve abreviacion de doctype para prefijos de series."""

    map_codes = {
        "purchase_request": "PREQ",
        "purchase_quotation": "RFQ",
        "supplier_quotation": "SPQ",
        "purchase_order": "PO",
        "purchase_receipt": "PR",
        "purchase_invoice": "PI",
        "sales_order": "SO",
        "sales_request": "SR",
        "delivery_note": "DN",
        "sales_invoice": "SI",
        "sales_quotation": "SQ",
        "payment_entry": "PAY",
        "stock_entry": "STE",
    }
    return map_codes.get(entity_type, entity_type[:3].upper())


def _create_default_series(entity_type: str, company: str) -> NamingSeries:
    """Crea una serie y secuencia por defecto para compania + doctype."""

    code = _default_entity_code(entity_type)
    sequence = Sequence(
        name=f"{company} {entity_type} sequence",
        current_value=0,
        increment=1,
        padding=5,
        reset_policy="yearly",
    )
    database.session.add(sequence)
    database.session.flush()

    naming_series = NamingSeries(
        name=f"{company}-{code}",
        entity_type=entity_type,
        company=company,
        prefix_template=f"*COMP*-{code}-*YYYY*-*MM*-",
        is_active=True,
    )
    database.session.add(naming_series)
    database.session.flush()

    database.session.add(
        SeriesSequenceMap(
            naming_series_id=naming_series.id,
            sequence_id=sequence.id,
            priority=0,
            condition=None,
        )
    )
    database.session.flush()
    return naming_series


def _pick_sequence_id(naming_series_id: str) -> str:
    """Selecciona la secuencia con mayor prioridad para la serie."""

    mapping = (
        database.session.execute(
            database.select(SeriesSequenceMap)
            .filter_by(naming_series_id=naming_series_id)
            .order_by(SeriesSequenceMap.priority.asc())
        )
        .scalars()
        .first()
    )

    if not mapping:
        raise IdentifierConfigurationError("La serie seleccionada no tiene una secuencia asociada.")

    return mapping.sequence_id


def assign_document_identifier(
    *,
    document: object,
    entity_type: str,
    posting_date_raw: date | str | None,
    naming_series_id: str | None,
) -> None:
    """Asigna document_no y naming_series_id a un documento transaccional."""

    posting_date = parse_posting_date(posting_date_raw)
    company = getattr(document, "company", None)
    validate_accounting_period(company=company, posting_date=posting_date)
    company_code = cast(str, company)

    naming_series = _pick_naming_series(
        entity_type=entity_type,
        company=company_code,
        naming_series_id=naming_series_id,
    )
    sequence_id = _pick_sequence_id(naming_series.id)

    identifier = generate_identifier(
        entity_type=entity_type,
        entity_id=getattr(document, "id"),
        posting_date=posting_date,
        company=company_code,
        naming_series_id=naming_series.id,
        sequence_id=sequence_id,
    )

    setattr(document, "posting_date", posting_date)
    setattr(document, "naming_series_id", naming_series.id)
    setattr(document, "document_no", identifier)
