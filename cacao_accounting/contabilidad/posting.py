# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Motor de posting contable para generar entradas GL desde documentos."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select

from cacao_accounting.database import (
    Accounts,
    AccountingPeriod,
    Book,
    GLEntry,
    ItemAccount,
    PartyAccount,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    SalesInvoice,
    SalesInvoiceItem,
    StockEntry,
    StockEntryItem,
    PaymentEntry,
    database,
)
from cacao_accounting.document_identifiers import validate_accounting_period


class PostingError(ValueError):
    """Error controlado del motor de posting contable."""


def _decimal_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise PostingError("Valor monetario invalido para contabilizacion.") from exc


def _validate_gl_entry_balance(debit: Decimal, credit: Decimal) -> None:
    if debit < 0 or credit < 0:
        raise PostingError("Los montos de debito y credito deben ser no negativos.")
    if not ((debit > 0 and credit == 0) or (debit == 0 and credit > 0)):
        raise PostingError("Cada asiento GL debe tener un debito o un credito positivo, no ambos.")


def _resolve_book_id(company: str, ledger_code: str | None = None) -> str | None:
    query = select(Book).filter_by(entity=company)
    if ledger_code:
        query = query.filter_by(code=ledger_code)
    else:
        query = query.order_by(Book.is_primary.desc())
    book = database.session.execute(query).scalars().first()
    return book.id if book else None


def _account_code_for(account_id: str | None) -> str | None:
    if not account_id:
        return None
    account = database.session.get(Accounts, account_id)
    return getattr(account, "code", None)


def _resolve_party_account_id(party_id: str | None, company: str, receivable: bool) -> str | None:
    if not party_id:
        return None
    mapping = database.session.execute(
        select(PartyAccount).filter_by(party_id=party_id, company=company)
    ).scalars().first()
    if not mapping:
        return None
    return mapping.receivable_account_id if receivable else mapping.payable_account_id


def _resolve_item_account_id(item_code: str | None, company: str, account_type: str) -> str | None:
    if not item_code:
        return None
    mapping = database.session.execute(
        select(ItemAccount).filter_by(item_code=item_code, company=company)
    ).scalars().first()
    if not mapping:
        return None
    if account_type == "income":
        return mapping.income_account_id
    if account_type == "expense":
        return mapping.expense_account_id
    if account_type == "inventory":
        return mapping.inventory_account_id
    return None


def _account_id_for_item(item: Any, company: str, account_type: str) -> str | None:
    explicit_field = f"{account_type}_account_id"
    if hasattr(item, explicit_field):
        value = getattr(item, explicit_field)
        if value:
            return value
    return _resolve_item_account_id(getattr(item, "item_code", None), company, account_type)


def _find_period_ids(company: str, posting_date: Any) -> tuple[str | None, str | None]:
    period = database.session.execute(
        select(AccountingPeriod)
        .filter_by(entity=company, enabled=True)
        .where(AccountingPeriod.start <= posting_date)
        .where(AccountingPeriod.end >= posting_date)
    ).scalars().first()
    if not period:
        return None, None
    return period.id, period.fiscal_year_id


def _get_voucher_type(document: Any) -> str:
    return str(getattr(document, "voucher_type", None) or getattr(document, "__tablename__", ""))


def _get_voucher_id(document: Any) -> str:
    return str(getattr(document, "voucher_id", None) or getattr(document, "id", ""))


