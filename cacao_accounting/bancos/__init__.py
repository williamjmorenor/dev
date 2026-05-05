# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Caja y Bancos."""

# ---------------------------------------------------------------------------------------
# Libreria estandar
# --------------------------------------------------------------------------------------
from decimal import Decimal
from typing import cast

# ---------------------------------------------------------------------------------------
# Librerias de terceros
# ---------------------------------------------------------------------------------------
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

# ---------------------------------------------------------------------------------------
# Recursos locales
# ---------------------------------------------------------------------------------------
from cacao_accounting.database import (
    Bank,
    BankAccount,
    BankTransaction,
    PaymentEntry,
    PaymentReference,
    PurchaseInvoice,
    SalesInvoice,
    database,
)
from cacao_accounting.database.helpers import get_active_naming_series
from cacao_accounting.contabilidad.posting import PostingError, cancel_document, submit_document
from cacao_accounting.document_flow.status import _
from cacao_accounting.document_identifiers import IdentifierConfigurationError, assign_document_identifier
from cacao_accounting.decorators import modulo_activo
from cacao_accounting.version import APPNAME

bancos = Blueprint("bancos", __name__, template_folder="templates")


def _series_choices(entity_type: str, company: str | None) -> list[tuple[str, str]]:
    """Construye las opciones de series activas para un doctype y compania."""

    if not company:
        return [("", "")]

    return [("", "")] + [
        (str(series.id), f"{series.name} ({series.prefix_template})")
        for series in get_active_naming_series(entity_type=entity_type, company=company)
    ]


@bancos.route("/")
@bancos.route("/caja")
@bancos.route("/tesoreria")
@bancos.route("/bancos")
@bancos.route("/cash")
@modulo_activo("cash")
@login_required
def bancos_():
    """Pantalla principal del modulo de bancos."""
    return render_template("bancos.html")


