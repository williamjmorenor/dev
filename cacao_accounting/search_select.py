# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Servicio generico para campos de seleccion asistida."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from sqlalchemy import Select, case, cast, func, or_, select, true
from sqlalchemy.orm.attributes import InstrumentedAttribute

from cacao_accounting.database import (
    Accounts,
    BankAccount,
    CompanyParty,
    Item,
    NamingSeries,
    Party,
    Warehouse,
    database,
)


class SearchSelectError(ValueError):
    """Error validado para busquedas de campos seleccionables."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        """Initialize SearchSelectError with a message and HTTP status code."""
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class SearchSelectSpec:
    """Contrato de busqueda para un doctype permitido."""

    doctype: str
    model: type[Any]
    search_fields: tuple[str, ...]
    value_field: str
    label_builder: Callable[[Any], str]
    allowed_filters: dict[str, str]
    default_filters: dict[str, str | bool]
    limit: int = 20


def _account_label(account: Accounts) -> str:
    return f"{account.code} - {account.name}"


def _party_label(party: Party) -> str:
    tax_suffix = f" ({party.tax_id})" if party.tax_id else ""
    return f"{party.name}{tax_suffix}"


def _item_label(item: Item) -> str:
    return f"{item.code} - {item.name}"


def _warehouse_label(warehouse: Warehouse) -> str:
    return f"{warehouse.code} - {warehouse.name}"


def _bank_account_label(bank_account: BankAccount) -> str:
    account_no = f" {bank_account.account_no}" if bank_account.account_no else ""
    return f"{bank_account.account_name}{account_no}"


def _naming_series_label(naming_series: NamingSeries) -> str:
    return f"{naming_series.name} ({naming_series.entity_type})"


SEARCH_SELECT_REGISTRY: dict[str, SearchSelectSpec] = {
    "account": SearchSelectSpec(
        doctype="account",
        model=Accounts,
        search_fields=("code", "name"),
        value_field="id",
        label_builder=_account_label,
        allowed_filters={"company": "entity", "account_type": "account_type", "is_active": "active"},
        default_filters={"group": False, "active": True, "enabled": True},
    ),
    "customer": SearchSelectSpec(
        doctype="customer",
        model=Party,
        search_fields=("name", "comercial_name", "tax_id"),
        value_field="id",
        label_builder=_party_label,
        allowed_filters={"company": "company", "party_type": "party_type", "is_active": "is_active"},
        default_filters={"party_type": "customer", "is_active": True},
    ),
    "supplier": SearchSelectSpec(
        doctype="supplier",
        model=Party,
        search_fields=("name", "comercial_name", "tax_id"),
        value_field="id",
        label_builder=_party_label,
        allowed_filters={"company": "company", "party_type": "party_type", "is_active": "is_active"},
        default_filters={"party_type": "supplier", "is_active": True},
    ),
    "item": SearchSelectSpec(
        doctype="item",
        model=Item,
        search_fields=("code", "name", "description"),
        value_field="code",
        label_builder=_item_label,
        allowed_filters={"is_active": "is_active", "item_type": "item_type", "is_stock_item": "is_stock_item"},
        default_filters={"is_active": True},
    ),
    "warehouse": SearchSelectSpec(
        doctype="warehouse",
        model=Warehouse,
        search_fields=("code", "name"),
        value_field="code",
        label_builder=_warehouse_label,
        allowed_filters={"company": "company", "is_active": "is_active"},
        default_filters={"is_group": False, "is_active": True},
    ),
    "bank_account": SearchSelectSpec(
        doctype="bank_account",
        model=BankAccount,
        search_fields=("account_name", "account_no", "iban"),
        value_field="id",
        label_builder=_bank_account_label,
        allowed_filters={"company": "company", "is_active": "is_active"},
        default_filters={"is_active": True},
    ),
    "naming_series": SearchSelectSpec(
        doctype="naming_series",
        model=NamingSeries,
        search_fields=("name", "entity_type", "prefix_template"),
        value_field="id",
        label_builder=_naming_series_label,
        allowed_filters={"company": "company", "entity_type": "entity_type", "is_active": "is_active"},
        default_filters={"is_active": True},
    ),
}


def search_select(doctype: str, query: str, filters: dict[str, list[str]], limit: int | None = None) -> dict[str, Any]:
    """Busca opciones para un doctype registrado y devuelve un payload uniforme."""
    spec = SEARCH_SELECT_REGISTRY.get(doctype)
    if spec is None:
        raise SearchSelectError("Tipo de seleccion no registrado.", 404)

    rejected_filters = sorted(set(filters) - set(spec.allowed_filters))
    if rejected_filters:
        raise SearchSelectError("Filtros no permitidos: " + ", ".join(rejected_filters))

    max_results = _normalize_limit(limit, spec.limit)
    normalized_query = query.strip()
    if not normalized_query:
        return {"doctype": doctype, "query": normalized_query, "results": [], "has_more": False}

    statement = select(spec.model)
    if spec.model is Party and filters.get("company"):
        statement = statement.join(CompanyParty, CompanyParty.party_id == Party.id)
        statement = statement.where(CompanyParty.is_active.is_(True))

    statement = _apply_default_filters(statement, spec)
    statement = _apply_request_filters(statement, spec, filters)
    statement = _apply_search(statement, spec, normalized_query)
    statement = statement.limit(max_results + 1)

    rows = database.session.execute(statement).scalars().all()
    visible_rows = rows[:max_results]
    return {
        "doctype": doctype,
        "query": normalized_query,
        "results": [_serialize_result(spec, row) for row in visible_rows],
        "has_more": len(rows) > max_results,
    }


def _normalize_limit(limit: int | None, default_limit: int) -> int:
    if limit is None:
        return default_limit
    if limit < 1:
        raise SearchSelectError("El limite debe ser mayor que cero.")
    return min(limit, 50)


def _apply_default_filters(statement: Select[tuple[Any]], spec: SearchSelectSpec) -> Select[tuple[Any]]:
    for field, value in spec.default_filters.items():
        column = _column_for(spec.model, field)
        statement = statement.where(_condition_for(column, [str(value)] if isinstance(value, str) else [value]))
    return statement


def _apply_request_filters(
    statement: Select[tuple[Any]], spec: SearchSelectSpec, filters: dict[str, list[str]]
) -> Select[tuple[Any]]:
    for filter_name, values in filters.items():
        clean_values = [value for value in values if value != ""]
        if not clean_values:
            continue
        if spec.model is Party and filter_name == "company":
            statement = statement.where(CompanyParty.company.in_(clean_values))
            continue
        column = _column_for(spec.model, spec.allowed_filters[filter_name])
        statement = statement.where(_condition_for(column, clean_values))
    return statement


def _apply_search(statement: Select[tuple[Any]], spec: SearchSelectSpec, query: str) -> Select[tuple[Any]]:
    like_query = f"%{query.lower()}%"
    prefix_query = f"{query.lower()}%"
    searchable_columns = [_column_for(spec.model, field) for field in spec.search_fields]
    search_conditions = [func.lower(cast(column, database.String)).like(like_query) for column in searchable_columns]
    prefix_conditions = [func.lower(cast(column, database.String)).like(prefix_query) for column in searchable_columns]
    priority = case((or_(*prefix_conditions), 0), else_=1)
    first_sort = searchable_columns[0]
    return statement.where(or_(*search_conditions)).order_by(priority, first_sort)


def _condition_for(column: InstrumentedAttribute[Any], values: Sequence[str | bool]) -> Any:
    if not values:
        return true()
    if all(isinstance(value, bool) for value in values):
        return column.is_(values[0])
    normalized_values = [_normalize_filter_value(value) for value in values]
    if len(normalized_values) == 1:
        value = normalized_values[0]
        if isinstance(value, bool):
            return column.is_(value)
        return column == value
    return column.in_(normalized_values)


def _normalize_filter_value(value: str | bool) -> str | bool:
    if isinstance(value, bool):
        return value
    match value.strip().lower():
        case "true" | "1" | "yes" | "si" | "sí":
            return True
        case "false" | "0" | "no":
            return False
        case "__empty__":
            return ""
        case other:
            return other if other == value else value


def _column_for(model: type[Any], field: str) -> InstrumentedAttribute[Any]:
    column = getattr(model, field, None)
    if column is None:
        raise SearchSelectError("Filtro no disponible para este tipo de seleccion.")
    return column


def _serialize_result(spec: SearchSelectSpec, row: Any) -> dict[str, Any]:
    value = str(getattr(row, spec.value_field))
    label = spec.label_builder(row)
    payload: dict[str, Any] = {"id": value, "value": value, "label": label, "display_name": label}
    for field in ("code", "name", "account_type", "party_type", "item_type", "account_name", "account_no", "entity_type"):
        if hasattr(row, field):
            payload[field] = getattr(row, field)
    return payload
