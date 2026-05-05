# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Servicios de contabilizacion para documentos operativos."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Sequence

from sqlalchemy import func, select

from cacao_accounting.database import (
    Accounts,
    AccountingPeriod,
    BankAccount,
    Book,
    CompanyDefaultAccount,
    GLEntry,
    Item,
    ItemAccount,
    PartyAccount,
    PaymentEntry,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    SalesInvoice,
    SalesInvoiceItem,
    StockBin,
    StockEntry,
    StockEntryItem,
    StockLedgerEntry,
    StockValuationLayer,
    database,
)
from cacao_accounting.document_identifiers import validate_accounting_period


class PostingError(ValueError):
    """Error controlado del motor de contabilizacion."""


@dataclass(frozen=True)
class LedgerContext:
    """Contexto comun para generar lineas contables por libro."""

    company: str
    posting_date: Any
    ledger_id: str | None
    voucher_type: str
    voucher_id: str
    document_no: str | None
    naming_series_id: str | None
    accounting_period_id: str | None
    fiscal_year_id: str | None
    transaction_currency: str | None
    company_currency: str | None
    exchange_rate: Decimal | None
    document_remarks: str | None


def _decimal_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise PostingError("Valor numerico invalido para contabilizacion.") from exc


def _validate_single_sided_amount(debit: Decimal, credit: Decimal) -> None:
    if debit < 0 or credit < 0:
        raise PostingError("Los montos de debito y credito deben ser no negativos.")
    if not ((debit > 0 and credit == 0) or (debit == 0 and credit > 0)):
        raise PostingError("Cada entrada GL debe tener un debito o un credito positivo, no ambos.")


def _get_voucher_type(document: Any) -> str:
    return str(getattr(document, "voucher_type", None) or getattr(document, "__tablename__", ""))


def _get_voucher_id(document: Any) -> str:
    return str(getattr(document, "voucher_id", None) or getattr(document, "id", ""))


def _company_for(document: Any) -> str:
    company = getattr(document, "company", None)
    if not company:
        raise PostingError("El documento no tiene compania definida.")
    return str(company)


def _posting_date_for(document: Any) -> Any:
    posting_date = getattr(document, "posting_date", None)
    if not posting_date:
        raise PostingError("El documento no tiene fecha de contabilizacion definida.")
    return posting_date


def _find_period_ids(company: str, posting_date: Any) -> tuple[str | None, str | None]:
    period = (
        database.session.execute(
            select(AccountingPeriod)
            .filter_by(entity=company, enabled=True)
            .where(AccountingPeriod.start <= posting_date)
            .where(AccountingPeriod.end >= posting_date)
        )
        .scalars()
        .first()
    )
    if not period:
        return None, None
    return period.id, period.fiscal_year_id


def _active_books(company: str, ledger_code: str | None = None) -> list[Book | None]:
    query = select(Book).filter_by(entity=company)
    if ledger_code:
        query = query.filter_by(code=ledger_code)
    books = database.session.execute(query.order_by(Book.is_primary.desc(), Book.code)).scalars().all()
    if ledger_code and not books:
        raise PostingError("El libro contable indicado no existe para la compania.")
    return list(books) if books else [None]


def _document_contexts(document: Any, ledger_code: str | None = None) -> list[LedgerContext]:
    company = _company_for(document)
    posting_date = _posting_date_for(document)
    validate_accounting_period(company, posting_date)
    accounting_period_id, fiscal_year_id = _find_period_ids(company, posting_date)
    exchange_rate = getattr(document, "exchange_rate", None)
    contexts: list[LedgerContext] = []
    for book in _active_books(company, ledger_code):
        contexts.append(
            LedgerContext(
                company=company,
                posting_date=posting_date,
                ledger_id=book.id if book else None,
                voucher_type=_get_voucher_type(document),
                voucher_id=_get_voucher_id(document),
                document_no=getattr(document, "document_no", None),
                naming_series_id=getattr(document, "naming_series_id", None),
                accounting_period_id=accounting_period_id,
                fiscal_year_id=fiscal_year_id,
                transaction_currency=getattr(document, "transaction_currency", None),
                company_currency=getattr(document, "base_currency", None) or getattr(book, "currency", None),
                exchange_rate=_decimal_value(exchange_rate) if exchange_rate is not None else None,
                document_remarks=getattr(document, "remarks", None),
            )
        )
    return contexts