@bancos.route("/bank/list")
@modulo_activo("cash")
@login_required
def bancos_banco_lista():
    """Listado de bancos."""
    consulta = database.paginate(
        database.select(Bank),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Bancos - " + APPNAME
    return render_template("bancos/banco_lista.html", consulta=consulta, titulo=titulo)


@bancos.route("/bank-account/list")
@modulo_activo("cash")
@login_required
def bancos_cuenta_bancaria_lista():
    """Listado de cuentas bancarias."""
    consulta = database.paginate(
        database.select(BankAccount),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Cuentas Bancarias - " + APPNAME
    return render_template("bancos/banco_cuenta_lista.html", consulta=consulta, titulo=titulo)


@bancos.route("/payment/list")
@modulo_activo("cash")
@login_required
def bancos_pago_lista():
    """Listado de entradas de pago."""
    consulta = database.paginate(
        database.select(PaymentEntry),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Pagos - " + APPNAME
    return render_template("bancos/pago_lista.html", consulta=consulta, titulo=titulo)


@bancos.route("/bank-transaction/list")
@modulo_activo("cash")
@login_required
def bancos_transaccion_lista():
    """Listado de transacciones bancarias."""
    consulta = database.paginate(
        database.select(BankTransaction),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Transacciones Bancarias - " + APPNAME
    return render_template("bancos/transaccion_lista.html", consulta=consulta, titulo=titulo)


@bancos.route("/bank/new", methods=["GET", "POST"])
@modulo_activo("cash")
@login_required
def bancos_banco_nuevo():
    """Formulario para crear un nuevo banco."""
    from cacao_accounting.bancos.forms import FormularioBanco

    formulario = FormularioBanco()
    titulo = "Nuevo Banco - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        banco = Bank(
            name=request.form.get("name"),
            swift_code=request.form.get("swift_code"),
        )
        database.session.add(banco)
        database.session.commit()
        return redirect("/cash_management/bank/list")
    return render_template("bancos/banco_nuevo.html", form=formulario, titulo=titulo)


@bancos.route("/bank/<bank_id>")
@modulo_activo("cash")
@login_required
def bancos_banco(bank_id):
    """Detalle de banco."""
    from flask import abort

    registro = database.session.get(Bank, bank_id)
    if not registro:
        abort(404)
    titulo = registro.name + " - " + APPNAME
    return render_template("bancos/banco.html", registro=registro, titulo=titulo)


@bancos.route("/bank-account/new", methods=["GET", "POST"])
@modulo_activo("cash")
@login_required
def bancos_cuenta_bancaria_nuevo():
    """Formulario para crear una nueva cuenta bancaria."""
    from cacao_accounting.bancos.forms import FormularioCuentaBancaria
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial, obtener_lista_monedas

    formulario = FormularioCuentaBancaria()
    formulario.bank_id.choices = [(b[0].id, b[0].name) for b in database.session.execute(database.select(Bank)).all()]
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.currency.choices = [("", "")] + obtener_lista_monedas()
    titulo = "Nueva Cuenta Bancaria - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        cuenta = BankAccount(
            bank_id=request.form.get("bank_id"),
            company=request.form.get("company"),
            account_name=request.form.get("account_name"),
            account_no=request.form.get("account_no"),
            iban=request.form.get("iban"),
            currency=request.form.get("currency") or None,
        )
        database.session.add(cuenta)
        database.session.commit()
        return redirect("/cash_management/bank-account/list")
    return render_template("bancos/banco_cuenta_nuevo.html", form=formulario, titulo=titulo)


@bancos.route("/bank-account/<account_id>")
@modulo_activo("cash")
@login_required
def bancos_cuenta_bancaria(account_id):
    """Detalle de cuenta bancaria."""
    from flask import abort

    registro = database.session.get(BankAccount, account_id)
    if not registro:
        abort(404)
    titulo = registro.account_name + " - " + APPNAME
    return render_template("bancos/banco_cuenta.html", registro=registro, titulo=titulo)


def _form_decimal(field_name: str, default: str = "0") -> Decimal:
    """Convierte un valor de formulario a Decimal."""

    value = request.form.get(field_name)
    return Decimal(str(value if value not in (None, "") else default))


def _invoice_outstanding(invoice) -> Decimal:
    """Devuelve el saldo vivo cacheado de una factura."""

    value = invoice.outstanding_amount if invoice.outstanding_amount is not None else invoice.grand_total
    return Decimal(str(value or 0))


def _payment_source_rows(purchase_invoice_ids: list[str], sales_invoice_ids: list[str]) -> list[dict]:
    """Construye las filas origen para el formulario de pago."""

    rows = []
    for invoice_id in purchase_invoice_ids:
        invoice = database.session.get(PurchaseInvoice, invoice_id)
        if invoice:
            rows.append(
                {
                    "reference_type": "purchase_invoice",
                    "label": "Factura de Compra",
                    "document": invoice,
                    "url": url_for("compras.compras_factura_compra", invoice_id=invoice.id),
                }
            )
    for invoice_id in sales_invoice_ids:
        invoice = database.session.get(SalesInvoice, invoice_id)
        if invoice:
            rows.append(
                {
                    "reference_type": "sales_invoice",
                    "label": "Factura de Venta",
                    "document": invoice,
                    "url": url_for("ventas.ventas_factura_venta", invoice_id=invoice.id),
                }
            )
    return rows


def _save_payment_references(payment: PaymentEntry) -> Decimal:
    """Guarda referencias de pago y actualiza saldos vivos de facturas."""

    total_allocated = Decimal("0")
    i = 0
    while request.form.get(f"reference_id_{i}"):
        reference_type = request.form.get(f"reference_type_{i}", "")
        reference_id = request.form.get(f"reference_id_{i}", "")
        allocated = _form_decimal(f"allocated_amount_{i}", "0")
        if allocated <= 0:
            i += 1
            continue
        if reference_type == "purchase_invoice":
            invoice = database.session.get(PurchaseInvoice, reference_id)
        elif reference_type == "sales_invoice":
            invoice = database.session.get(SalesInvoice, reference_id)
        else:
            abort(400)
        if not invoice:
            abort(404)
        invoice = cast(PurchaseInvoice | SalesInvoice, invoice)
        if payment.company and invoice.company and payment.company != invoice.company:
            abort(409)
        outstanding = _invoice_outstanding(invoice)
        if allocated > outstanding:
            abort(409)
        reference = PaymentReference(
            payment_id=payment.id,
            reference_type=reference_type,
            reference_id=reference_id,
            total_amount=invoice.grand_total,
            outstanding_amount=outstanding,
            allocated_amount=allocated,
            allocation_date=payment.posting_date,
        )
        database.session.add(reference)
        invoice.outstanding_amount = outstanding - allocated
        invoice.base_outstanding_amount = invoice.outstanding_amount
        total_allocated += allocated
        i += 1
    return total_allocated


@bancos.route("/payment/new", methods=["GET", "POST"])
@modulo_activo("cash")
@login_required
def bancos_pago_nuevo():
    """Formulario para crear un nuevo pago."""
    from cacao_accounting.bancos.forms import FormularioPago
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.database import ExternalCounter, Party

    formulario = FormularioPago()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    selected_company = request.values.get("company") or (
        formulario.company.choices[0][0] if formulario.company.choices else None
    )
    formulario.naming_series.choices = _series_choices("payment_entry", selected_company)
    formulario.bank_account_id.choices = [("", "")] + [
        (str(b[0].id), f"{b[0].account_name} {b[0].account_no or ''}".strip())
        for b in database.session.execute(database.select(BankAccount).filter_by(is_active=True)).all()
    ]
    formulario.party_id.choices = [("", "")] + [
        (str(p[0].id), p[0].name) for p in database.session.execute(database.select(Party)).all()
    ]
    # Contadores externos activos para la compania seleccionada
    counters_query = database.select(ExternalCounter).filter_by(is_active=True)
    if selected_company:
        counters_query = counters_query.filter_by(company=selected_company)
    active_counters = database.session.execute(counters_query).scalars().all()
    formulario.external_counter_id.choices = [("", "— Sin contador externo —")] + [
        (str(c.id), f"{c.name} (siguiente: {c.next_suggested_formatted})") for c in active_counters
    ]

    from_purchase_invoice_ids = request.values.getlist("from_purchase_invoice")
    from_sales_invoice_ids = request.values.getlist("from_sales_invoice")
    facturas_origen = _payment_source_rows(from_purchase_invoice_ids, from_sales_invoice_ids)
    if request.method == "GET" and facturas_origen:
        first = facturas_origen[0]["document"]
        formulario.company.data = first.company
        formulario.party_id.data = getattr(first, "supplier_id", None) or getattr(first, "customer_id", None)
        formulario.party_type.data = "supplier" if facturas_origen[0]["reference_type"] == "purchase_invoice" else "customer"
        formulario.payment_type.data = "pay" if facturas_origen[0]["reference_type"] == "purchase_invoice" else "receive"
        formulario.paid_amount.data = str(
            sum((_invoice_outstanding(row["document"]) for row in facturas_origen), Decimal("0"))
        )
    factura_compra_origen = (
        database.session.get(PurchaseInvoice, from_purchase_invoice_ids[0]) if from_purchase_invoice_ids else None
    )
    factura_venta_origen = database.session.get(SalesInvoice, from_sales_invoice_ids[0]) if from_sales_invoice_ids else None
    titulo = "Nuevo Pago - " + APPNAME
    if request.method == "POST":
        try:
            amount = _form_decimal("paid_amount", "0")
            payment_type = request.form.get("payment_type") or "receive"
            payment = PaymentEntry(
                payment_type=payment_type,
                company=request.form.get("company") or None,
                posting_date=request.form.get("posting_date") or None,
                bank_account_id=request.form.get("bank_account_id") or None,
                party_type=request.form.get("party_type") or None,
                party_id=request.form.get("party_id") or None,
                remarks=request.form.get("remarks"),
                docstatus=0,
            )
            if payment_type == "pay":
                payment.paid_amount = amount
                payment.base_paid_amount = amount
            elif payment_type == "receive":
                payment.received_amount = amount
                payment.base_received_amount = amount
            else:
                payment.paid_amount = amount
                payment.received_amount = amount
            database.session.add(payment)
            database.session.flush()
            # Contexto para seleccion contextual del contador externo
            ext_context = {
                "payment_type": payment_type,
                "bank_account_id": request.form.get("bank_account_id") or None,
            }
            assign_document_identifier(
                document=payment,
                entity_type="payment_entry",
                posting_date_raw=request.form.get("posting_date"),
                naming_series_id=request.form.get("naming_series") or None,
                external_counter_id=request.form.get("external_counter_id") or None,
                external_number=request.form.get("external_number") or None,
                external_context=ext_context,
            )
            allocated = _save_payment_references(payment)
            if amount == 0 and allocated:
                if payment_type == "pay":
                    payment.paid_amount = allocated
                    payment.base_paid_amount = allocated
                else:
                    payment.received_amount = allocated
                    payment.base_received_amount = allocated
            database.session.commit()
            flash("Pago creado correctamente.", "success")
            return redirect(url_for("bancos.bancos_pago", payment_id=payment.id))
        except IdentifierConfigurationError as exc:
            database.session.rollback()
            flash(str(exc), "danger")
    return render_template(
        "bancos/pago_nuevo.html",
        form=formulario,
        titulo=titulo,
        from_purchase_invoice_ids=from_purchase_invoice_ids,
        from_sales_invoice_ids=from_sales_invoice_ids,
        factura_compra_origen=factura_compra_origen,
        factura_venta_origen=factura_venta_origen,
        facturas_origen=facturas_origen,
    )


@bancos.route("/payment/<payment_id>")
@modulo_activo("cash")
@login_required
def bancos_pago(payment_id):
    """Detalle de pago."""
    from flask import abort

    registro = database.session.get(PaymentEntry, payment_id)
    if not registro:
        abort(404)
    titulo = (registro.document_no or payment_id) + " - " + APPNAME
    return render_template("bancos/pago.html", registro=registro, titulo=titulo)


@bancos.route("/payment/<payment_id>/submit", methods=["POST"])
@modulo_activo("cash")
@login_required
def bancos_pago_submit(payment_id: str):
    """Aprueba y contabiliza un pago."""

    registro = database.session.get(PaymentEntry, payment_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    try:
        submit_document(registro)
        database.session.commit()
    except PostingError as exc:
        database.session.rollback()
        flash(_(str(exc)), "danger")
        return redirect(url_for("bancos.bancos_pago", payment_id=payment_id))
    flash(_("Pago aprobado y contabilizado."), "success")
    return redirect(url_for("bancos.bancos_pago", payment_id=payment_id))


@bancos.route("/payment/<payment_id>/cancel", methods=["POST"])
@modulo_activo("cash")
@login_required
def bancos_pago_cancel(payment_id: str):
    """Cancela un pago con reverso contable."""

    registro = database.session.get(PaymentEntry, payment_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    try:
        cancel_document(registro)
        database.session.commit()
    except PostingError as exc:
        database.session.rollback()
        flash(_(str(exc)), "danger")
        return redirect(url_for("bancos.bancos_pago", payment_id=payment_id))
    flash(_("Pago cancelado con reverso contable."), "warning")
    return redirect(url_for("bancos.bancos_pago", payment_id=payment_id))
