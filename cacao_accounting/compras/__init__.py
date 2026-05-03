# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Compras."""

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
from cacao_accounting.database import Party, PurchaseInvoice, PurchaseOrder, PurchaseReceipt, database
from cacao_accounting.decorators import modulo_activo
from cacao_accounting.version import APPNAME

# < --------------------------------------------------------------------------------------------- >
compras = Blueprint("compras", __name__, template_folder="templates")


@compras.route("/")
@compras.route("/compras")
@compras.route("/buying")
@modulo_activo("purchases")
@login_required
def compras_():
    """Pantalla principal del modulo de compras."""
    return render_template("compras.html")


@compras.route("/purchase-order/list")
@modulo_activo("purchases")
@login_required
def compras_orden_compra_lista():
    """Listado de ordenes de compra."""
    consulta = database.paginate(
        database.select(PurchaseOrder),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Ordenes de Compra - " + APPNAME
    return render_template("compras/orden_compra_lista.html", consulta=consulta, titulo=titulo)


@compras.route("/purchase-receipt/list")
@modulo_activo("purchases")
@login_required
def compras_recepcion_lista():
    """Listado de recepciones de compra."""
    consulta = database.paginate(
        database.select(PurchaseReceipt),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Recepciones de Compra - " + APPNAME
    return render_template("compras/recepcion_lista.html", consulta=consulta, titulo=titulo)


@compras.route("/purchase-invoice/list")
@modulo_activo("purchases")
@login_required
def compras_factura_compra_lista():
    """Listado de facturas de compra."""
    consulta = database.paginate(
        database.select(PurchaseInvoice),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Facturas de Compra - " + APPNAME
    return render_template("compras/factura_compra_lista.html", consulta=consulta, titulo=titulo)


@compras.route("/supplier/list")
@modulo_activo("purchases")
@login_required
def compras_proveedor_lista():
    """Listado de proveedores."""
    consulta = database.paginate(
        database.select(Party).filter(Party.party_type == "supplier"),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Proveedores - " + APPNAME
    return render_template("compras/proveedor_lista.html", consulta=consulta, titulo=titulo)


@compras.route("/supplier/new", methods=["GET", "POST"])
@modulo_activo("purchases")
@login_required
def compras_proveedor_nuevo():
    """Formulario para crear un nuevo proveedor."""
    from cacao_accounting.compras.forms import FormularioProveedor

    formulario = FormularioProveedor()
    titulo = "Nuevo Proveedor - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        proveedor = Party(
            party_type="supplier",
            name=request.form.get("name"),
            comercial_name=request.form.get("comercial_name"),
            tax_id=request.form.get("tax_id"),
            classification=request.form.get("classification"),
        )
        database.session.add(proveedor)
        database.session.commit()
        return redirect("/buying/supplier/list")
    return render_template("compras/proveedor_nuevo.html", form=formulario, titulo=titulo)


@compras.route("/supplier/<supplier_id>")
@modulo_activo("purchases")
@login_required
def compras_proveedor(supplier_id):
    """Detalle de proveedor."""
    from flask import abort

    registro = database.session.execute(
        database.select(Party).filter_by(id=supplier_id, party_type="supplier")
    ).first()
    if not registro:
        abort(404)
    titulo = registro[0].name + " - " + APPNAME
    return render_template("compras/proveedor.html", registro=registro[0], titulo=titulo)


@compras.route("/purchase-order/new", methods=["GET", "POST"])
@modulo_activo("purchases")
@login_required
def compras_orden_compra_nuevo():
    """Formulario para crear una orden de compra."""
    from cacao_accounting.compras.forms import FormularioOrdenCompra

    formulario = FormularioOrdenCompra()
    titulo = "Nueva Orden de Compra - " + APPNAME
    return render_template("compras/orden_compra_nuevo.html", form=formulario, titulo=titulo)


@compras.route("/purchase-order/<order_id>")
@modulo_activo("purchases")
@login_required
def compras_orden_compra(order_id):
    """Detalle de orden de compra."""
    from flask import abort

    registro = database.session.get(PurchaseOrder, order_id)
    if not registro:
        abort(404)
    titulo = (registro.document_no or order_id) + " - " + APPNAME
    return render_template("compras/orden_compra.html", registro=registro, titulo=titulo)


@compras.route("/purchase-receipt/new", methods=["GET", "POST"])
@modulo_activo("purchases")
@login_required
def compras_recepcion_nuevo():
    """Formulario para crear una recepción de compra."""
    from cacao_accounting.compras.forms import FormularioRecepcionCompra

    formulario = FormularioRecepcionCompra()
    titulo = "Nueva Recepción de Compra - " + APPNAME
    return render_template("compras/recepcion_nuevo.html", form=formulario, titulo=titulo)


@compras.route("/purchase-receipt/<receipt_id>")
@modulo_activo("purchases")
@login_required
def compras_recepcion(receipt_id):
    """Detalle de recepción de compra."""
    from flask import abort

    registro = database.session.get(PurchaseReceipt, receipt_id)
    if not registro:
        abort(404)
    titulo = (registro.document_no or receipt_id) + " - " + APPNAME
    return render_template("compras/recepcion.html", registro=registro, titulo=titulo)


@compras.route("/purchase-invoice/new", methods=["GET", "POST"])
@modulo_activo("purchases")
@login_required
def compras_factura_compra_nuevo():
    """Formulario para crear una factura de compra."""
    from cacao_accounting.compras.forms import FormularioFacturaCompra

    formulario = FormularioFacturaCompra()
    titulo = "Nueva Factura de Compra - " + APPNAME
    return render_template("compras/factura_compra_nuevo.html", form=formulario, titulo=titulo)


@compras.route("/purchase-invoice/<invoice_id>")
@modulo_activo("purchases")
@login_required
def compras_factura_compra(invoice_id):
    """Detalle de factura de compra."""
    from flask import abort

    registro = database.session.get(PurchaseInvoice, invoice_id)
    if not registro:
        abort(404)
    titulo = (registro.document_no or invoice_id) + " - " + APPNAME
    return render_template("compras/factura_compra.html", registro=registro, titulo=titulo)