def _account_code_for(account_id: str) -> str | None:
    account = database.session.get(Accounts, account_id)
    return getattr(account, "code", None)


def _require_account(account_id: str | None, message: str) -> str:
    if not account_id:
        raise PostingError(message)
    if not database.session.get(Accounts, account_id):
        raise PostingError("La cuenta contable configurada no existe.")
    return account_id


def _company_defaults(company: str) -> CompanyDefaultAccount | None:
    return database.session.execute(select(CompanyDefaultAccount).filter_by(company=company)).scalars().first()


def _resolve_party_account_id(party_id: str | None, company: str, receivable: bool) -> str | None:
    if party_id:
        mapping = (
            database.session.execute(select(PartyAccount).filter_by(party_id=party_id, company=company)).scalars().first()
        )
        if mapping:
            account_id = mapping.receivable_account_id if receivable else mapping.payable_account_id
            if account_id:
                return account_id
    defaults = _company_defaults(company)
    if not defaults:
        return None
    return defaults.default_receivable if receivable else defaults.default_payable


def _resolve_item_account_id(item_code: str | None, company: str, account_type: str) -> str | None:
    if item_code:
        mapping = (
            database.session.execute(select(ItemAccount).filter_by(item_code=item_code, company=company)).scalars().first()
        )
        if mapping:
            mapped = {
                "income": mapping.income_account_id,
                "expense": mapping.expense_account_id,
                "inventory": mapping.inventory_account_id,
            }.get(account_type)
            if mapped:
                return mapped

    defaults = _company_defaults(company)
    if not defaults:
        return None
    return {
        "income": defaults.default_income,
        "expense": defaults.default_expense,
        "inventory": defaults.default_inventory,
        "gr_ir": defaults.gr_ir_account_id,
    }.get(account_type)


def _account_id_for_item(item: Any, company: str, account_type: str) -> str | None:
    explicit_field = f"{account_type}_account_id"
    if hasattr(item, explicit_field):
        value = getattr(item, explicit_field)
        if value:
            return str(value)
    return _resolve_item_account_id(getattr(item, "item_code", None), company, account_type)


def _resolve_bank_gl_account_id(document: PaymentEntry, destination: bool) -> str | None:
    explicit = document.paid_to_account_id if destination else document.paid_from_account_id
    if explicit:
        return explicit
    if document.bank_account_id:
        bank_account = database.session.get(BankAccount, document.bank_account_id)
        if bank_account and bank_account.gl_account_id:
            return bank_account.gl_account_id
    defaults = _company_defaults(_company_for(document))
    return defaults.default_bank if defaults else None