def _create_gl_entry(
    *,
    company: str,
    posting_date: Any,
    ledger_id: str | None,
    account_id: str | None,
    debit: Decimal,
    credit: Decimal,
    voucher_type: str,
    voucher_id: str,
    document_no: str | None,
    naming_series_id: str | None,
    party_type: str | None = None,
    party_id: str | None = None,
    cost_center_code: str | None = None,
    unit_code: str | None = None,
    project_code: str | None = None,
    document_remarks: str | None = None,
    entry_remarks: str | None = None,
    accounting_period_id: str | None = None,
    fiscal_year_id: str | None = None,
    transaction_currency: str | None = None,
    company_currency: str | None = None,
    exchange_rate: Any = None,
) -> GLEntry:
    _validate_gl_entry_balance(debit, credit)
    account_code = _account_code_for(account_id)

    return GLEntry(
        posting_date=posting_date,
        company=company,
        ledger_id=ledger_id,
        account_id=account_id,
        account_code=account_code,
        debit=debit,
        credit=credit,
        debit_in_account_currency=debit if transaction_currency else None,
        credit_in_account_currency=credit if transaction_currency else None,
        account_currency=transaction_currency,
        company_currency=company_currency,
        exchange_rate=_decimal_value(exchange_rate) if exchange_rate is not None else None,
        party_type=party_type,
        party_id=party_id,
        voucher_type=voucher_type,
        voucher_id=voucher_id,
        document_no=document_no,
        naming_series_id=naming_series_id,
        fiscal_year_id=fiscal_year_id,
        accounting_period_id=accounting_period_id,
        cost_center_code=cost_center_code,
        unit_code=unit_code,
        project_code=project_code,
        remarks=entry_remarks if entry_remarks is not None else document_remarks,
    )


def _post_entries(entries: list[GLEntry]) -> list[GLEntry]:
    if not entries:
        raise PostingError("No se generan entradas contables para este documento.")
    database.session.add_all(entries)
    return entries


def _document_posting_context(document: Any, ledger_code: str | None = None) -> dict[str, Any]:
    if not getattr(document, "company", None):
        raise PostingError("El documento no tiene compañia definida.")
    if not getattr(document, "posting_date", None):
        raise PostingError("El documento no tiene fecha de contabilizacion definida.")
    validate_accounting_period(document.company, document.posting_date)
    ledger_id = _resolve_book_id(document.company, ledger_code)
    accounting_period_id, fiscal_year_id = _find_period_ids(document.company, document.posting_date)
    return {
        "company": document.company,
        "posting_date": document.posting_date,
        "ledger_id": ledger_id,
        "voucher_type": _get_voucher_type(document),
        "voucher_id": _get_voucher_id(document),
        "document_no": getattr(document, "document_no", None),
        "naming_series_id": getattr(document, "naming_series_id", None),
        "party_type": getattr(document, "party_type", None),
        "party_id": getattr(document, "party_id", None),
        "accounting_period_id": accounting_period_id,
        "fiscal_year_id": fiscal_year_id,
        "transaction_currency": getattr(document, "transaction_currency", None),
        "company_currency": getattr(document, "base_currency", None),
        "exchange_rate": getattr(document, "exchange_rate", None),
        "document_remarks": getattr(document, "remarks", None),
    }


def post_sales_invoice(document: SalesInvoice, ledger_code: str | None = None) -> list[GLEntry]:
    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede contabilizar una factura de venta aprobada.")

    context = _document_posting_context(document, ledger_code=ledger_code)
    receivable_account_id = _resolve_party_account_id(document.customer_id, document.company, receivable=True)
    if not receivable_account_id:
        raise PostingError("No existe cuenta por cobrar configurada para el cliente.")

    items = database.session.execute(
        select(SalesInvoiceItem).filter_by(sales_invoice_id=document.id)
    ).scalars().all()
    if not items:
        raise PostingError("La factura de venta no contiene lineas para contabilizar.")

    amount_total = Decimal("0")
    entries: list[GLEntry] = []
    for item in items:
        amount = _decimal_value(getattr(item, "amount", None))
        if amount <= 0:
            continue
        income_account_id = _account_id_for_item(item, document.company, "income")
        if not income_account_id:
            raise PostingError("Falta la cuenta de ingresos para una linea de factura de venta.")
        amount_total += amount
        entries.append(
            _create_gl_entry(
                **context,
                account_id=income_account_id,
                debit=Decimal("0"),
                credit=amount,
                entry_remarks=getattr(item, "item_name", None) or getattr(item, "item_code", None),
            )
        )

    if amount_total <= 0:
        raise PostingError("El total de la factura de venta es cero y no puede contabilizarse.")

    entries.insert(
        0,
        _create_gl_entry(
            **context,
            account_id=receivable_account_id,
            debit=amount_total,
            credit=Decimal("0"),
            entry_remarks="Cuentas por cobrar",
        ),
    )

    return _post_entries(entries)


