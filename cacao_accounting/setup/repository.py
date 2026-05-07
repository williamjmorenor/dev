# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""Repositorios de datos para el asistente de configuración inicial."""

from __future__ import annotations

from datetime import date
from typing import Any

from cacao_accounting.database import (
    AccountingPeriod,
    Book,
    CacaoConfig,
    CostCenter,
    Entity,
    FiscalYear,
    database,
)


def get_setup_value(key: str, default: Any = None) -> Any:
    """Recupera un valor de configuración por clave."""
    record = database.session.execute(database.select(CacaoConfig).filter_by(key=key)).first()
    if record:
        return record[0].value
    return default


def set_setup_value(key: str, value: str) -> None:
    """Establece o crea un valor de configuración."""
    record = database.session.execute(database.select(CacaoConfig).filter_by(key=key)).first()
    if record:
        config = record[0]
        config.value = value
    else:
        config = CacaoConfig(key=key, value=value)
        database.session.add(config)


def create_default_entity(data: dict, status: str = "default", default: bool = True) -> Entity:
    """Crea y añade una entidad en la sesión de base de datos."""
    if not data.get("id") or not data.get("razon_social") or not data.get("id_fiscal"):
        raise ValueError("Los datos de la entidad son incompletos.")

    existing_entity = database.session.execute(database.select(Entity).filter_by(code=data["id"])).scalar_one_or_none()
    if existing_entity is not None:
        raise ValueError(f"La entidad con código '{data['id']}' ya existe.")

    entity = Entity(
        code=data.get("id"),
        company_name=data.get("razon_social"),
        name=data.get("nombre_comercial") or data.get("razon_social"),
        tax_id=data.get("id_fiscal"),
        currency=data.get("moneda"),
        country=data.get("pais"),
        entity_type=data.get("tipo_entidad"),
        status=status,
        enabled=True,
        default=default,
    )
    database.session.add(entity)
    return entity


def create_default_book(entity: Entity) -> "Book":
    from cacao_accounting.database import Book

    existing_book = database.session.execute(
        database.select(Book).filter_by(entity=entity.code, code="FISC")
    ).scalar_one_or_none()
    if existing_book is not None:
        return existing_book

    book = Book(
        code="FISC",
        name="Fiscal",
        entity=entity.code,
        currency=entity.currency,
        is_primary=True,
        default=True,
    )
    database.session.add(book)
    return book


def create_default_cost_center(entity: Entity) -> "CostCenter":
    from cacao_accounting.database import CostCenter

    existing_cost_center = database.session.execute(
        database.select(CostCenter).filter_by(entity=entity.code, code="MAIN")
    ).scalar_one_or_none()
    if existing_cost_center is not None:
        return existing_cost_center

    cost_center = CostCenter(
        entity=entity.code,
        code="MAIN",
        name="Principal",
        active=True,
        enabled=True,
        default=True,
        group=False,
    )
    database.session.add(cost_center)
    return cost_center


def create_default_fiscal_year(entity: Entity, reference_date: "date | None" = None) -> "FiscalYear":
    from datetime import date as _date
    from cacao_accounting.database import FiscalYear

    today = reference_date or _date.today()
    start = _date(today.year, 1, 1)
    end = _date(today.year, 12, 31)
    existing_year = database.session.execute(
        database.select(FiscalYear).filter_by(entity=entity.code, year_start_date=start, year_end_date=end)
    ).scalar_one_or_none()
    if existing_year is not None:
        return existing_year

    fiscal_year = FiscalYear(
        entity=entity.code,
        name=str(today.year),
        year_start_date=start,
        year_end_date=end,
        is_closed=False,
    )
    database.session.add(fiscal_year)
    database.session.flush()
    return fiscal_year


def create_default_accounting_period(entity: Entity, fiscal_year: "FiscalYear") -> "AccountingPeriod":
    from cacao_accounting.database import AccountingPeriod

    existing_period = database.session.execute(
        database.select(AccountingPeriod)
        .filter_by(entity=entity.code, name=str(fiscal_year.year_start_date.year))
    ).scalar_one_or_none()
    if existing_period is not None:
        return existing_period

    period = AccountingPeriod(
        entity=entity.code,
        fiscal_year_id=fiscal_year.id,
        name=str(fiscal_year.year_start_date.year),
        status="open",
        enabled=True,
        is_closed=False,
        start=fiscal_year.year_start_date,
        end=fiscal_year.year_end_date,
    )
    database.session.add(period)
    return period


def get_default_entity() -> Entity | None:
    """Recupera la entidad predeterminada si existe."""
    return database.session.execute(database.select(Entity).filter_by(status="default")).scalar_one_or_none()
