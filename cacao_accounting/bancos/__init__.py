# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Caja y Bancos."""

# ---------------------------------------------------------------------------------------
# Libreria estandar
# --------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
# Librerias de terceros
# ---------------------------------------------------------------------------------------
from flask import Blueprint, redirect, render_template, request
from flask_login import login_required

# ---------------------------------------------------------------------------------------
# Recursos locales
# ---------------------------------------------------------------------------------------
from cacao_accounting.database import Bank, BankAccount, BankTransaction, PaymentEntry, PurchaseInvoice, SalesInvoice, database
from cacao_accounting.decorators import modulo_activo
from cacao_accounting.version import APPNAME

bancos = Blueprint("bancos", __name__, template_folder="templates")


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

    formulario = FormularioCuentaBancaria()
    formulario.bank_id.choices = [
        (b[0].id, b[0].name)
        for b in database.session.execute(database.select(Bank)).all()
    ]
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


@bancos.route("/payment/new", methods=["GET", "POST"])
@modulo_activo("cash")
@login_required
def bancos_pago_nuevo():
    """Formulario para crear un nuevo pago."""
    from cacao_accounting.bancos.forms import FormularioPago
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.database import Party

    formulario = FormularioPago()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.party_id.choices = [("", "")] + [
        (str(p[0].id), p[0].name)
        for p in database.session.execute(database.select(Party)).all()
    ]
    from_purchase_invoice_id = request.args.get("from_purchase_invoice")
    from_sales_invoice_id = request.args.get("from_sales_invoice")
    factura_compra_origen = (
        database.session.get(PurchaseInvoice, from_purchase_invoice_id) if from_purchase_invoice_id else None
    )
    factura_venta_origen = (
        database.session.get(SalesInvoice, from_sales_invoice_id) if from_sales_invoice_id else None
    )
    titulo = "Nuevo Pago - " + APPNAME
    return render_template(
        "bancos/pago_nuevo.html",
        form=formulario,
        titulo=titulo,
        from_purchase_invoice_id=from_purchase_invoice_id,
        from_sales_invoice_id=from_sales_invoice_id,
        factura_compra_origen=factura_compra_origen,
        factura_venta_origen=factura_venta_origen,
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
