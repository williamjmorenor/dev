# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Caja y Bancos."""

# ---------------------------------------------------------------------------------------
# Libreria estandar
# --------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
# Librerias de terceros
# ---------------------------------------------------------------------------------------
from flask import Blueprint, render_template, request
from flask_login import login_required

# ---------------------------------------------------------------------------------------
# Recursos locales
# ---------------------------------------------------------------------------------------
from cacao_accounting.database import Bank, BankAccount, BankTransaction, PaymentEntry, database
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
