# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Ventas."""

from flask import Blueprint, render_template, request
from flask_login import login_required

from cacao_accounting.database import DeliveryNote, Party, SalesInvoice, SalesOrder, database
from cacao_accounting.decorators import modulo_activo
from cacao_accounting.version import APPNAME

ventas = Blueprint("ventas", __name__, template_folder="templates")


@ventas.route("/")
@ventas.route("/ventas")
@ventas.route("/sales")
@modulo_activo("sales")
@login_required
def ventas_():
    """Modulo de ventas."""
    return render_template("ventas.html")


@ventas.route("/sales-order/list")
@modulo_activo("sales")
@login_required
def ventas_orden_venta_lista():
    """Listado de ordenes de venta."""
    consulta = database.paginate(
        database.select(SalesOrder),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Ordenes de Venta - " + APPNAME
    return render_template("ventas/orden_venta_lista.html", consulta=consulta, titulo=titulo)


@ventas.route("/delivery-note/list")
@modulo_activo("sales")
@login_required
def ventas_entrega_lista():
    """Listado de notas de entrega."""
    consulta = database.paginate(
        database.select(DeliveryNote),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Notas de Entrega - " + APPNAME
    return render_template("ventas/entrega_lista.html", consulta=consulta, titulo=titulo)


@ventas.route("/sales-invoice/list")
@modulo_activo("sales")
@login_required
def ventas_factura_venta_lista():
    """Listado de facturas de venta."""
    consulta = database.paginate(
        database.select(SalesInvoice),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Facturas de Venta - " + APPNAME
    return render_template("ventas/factura_venta_lista.html", consulta=consulta, titulo=titulo)


@ventas.route("/customer/list")
@modulo_activo("sales")
@login_required
def ventas_cliente_lista():
    """Listado de clientes."""
    consulta = database.paginate(
        database.select(Party).filter(Party.party_type == "customer"),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Clientes - " + APPNAME
    return render_template("ventas/cliente_lista.html", consulta=consulta, titulo=titulo)