def post_purchase_invoice(document: PurchaseInvoice, ledger_code: str | None = None) -> list[GLEntry]:
    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede contabilizar una factura de compra aprobada.")

    context = _document_posting_context(document, ledger_code=ledger_code)
    payable_account_id = _resolve_party_account_id(document.supplier_id, document.company, receivable=False)
    if not payable_account_id:
        raise PostingError("No existe cuenta por pagar configurada para el proveedor.")

    items = database.session.execute(
        select(PurchaseInvoiceItem).filter_by(purchase_invoice_id=document.id)
    ).scalars().all()
    if not items:
        raise PostingError("La factura de compra no contiene lineas para contabilizar.")

    amount_total = Decimal("0")
    entries: list[GLEntry] = []
    for item in items:
        amount = _decimal_value(getattr(item, "amount", None))
        if amount <= 0:
            continue
        expense_account_id = _account_id_for_item(item, document.company, "expense")
        if not expense_account_id:
            raise PostingError("Falta la cuenta de gastos para una linea de factura de compra.")
        amount_total += amount
        entries.append(
            _create_gl_entry(
                **context,
                account_id=expense_account_id,
                debit=amount,
                credit=Decimal("0"),
                entry_remarks=getattr(item, "item_name", None) or getattr(item, "item_code", None),
            )
        )

    if amount_total <= 0:
        raise PostingError("El total de la factura de compra es cero y no puede contabilizarse.")

    entries.append(
        _create_gl_entry(
            **context,
            account_id=payable_account_id,
            debit=Decimal("0"),
            credit=amount_total,
            entry_remarks="Cuentas por pagar",
        )
    )

    return _post_entries(entries)


def post_payment_entry(document: PaymentEntry, ledger_code: str | None = None) -> list[GLEntry]:
    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede contabilizar un pago aprobado.")

    context = _document_posting_context(document, ledger_code=ledger_code)
    amount = _decimal_value(document.paid_amount or document.received_amount)
    if amount <= 0:
        raise PostingError("El monto del pago debe ser mayor que cero.")

    payment_type = getattr(document, "payment_type", "").lower()
    if payment_type == "pay":
        payable_account_id = _resolve_party_account_id(document.party_id, document.company, receivable=False)
        if not payable_account_id:
            raise PostingError("No existe cuenta por pagar configurada para el proveedor.")
        bank_account_id = getattr(document, "paid_from_account_id", None)
        if not bank_account_id:
            raise PostingError("El pago no tiene una cuenta de origen configurada.")
        entries = [
            _create_gl_entry(
                **context,
                account_id=payable_account_id,
                debit=amount,
                credit=Decimal("0"),
                entry_remarks="Pago a proveedor",
            ),
            _create_gl_entry(
                **context,
                account_id=bank_account_id,
                debit=Decimal("0"),
                credit=amount,
                entry_remarks="Cuenta bancaria de pago",
            ),
        ]
    elif payment_type == "receive":
        receivable_account_id = _resolve_party_account_id(document.party_id, document.company, receivable=True)
        if not receivable_account_id:
            raise PostingError("No existe cuenta por cobrar configurada para el cliente.")
        bank_account_id = getattr(document, "paid_to_account_id", None)
        if not bank_account_id:
            raise PostingError("El pago no tiene una cuenta de destino configurada.")
        entries = [
            _create_gl_entry(
                **context,
                account_id=bank_account_id,
                debit=amount,
                credit=Decimal("0"),
                entry_remarks="Cuenta bancaria receptora",
            ),
            _create_gl_entry(
                **context,
                account_id=receivable_account_id,
                debit=Decimal("0"),
                credit=amount,
                entry_remarks="Cobro de cliente",
            ),
        ]
    elif payment_type == "internal_transfer":
        from_account_id = getattr(document, "paid_from_account_id", None)
        to_account_id = getattr(document, "paid_to_account_id", None)
        if not from_account_id or not to_account_id:
            raise PostingError("La transferencia interna requiere cuenta de origen y destino.")
        entries = [
            _create_gl_entry(
                **context,
                account_id=to_account_id,
                debit=amount,
                credit=Decimal("0"),
                entry_remarks="Transferencia interna entrada",
            ),
            _create_gl_entry(
                **context,
                account_id=from_account_id,
                debit=Decimal("0"),
                credit=amount,
                entry_remarks="Transferencia interna salida",
            ),
        ]
    else:
        raise PostingError("Tipo de pago no soportado para contabilizacion.")

    return _post_entries(entries)


