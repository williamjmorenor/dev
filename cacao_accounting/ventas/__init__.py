# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Ventas."""

from flask import Blueprint, redirect, render_template, request
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


@ventas.route("/customer/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_cliente_nuevo():
    """Formulario para crear un nuevo cliente."""
    from cacao_accounting.ventas.forms import FormularioCliente

    formulario = FormularioCliente()
    titulo = "Nuevo Cliente - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        cliente = Party(
            party_type="customer",
            name=request.form.get("name"),
            comercial_name=request.form.get("comercial_name"),
            tax_id=request.form.get("tax_id"),
            classification=request.form.get("classification"),
        )
        database.session.add(cliente)
        database.session.commit()
        return redirect("/sales/customer/list")
    return render_template("ventas/cliente_nuevo.html", form=formulario, titulo=titulo)


@ventas.route("/customer/<customer_id>")
@modulo_activo("sales")
@login_required
def ventas_cliente(customer_id):
    """Detalle de cliente."""
    from flask import abort

    registro = database.session.execute(
        database.select(Party).filter_by(id=customer_id, party_type="customer")
    ).first()
    if not registro:
        abort(404)
    titulo = registro[0].name + " - " + APPNAME
    return render_template("ventas/cliente.html", registro=registro[0], titulo=titulo)


@ventas.route("/sales-order/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_orden_venta_nuevo():
    """Formulario para crear una orden de venta."""
    from cacao_accounting.ventas.forms import FormularioOrdenVenta

    formulario = FormularioOrdenVenta()
    titulo = "Nueva Orden de Venta - " + APPNAME
    return render_template("ventas/orden_venta_nuevo.html", form=formulario, titulo=titulo)


@ventas.route("/sales-order/<order_id>")
@modulo_activo("sales")
@login_required
def ventas_orden_venta(order_id):
    """Detalle de orden de venta."""
    from flask import abort

    registro = database.session.get(SalesOrder, order_id)
    if not registro:
        abort(404)
    titulo = (registro.document_no or order_id) + " - " + APPNAME
    return render_template("ventas/orden_venta.html", registro=registro, titulo=titulo)


@ventas.route("/delivery-note/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_entrega_nuevo():
    """Formulario para crear una nota de entrega."""
    from cacao_accounting.ventas.forms import FormularioEntregaVenta

    formulario = FormularioEntregaVenta()
    titulo = "Nueva Nota de Entrega - " + APPNAME
    return render_template("ventas/entrega_nuevo.html", form=formulario, titulo=titulo)


@ventas.route("/delivery-note/<note_id>")
@modulo_activo("sales")
@login_required
def ventas_entrega(note_id):
    """Detalle de nota de entrega."""
    from flask import abort

    registro = database.session.get(DeliveryNote, note_id)
    if not registro:
        abort(404)
    titulo = (registro.document_no or note_id) + " - " + APPNAME
    return render_template("ventas/entrega.html", registro=registro, titulo=titulo)


@ventas.route("/sales-invoice/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_factura_venta_nuevo():
    """Formulario para crear una factura de venta."""
    from cacao_accounting.ventas.forms import FormularioFacturaVenta

    formulario = FormularioFacturaVenta()
    titulo = "Nueva Factura de Venta - " + APPNAME
    return render_template("ventas/factura_venta_nuevo.html", form=formulario, titulo=titulo)


@ventas.route("/sales-invoice/<invoice_id>")
@modulo_activo("sales")
@login_required
def ventas_factura_venta(invoice_id):
    """Detalle de factura de venta."""
    from flask import abort

    registro = database.session.get(SalesInvoice, invoice_id)
    if not registro:
        abort(404)
    titulo = (registro.document_no or invoice_id) + " - " + APPNAME
    return render_template("ventas/factura_venta.html", registro=registro, titulo=titulo)