def _has_active_gl_entries(document: Any) -> bool:
    return (
        database.session.execute(
            select(GLEntry.id)
            .filter_by(
                company=_company_for(document),
                voucher_type=_get_voucher_type(document),
                voucher_id=_get_voucher_id(document),
                is_cancelled=False,
                is_reversal=False,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _has_stock_ledger_entries(document: Any) -> bool:
    return (
        database.session.execute(
            select(StockLedgerEntry.id)
            .filter_by(
                company=_company_for(document),
                voucher_type=_get_voucher_type(document),
                voucher_id=_get_voucher_id(document),
                is_cancelled=False,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _create_gl_entry(
    *,
    context: LedgerContext,
    account_id: str,
    debit: Decimal,
    credit: Decimal,
    party_type: str | None = None,
    party_id: str | None = None,
    cost_center_code: str | None = None,
    unit_code: str | None = None,
    project_code: str | None = None,
    entry_remarks: str | None = None,
    is_reversal: bool = False,
    reversal_of: str | None = None,
) -> GLEntry:
    _validate_single_sided_amount(debit, credit)
    return GLEntry(
        posting_date=context.posting_date,
        company=context.company,
        ledger_id=context.ledger_id,
        account_id=_require_account(account_id, "Toda entrada GL requiere cuenta contable."),
        account_code=_account_code_for(account_id),
        debit=debit,
        credit=credit,
        debit_in_account_currency=debit if context.transaction_currency else None,
        credit_in_account_currency=credit if context.transaction_currency else None,
        account_currency=context.transaction_currency,
        company_currency=context.company_currency,
        exchange_rate=context.exchange_rate,
        party_type=party_type,
        party_id=party_id,
        voucher_type=context.voucher_type,
        voucher_id=context.voucher_id,
        document_no=context.document_no,
        naming_series_id=context.naming_series_id,
        fiscal_year_id=context.fiscal_year_id,
        accounting_period_id=context.accounting_period_id,
        cost_center_code=cost_center_code,
        unit_code=unit_code,
        project_code=project_code,
        remarks=entry_remarks if entry_remarks is not None else context.document_remarks,
        is_reversal=is_reversal,
        reversal_of=reversal_of,
    )


def _assert_entries_balance(entries: list[GLEntry]) -> None:
    ledger_ids = {entry.ledger_id for entry in entries}
    for ledger_id in ledger_ids:
        ledger_entries = [entry for entry in entries if entry.ledger_id == ledger_id]
        debit_total = sum((_decimal_value(entry.debit) for entry in ledger_entries), Decimal("0"))
        credit_total = sum((_decimal_value(entry.credit) for entry in ledger_entries), Decimal("0"))
        if debit_total != credit_total:
            raise PostingError("Las entradas GL generadas no balancean por libro contable.")


def _add_entries(entries: list[GLEntry]) -> list[GLEntry]:
    if not entries:
        return []
    _assert_entries_balance(entries)
    database.session.add_all(entries)
    return entries


def _signed_amount(document: Any, amount: Decimal) -> Decimal:
    return -amount if getattr(document, "is_return", False) or getattr(document, "is_reversal", False) else amount


def _normal_entries_for_amount(
    *,
    context: LedgerContext,
    debit_account_id: str,
    credit_account_id: str,
    amount: Decimal,
    party_type: str | None = None,
    party_id: str | None = None,
    debit_remarks: str | None = None,
    credit_remarks: str | None = None,
) -> list[GLEntry]:
    if amount > 0:
        return [
            _create_gl_entry(
                context=context,
                account_id=debit_account_id,
                debit=amount,
                credit=Decimal("0"),
                party_type=party_type,
                party_id=party_id,
                entry_remarks=debit_remarks,
            ),
            _create_gl_entry(
                context=context,
                account_id=credit_account_id,
                debit=Decimal("0"),
                credit=amount,
                entry_remarks=credit_remarks,
            ),
        ]
    if amount < 0:
        reversed_amount = abs(amount)
        return [
            _create_gl_entry(
                context=context,
                account_id=credit_account_id,
                debit=reversed_amount,
                credit=Decimal("0"),
                entry_remarks=credit_remarks,
            ),
            _create_gl_entry(
                context=context,
                account_id=debit_account_id,
                debit=Decimal("0"),
                credit=reversed_amount,
                party_type=party_type,
                party_id=party_id,
                entry_remarks=debit_remarks,
            ),
        ]
    return []


def _invoice_items_total(items: Sequence[Any], document: Any) -> Decimal:
    total = sum((_decimal_value(getattr(item, "amount", None)) for item in items), Decimal("0"))
    signed_total = _signed_amount(document, total)
    if signed_total == 0:
        raise PostingError("El total del documento es cero y no puede contabilizarse.")
    return signed_total


def post_sales_invoice(document: SalesInvoice, ledger_code: str | None = None) -> list[GLEntry]:
    """Genera GL para una factura o nota de venta aprobada."""

    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede contabilizar una factura de venta aprobada.")

    company = _company_for(document)
    receivable_account_id = _require_account(
        _resolve_party_account_id(document.customer_id, company, receivable=True),
        "No existe cuenta por cobrar configurada para el cliente.",
    )
    items = database.session.execute(select(SalesInvoiceItem).filter_by(sales_invoice_id=document.id)).scalars().all()
    if not items:
        raise PostingError("La factura de venta no contiene lineas para contabilizar.")

    entries: list[GLEntry] = []
    for context in _document_contexts(document, ledger_code=ledger_code):
        amount_total = _invoice_items_total(items, document)
        if amount_total > 0:
            entries.append(
                _create_gl_entry(
                    context=context,
                    account_id=receivable_account_id,
                    debit=amount_total,
                    credit=Decimal("0"),
                    party_type="customer",
                    party_id=document.customer_id,
                    entry_remarks="Cuentas por cobrar",
                )
            )
        else:
            entries.append(
                _create_gl_entry(
                    context=context,
                    account_id=receivable_account_id,
                    debit=Decimal("0"),
                    credit=abs(amount_total),
                    party_type="customer",
                    party_id=document.customer_id,
                    entry_remarks="Cuentas por cobrar",
                )
            )

        for item in items:
            amount = _signed_amount(document, _decimal_value(getattr(item, "amount", None)))
            if amount == 0:
                continue
            income_account_id = _require_account(
                _account_id_for_item(item, company, "income"),
                "Falta la cuenta de ingresos para una linea de factura de venta.",
            )
            if amount > 0:
                entries.append(
                    _create_gl_entry(
                        context=context,
                        account_id=income_account_id,
                        debit=Decimal("0"),
                        credit=amount,
                        entry_remarks=getattr(item, "item_name", None) or getattr(item, "item_code", None),
                    )
                )
            else:
                entries.append(
                    _create_gl_entry(
                        context=context,
                        account_id=income_account_id,
                        debit=abs(amount),
                        credit=Decimal("0"),
                        entry_remarks=getattr(item, "item_name", None) or getattr(item, "item_code", None),
                    )
                )

    return _add_entries(entries)


def post_purchase_invoice(document: PurchaseInvoice, ledger_code: str | None = None) -> list[GLEntry]:
    """Genera GL para una factura o nota de compra aprobada."""

    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede contabilizar una factura de compra aprobada.")

    company = _company_for(document)
    payable_account_id = _require_account(
        _resolve_party_account_id(document.supplier_id, company, receivable=False),
        "No existe cuenta por pagar configurada para el proveedor.",
    )
    items = database.session.execute(select(PurchaseInvoiceItem).filter_by(purchase_invoice_id=document.id)).scalars().all()
    if not items:
        raise PostingError("La factura de compra no contiene lineas para contabilizar.")

    entries: list[GLEntry] = []
    for context in _document_contexts(document, ledger_code=ledger_code):
        amount_total = _invoice_items_total(items, document)
        for item in items:
            amount = _signed_amount(document, _decimal_value(getattr(item, "amount", None)))
            if amount == 0:
                continue
            debit_account_type = "gr_ir" if getattr(document, "purchase_receipt_id", None) else "expense"
            debit_account_id = _require_account(
                _account_id_for_item(item, company, debit_account_type),
                "Falta la cuenta de gasto o GR/IR para una linea de factura de compra.",
            )
            if amount > 0:
                entries.append(
                    _create_gl_entry(
                        context=context,
                        account_id=debit_account_id,
                        debit=amount,
                        credit=Decimal("0"),
                        entry_remarks=getattr(item, "item_name", None) or getattr(item, "item_code", None),
                    )
                )
            else:
                entries.append(
                    _create_gl_entry(
                        context=context,
                        account_id=debit_account_id,
                        debit=Decimal("0"),
                        credit=abs(amount),
                        entry_remarks=getattr(item, "item_name", None) or getattr(item, "item_code", None),
                    )
                )

        if amount_total > 0:
            entries.append(
                _create_gl_entry(
                    context=context,
                    account_id=payable_account_id,
                    debit=Decimal("0"),
                    credit=amount_total,
                    party_type="supplier",
                    party_id=document.supplier_id,
                    entry_remarks="Cuentas por pagar",
                )
            )
        else:
            entries.append(
                _create_gl_entry(
                    context=context,
                    account_id=payable_account_id,
                    debit=abs(amount_total),
                    credit=Decimal("0"),
                    party_type="supplier",
                    party_id=document.supplier_id,
                    entry_remarks="Cuentas por pagar",
                )
            )

    return _add_entries(entries)


def post_payment_entry(document: PaymentEntry, ledger_code: str | None = None) -> list[GLEntry]:
    """Genera GL para cobros, pagos y transferencias internas."""

    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede contabilizar un pago aprobado.")

    company = _company_for(document)
    amount = _decimal_value(document.paid_amount or document.received_amount)
    if amount <= 0:
        raise PostingError("El monto del pago debe ser mayor que cero.")

    payment_type = getattr(document, "payment_type", "").lower()
    entries: list[GLEntry] = []
    for context in _document_contexts(document, ledger_code=ledger_code):
        if payment_type == "pay":
            payable_account_id = _require_account(
                _resolve_party_account_id(document.party_id, company, receivable=False),
                "No existe cuenta por pagar configurada para el proveedor.",
            )
            bank_account_id = _require_account(
                _resolve_bank_gl_account_id(document, destination=False),
                "El pago no tiene una cuenta bancaria de origen configurada.",
            )
            entries.extend(
                _normal_entries_for_amount(
                    context=context,
                    debit_account_id=payable_account_id,
                    credit_account_id=bank_account_id,
                    amount=amount,
                    party_type="supplier",
                    party_id=document.party_id,
                    debit_remarks="Pago a proveedor",
                    credit_remarks="Cuenta bancaria de pago",
                )
            )
        elif payment_type == "receive":
            receivable_account_id = _require_account(
                _resolve_party_account_id(document.party_id, company, receivable=True),
                "No existe cuenta por cobrar configurada para el cliente.",
            )
            bank_account_id = _require_account(
                _resolve_bank_gl_account_id(document, destination=True),
                "El pago no tiene una cuenta bancaria de destino configurada.",
            )
            entries.extend(
                [
                    _create_gl_entry(
                        context=context,
                        account_id=bank_account_id,
                        debit=amount,
                        credit=Decimal("0"),
                        entry_remarks="Cuenta bancaria receptora",
                    ),
                    _create_gl_entry(
                        context=context,
                        account_id=receivable_account_id,
                        debit=Decimal("0"),
                        credit=amount,
                        party_type="customer",
                        party_id=document.party_id,
                        entry_remarks="Cobro de cliente",
                    ),
                ]
            )
        elif payment_type == "internal_transfer":
            from_account_id = _require_account(
                _resolve_bank_gl_account_id(document, destination=False),
                "La transferencia interna requiere cuenta bancaria de origen.",
            )
            to_account_id = _require_account(
                _resolve_bank_gl_account_id(document, destination=True),
                "La transferencia interna requiere cuenta bancaria de destino.",
            )
            entries.extend(
                _normal_entries_for_amount(
                    context=context,
                    debit_account_id=to_account_id,
                    credit_account_id=from_account_id,
                    amount=amount,
                    debit_remarks="Transferencia interna entrada",
                    credit_remarks="Transferencia interna salida",
                )
            )
        else:
            raise PostingError("Tipo de pago no soportado para contabilizacion.")

    return _add_entries(entries)


def _stock_item_for(line: StockEntryItem) -> Item:
    item = database.session.get(Item, line.item_code)
    if item is None:
        item = database.session.execute(select(Item).filter_by(code=line.item_code)).scalars().first()
    if not item:
        raise PostingError("La linea de inventario referencia un item inexistente.")
    if item.item_type == "service" or not item.is_stock_item:
        raise PostingError("Solo los bienes inventariables pueden generar Stock Ledger.")
    if item.has_batch and not line.batch_id:
        raise PostingError("El item requiere lote para generar movimiento de inventario.")
    if item.has_serial_no and not line.serial_no:
        raise PostingError("El item requiere numero de serie para generar movimiento de inventario.")
    return item


def _line_qty(line: StockEntryItem) -> Decimal:
    qty = _decimal_value(line.qty_in_base_uom or line.qty)
    if qty <= 0:
        raise PostingError("La cantidad de inventario debe ser mayor que cero.")
    return qty


def _line_rate(line: StockEntryItem) -> Decimal:
    rate = _decimal_value(line.valuation_rate or line.basic_rate)
    if rate <= 0:
        amount = _decimal_value(line.amount)
        qty = _line_qty(line)
        if amount > 0 and qty > 0:
            rate = amount / qty
    if rate <= 0:
        raise PostingError("La linea de inventario requiere tasa de valuacion.")
    return rate


def _stock_qty_after(company: str, item_code: str, warehouse: str, qty_change: Decimal) -> Decimal:
    current = database.session.execute(
        select(func.coalesce(func.sum(StockLedgerEntry.qty_change), 0)).filter_by(
            company=company, item_code=item_code, warehouse=warehouse, is_cancelled=False
        )
    ).scalar_one()
    return _decimal_value(current) + qty_change


def _upsert_stock_bin(
    *,
    company: str,
    item_code: str,
    warehouse: str,
    qty_change: Decimal,
    valuation_rate: Decimal,
    value_change: Decimal,
) -> None:
    bin_row = (
        database.session.execute(select(StockBin).filter_by(company=company, item_code=item_code, warehouse=warehouse))
        .scalars()
        .first()
    )
    if not bin_row:
        bin_row = StockBin(company=company, item_code=item_code, warehouse=warehouse, actual_qty=Decimal("0"))
        database.session.add(bin_row)
    bin_row.actual_qty = _decimal_value(bin_row.actual_qty) + qty_change
    bin_row.valuation_rate = valuation_rate
    bin_row.stock_value = _decimal_value(bin_row.stock_value) + value_change


def _create_stock_movement(
    *,
    document: StockEntry,
    line: StockEntryItem,
    warehouse: str | None,
    qty_change: Decimal,
    valuation_rate: Decimal,
    value_change: Decimal,
) -> StockLedgerEntry:
    if not warehouse:
        raise PostingError("La linea de inventario requiere almacen.")
    qty_after = _stock_qty_after(document.company, line.item_code, warehouse, qty_change)
    _upsert_stock_bin(
        company=document.company,
        item_code=line.item_code,
        warehouse=warehouse,
        qty_change=qty_change,
        valuation_rate=valuation_rate,
        value_change=value_change,
    )
    database.session.add(
        StockValuationLayer(
            item_code=line.item_code,
            warehouse=warehouse,
            company=document.company,
            qty=qty_change,
            rate=valuation_rate,
            stock_value_difference=value_change,
            remaining_qty=max(qty_after, Decimal("0")),
            remaining_stock_value=max(qty_after * valuation_rate, Decimal("0")),
            voucher_type=_get_voucher_type(document),
            voucher_id=_get_voucher_id(document),
            posting_date=document.posting_date,
        )
    )
    return StockLedgerEntry(
        posting_date=document.posting_date,
        item_code=line.item_code,
        warehouse=warehouse,
        company=document.company,
        qty_change=qty_change,
        qty_after_transaction=qty_after,
        valuation_rate=valuation_rate,
        stock_value_difference=value_change,
        stock_value=qty_after * valuation_rate,
        voucher_type=_get_voucher_type(document),
        voucher_id=_get_voucher_id(document),
        batch_id=line.batch_id,
        serial_no=line.serial_no,
    )


def _create_stock_ledger(document: StockEntry) -> list[StockLedgerEntry]:
    if _has_stock_ledger_entries(document):
        raise PostingError("Este documento ya tiene movimientos de inventario contabilizados.")

    purpose = getattr(document, "purpose", "").lower()
    items = database.session.execute(select(StockEntryItem).filter_by(stock_entry_id=document.id)).scalars().all()
    if not items:
        raise PostingError("La entrada de stock no contiene lineas para contabilizar.")

    movements: list[StockLedgerEntry] = []
    for line in items:
        _stock_item_for(line)
        qty = _line_qty(line)
        valuation_rate = _line_rate(line)
        value = _decimal_value(line.amount) or (qty * valuation_rate)
        if purpose == "material_receipt":
            movements.append(
                _create_stock_movement(
                    document=document,
                    line=line,
                    warehouse=line.target_warehouse or document.to_warehouse,
                    qty_change=qty,
                    valuation_rate=valuation_rate,
                    value_change=value,
                )
            )
        elif purpose == "material_issue":
            movements.append(
                _create_stock_movement(
                    document=document,
                    line=line,
                    warehouse=line.source_warehouse or document.from_warehouse,
                    qty_change=-qty,
                    valuation_rate=valuation_rate,
                    value_change=-value,
                )
            )
        elif purpose == "material_transfer":
            movements.append(
                _create_stock_movement(
                    document=document,
                    line=line,
                    warehouse=line.source_warehouse or document.from_warehouse,
                    qty_change=-qty,
                    valuation_rate=valuation_rate,
                    value_change=-value,
                )
            )
            movements.append(
                _create_stock_movement(
                    document=document,
                    line=line,
                    warehouse=line.target_warehouse or document.to_warehouse,
                    qty_change=qty,
                    valuation_rate=valuation_rate,
                    value_change=value,
                )
            )
        else:
            raise PostingError("Proposito de inventario no soportado para Stock Ledger.")

    database.session.add_all(movements)
    return movements


def post_stock_entry(document: StockEntry, ledger_code: str | None = None) -> list[GLEntry]:
    """Genera Stock Ledger y GL para movimientos de inventario valuado."""

    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede contabilizar una entrada de stock aprobada.")
    if _has_active_gl_entries(document):
        raise PostingError("Este documento ya tiene entradas GL contabilizadas.")

    movements = _create_stock_ledger(document)
    purpose = getattr(document, "purpose", "").lower()
    if purpose == "material_transfer":
        return []

    company = _company_for(document)
    entries: list[GLEntry] = []
    items = database.session.execute(select(StockEntryItem).filter_by(stock_entry_id=document.id)).scalars().all()
    for context in _document_contexts(document, ledger_code=ledger_code):
        for line in items:
            amount = _decimal_value(line.amount) or (_line_qty(line) * _line_rate(line))
            if amount <= 0:
                continue
            inventory_account_id = _require_account(
                _account_id_for_item(line, company, "inventory"),
                "Falta la cuenta de inventario para la linea de stock.",
            )
            offset_type = "gr_ir" if purpose == "material_receipt" else "expense"
            offset_account_id = _require_account(
                _account_id_for_item(line, company, offset_type),
                "Falta la cuenta de contrapartida para la linea de stock.",
            )
            if purpose == "material_receipt":
                entries.extend(
                    _normal_entries_for_amount(
                        context=context,
                        debit_account_id=inventory_account_id,
                        credit_account_id=offset_account_id,
                        amount=amount,
                        debit_remarks="Ingreso de inventario",
                        credit_remarks="GR/IR",
                    )
                )
            else:
                entries.extend(
                    _normal_entries_for_amount(
                        context=context,
                        debit_account_id=offset_account_id,
                        credit_account_id=inventory_account_id,
                        amount=amount,
                        debit_remarks="Costo de material",
                        credit_remarks="Salida de inventario",
                    )
                )

    _add_entries(entries)
    if not movements and not entries:
        raise PostingError("No se generan movimientos para este documento de inventario.")
    return entries


def post_document_to_gl(document: Any, ledger_code: str | None = None) -> list[GLEntry]:
    """Genera entradas contables para un documento ya aprobado."""

    if not isinstance(document, StockEntry) and _has_active_gl_entries(document):
        raise PostingError("Este documento ya tiene entradas GL contabilizadas.")
    if isinstance(document, SalesInvoice):
        return post_sales_invoice(document, ledger_code=ledger_code)
    if isinstance(document, PurchaseInvoice):
        return post_purchase_invoice(document, ledger_code=ledger_code)
    if isinstance(document, PaymentEntry):
        return post_payment_entry(document, ledger_code=ledger_code)
    if isinstance(document, StockEntry):
        return post_stock_entry(document, ledger_code=ledger_code)
    raise PostingError("Tipo de documento no soportado para posting contable.")


def submit_document(document: Any, ledger_code: str | None = None) -> list[GLEntry]:
    """Aprueba y contabiliza un documento operativo de forma idempotente."""

    if getattr(document, "docstatus", 0) != 0:
        raise PostingError("Solo se puede aprobar un documento en borrador.")
    if _has_active_gl_entries(document):
        raise PostingError("Este documento ya tiene entradas GL contabilizadas.")
    document.docstatus = 1
    return post_document_to_gl(document, ledger_code=ledger_code)


def cancel_document(document: Any) -> list[GLEntry]:
    """Cancela un documento aprobado mediante reversos append-only."""

    if getattr(document, "docstatus", 0) != 1:
        raise PostingError("Solo se puede cancelar un documento aprobado.")

    company = _company_for(document)
    voucher_type = _get_voucher_type(document)
    voucher_id = _get_voucher_id(document)
    original_entries = (
        database.session.execute(
            select(GLEntry).filter_by(
                company=company,
                voucher_type=voucher_type,
                voucher_id=voucher_id,
                is_reversal=False,
                is_cancelled=False,
            )
        )
        .scalars()
        .all()
    )
    if not original_entries and not isinstance(document, StockEntry):
        raise PostingError("El documento no tiene entradas GL para reversar.")

    document.docstatus = 2
    reversals: list[GLEntry] = []
    for entry in original_entries:
        context = LedgerContext(
            company=entry.company,
            posting_date=_posting_date_for(document),
            ledger_id=entry.ledger_id,
            voucher_type=voucher_type,
            voucher_id=voucher_id,
            document_no=getattr(document, "document_no", None),
            naming_series_id=getattr(document, "naming_series_id", None),
            accounting_period_id=entry.accounting_period_id,
            fiscal_year_id=entry.fiscal_year_id,
            transaction_currency=entry.account_currency,
            company_currency=entry.company_currency,
            exchange_rate=entry.exchange_rate,
            document_remarks=getattr(document, "remarks", None),
        )
        reversals.append(
            _create_gl_entry(
                context=context,
                account_id=entry.account_id,
                debit=_decimal_value(entry.credit),
                credit=_decimal_value(entry.debit),
                party_type=entry.party_type,
                party_id=entry.party_id,
                cost_center_code=entry.cost_center_code,
                unit_code=entry.unit_code,
                project_code=entry.project_code,
                entry_remarks="Reversion " + (entry.remarks or ""),
                is_reversal=True,
                reversal_of=entry.id,
            )
        )
        entry.is_cancelled = True

    if isinstance(document, StockEntry):
        for movement in database.session.execute(
            select(StockLedgerEntry).filter_by(
                company=company,
                voucher_type=voucher_type,
                voucher_id=voucher_id,
                is_cancelled=False,
            )
        ).scalars():
            _upsert_stock_bin(
                company=movement.company,
                item_code=movement.item_code,
                warehouse=movement.warehouse,
                qty_change=-_decimal_value(movement.qty_change),
                valuation_rate=_decimal_value(movement.valuation_rate),
                value_change=-_decimal_value(movement.stock_value_difference),
            )
            movement.is_cancelled = True

    return _add_entries(reversals)