def post_stock_entry(document: StockEntry, ledger_code: str | None = None) -> list[GLEntry]:
    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede contabilizar una entrada de stock aprobada.")

    context = _document_posting_context(document, ledger_code=ledger_code)
    purpose = getattr(document, "purpose", "").lower()
    supported_purposes = {"material_receipt", "material_issue"}
    if purpose not in supported_purposes:
        raise PostingError("Solo se contabilizan ingresos y egresos de material en el libro mayor.")

    items = database.session.execute(
        select(StockEntryItem).filter_by(stock_entry_id=document.id)
    ).scalars().all()
    if not items:
        raise PostingError("La entrada de stock no contiene lineas para contabilizar.")

    entries: list[GLEntry] = []
    for item in items:
        amount = _decimal_value(getattr(item, "amount", None))
        if amount <= 0:
            continue
        inventory_account_id = _account_id_for_item(item, document.company, "inventory")
        expense_account_id = _account_id_for_item(item, document.company, "expense")
        if not inventory_account_id or not expense_account_id:
            raise PostingError("Faltan cuentas de inventario o gasto para la linea de stock.")
        if purpose == "material_receipt":
            entries.append(
                _create_gl_entry(
                    **context,
                    account_id=inventory_account_id,
                    debit=amount,
                    credit=Decimal("0"),
                    entry_remarks="Ingreso de inventario",
                )
            )
            entries.append(
                _create_gl_entry(
                    **context,
                    account_id=expense_account_id,
                    debit=Decimal("0"),
                    credit=amount,
                    entry_remarks="Consumo de inventario",
                )
            )
        else:
            entries.append(
                _create_gl_entry(
                    **context,
                    account_id=expense_account_id,
                    debit=amount,
                    credit=Decimal("0"),
                    entry_remarks="Costo de material",
                )
            )
            entries.append(
                _create_gl_entry(
                    **context,
                    account_id=inventory_account_id,
                    debit=Decimal("0"),
                    credit=amount,
                    entry_remarks="Salida de inventario",
                )
            )

    return _post_entries(entries)


def post_document_to_gl(document: Any, ledger_code: str | None = None) -> list[GLEntry]:
    if isinstance(document, SalesInvoice):
        return post_sales_invoice(document, ledger_code=ledger_code)
    if isinstance(document, PurchaseInvoice):
        return post_purchase_invoice(document, ledger_code=ledger_code)
    if isinstance(document, PaymentEntry):
        return post_payment_entry(document, ledger_code=ledger_code)
    if isinstance(document, StockEntry):
        return post_stock_entry(document, ledger_code=ledger_code)

    raise PostingError("Tipo de documento no soportado para posting contable.")
