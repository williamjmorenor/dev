# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Compras."""

# ---------------------------------------------------------------------------------------
# Libreria estandar
# --------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
# Librerias de terceros
# ---------------------------------------------------------------------------------------
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

# ---------------------------------------------------------------------------------------
# Recursos locales
# ---------------------------------------------------------------------------------------
from cacao_accounting.database import (
    Item,
    Party,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    UOM,
    database,
)
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


def _save_purchase_order_items(order_id: str) -> None:
    """Guarda las líneas de una orden de compra desde el formulario."""
    i = 0
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            linea = PurchaseOrderItem(
                purchase_order_id=order_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=request.form.get(f"qty_{i}", 1),
                uom=request.form.get(f"uom_{i}") or None,
                rate=request.form.get(f"rate_{i}") or None,
                amount=request.form.get(f"amount_{i}") or None,
            )
            database.session.add(linea)
        i += 1


def _save_purchase_receipt_items(receipt_id: str) -> None:
    """Guarda las líneas de una recepción de compra desde el formulario."""
    i = 0
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            linea = PurchaseReceiptItem(
                purchase_receipt_id=receipt_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=request.form.get(f"qty_{i}", 1),
                uom=request.form.get(f"uom_{i}") or None,
                rate=request.form.get(f"rate_{i}") or None,
                amount=request.form.get(f"amount_{i}") or None,
                warehouse=request.form.get(f"warehouse_{i}") or None,
            )
            database.session.add(linea)
        i += 1


def _save_purchase_invoice_items(invoice_id: str) -> None:
    """Guarda las líneas de una factura de compra desde el formulario."""
    i = 0
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            linea = PurchaseInvoiceItem(
                purchase_invoice_id=invoice_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=request.form.get(f"qty_{i}", 1),
                uom=request.form.get(f"uom_{i}") or None,
                rate=request.form.get(f"rate_{i}") or None,
                amount=request.form.get(f"amount_{i}") or None,
            )
            database.session.add(linea)
        i += 1


@compras.route("/purchase-order/new", methods=["GET", "POST"])
@modulo_activo("purchases")
@login_required
def compras_orden_compra_nuevo():
    """Formulario para crear una orden de compra."""
    from cacao_accounting.compras.forms import FormularioOrdenCompra
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial

    formulario = FormularioOrdenCompra()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.supplier_id.choices = [("", "")] + [
        (str(p[0].id), p[0].name)
        for p in database.session.execute(database.select(Party).filter_by(party_type="supplier")).all()
    ]
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item)).all()
    ]
    uoms_disponibles = [
        {"code": u[0].code, "name": u[0].name}
        for u in database.session.execute(database.select(UOM)).all()
    ]
    titulo = "Nueva Orden de Compra - " + APPNAME
    if request.method == "POST":
        orden = PurchaseOrder(
            supplier_id=request.form.get("supplier_id") or None,
            company=request.form.get("company") or None,
            posting_date=request.form.get("posting_date") or None,
            remarks=request.form.get("remarks"),
            docstatus=0,
        )
        database.session.add(orden)
        database.session.flush()
        _save_purchase_order_items(orden.id)
        database.session.commit()
        flash("Orden de compra creada correctamente.", "success")
        return redirect(url_for("compras.compras_orden_compra", order_id=orden.id))
    return render_template(
        "compras/orden_compra_nuevo.html",
        form=formulario,
        titulo=titulo,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
    )


@compras.route("/purchase-order/<order_id>")
@modulo_activo("purchases")
@login_required
def compras_orden_compra(order_id):
    """Detalle de orden de compra."""
    registro = database.session.get(PurchaseOrder, order_id)
    if not registro:
        abort(404)
    items = database.session.execute(
        database.select(PurchaseOrderItem).filter_by(purchase_order_id=order_id)
    ).all()
    titulo = (registro.document_no or order_id) + " - " + APPNAME
    return render_template("compras/orden_compra.html", registro=registro, items=items, titulo=titulo)


@compras.route("/purchase-order/<order_id>/submit", methods=["POST"])
@modulo_activo("purchases")
@login_required
def compras_orden_compra_submit(order_id: str):
    """Aprueba una orden de compra."""
    registro = database.session.get(PurchaseOrder, order_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    registro.docstatus = 1
    database.session.commit()
    flash("Orden de compra aprobada.", "success")
    return redirect(url_for("compras.compras_orden_compra", order_id=order_id))


@compras.route("/purchase-order/<order_id>/cancel", methods=["POST"])
@modulo_activo("purchases")
@login_required
def compras_orden_compra_cancel(order_id: str):
    """Cancela una orden de compra."""
    registro = database.session.get(PurchaseOrder, order_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    registro.docstatus = 2
    database.session.commit()
    flash("Orden de compra cancelada.", "warning")
    return redirect(url_for("compras.compras_orden_compra", order_id=order_id))


@compras.route("/purchase-receipt/new", methods=["GET", "POST"])
@modulo_activo("purchases")
@login_required
def compras_recepcion_nuevo():
    """Formulario para crear una recepción de compra."""
    from cacao_accounting.compras.forms import FormularioRecepcionCompra
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.database import Warehouse

    formulario = FormularioRecepcionCompra()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.supplier_id.choices = [("", "")] + [
        (str(p[0].id), p[0].name)
        for p in database.session.execute(database.select(Party).filter_by(party_type="supplier")).all()
    ]
    from_order_id = request.args.get("from_order") or request.form.get("from_order")
    orden_origen = database.session.get(PurchaseOrder, from_order_id) if from_order_id else None
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item)).all()
    ]
    uoms_disponibles = [
        {"code": u[0].code, "name": u[0].name}
        for u in database.session.execute(database.select(UOM)).all()
    ]
    bodegas_disponibles = [
        {"code": w[0].code, "name": w[0].name}
        for w in database.session.execute(database.select(Warehouse)).all()
    ]
    titulo = "Nueva Recepción de Compra - " + APPNAME
    if request.method == "POST":
        recepcion = PurchaseReceipt(
            supplier_id=request.form.get("supplier_id") or None,
            company=request.form.get("company") or None,
            posting_date=request.form.get("posting_date") or None,
            purchase_order_id=request.form.get("from_order") or None,
            remarks=request.form.get("remarks"),
            docstatus=0,
        )
        database.session.add(recepcion)
        database.session.flush()
        _save_purchase_receipt_items(recepcion.id)
        database.session.commit()
        flash("Recepción de compra creada correctamente.", "success")
        return redirect(url_for("compras.compras_recepcion", receipt_id=recepcion.id))
    return render_template(
        "compras/recepcion_nuevo.html",
        form=formulario,
        titulo=titulo,
        orden_origen=orden_origen,
        from_order_id=from_order_id,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
        bodegas_disponibles=bodegas_disponibles,
    )


@compras.route("/purchase-receipt/<receipt_id>")
@modulo_activo("purchases")
@login_required
def compras_recepcion(receipt_id):
    """Detalle de recepción de compra."""
    registro = database.session.get(PurchaseReceipt, receipt_id)
    if not registro:
        abort(404)
    items = database.session.execute(
        database.select(PurchaseReceiptItem).filter_by(purchase_receipt_id=receipt_id)
    ).all()
    titulo = (registro.document_no or receipt_id) + " - " + APPNAME
    return render_template("compras/recepcion.html", registro=registro, items=items, titulo=titulo)


@compras.route("/purchase-receipt/<receipt_id>/submit", methods=["POST"])
@modulo_activo("purchases")
@login_required
def compras_recepcion_submit(receipt_id: str):
    """Aprueba una recepción de compra."""
    registro = database.session.get(PurchaseReceipt, receipt_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    registro.docstatus = 1
    database.session.commit()
    flash("Recepción de compra aprobada.", "success")
    return redirect(url_for("compras.compras_recepcion", receipt_id=receipt_id))


@compras.route("/purchase-receipt/<receipt_id>/cancel", methods=["POST"])
@modulo_activo("purchases")
@login_required
def compras_recepcion_cancel(receipt_id: str):
    """Cancela una recepción de compra."""
    registro = database.session.get(PurchaseReceipt, receipt_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    registro.docstatus = 2
    database.session.commit()
    flash("Recepción de compra cancelada.", "warning")
    return redirect(url_for("compras.compras_recepcion", receipt_id=receipt_id))


@compras.route("/purchase-invoice/new", methods=["GET", "POST"])
@modulo_activo("purchases")
@login_required
def compras_factura_compra_nuevo():
    """Formulario para crear una factura de compra."""
    from cacao_accounting.compras.forms import FormularioFacturaCompra
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial

    formulario = FormularioFacturaCompra()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.supplier_id.choices = [("", "")] + [
        (str(p[0].id), p[0].name)
        for p in database.session.execute(database.select(Party).filter_by(party_type="supplier")).all()
    ]
    from_order_id = request.args.get("from_order") or request.form.get("from_order")
    from_receipt_id = request.args.get("from_receipt") or request.form.get("from_receipt")
    from_return_id = request.args.get("from_return") or request.form.get("from_return")
    orden_origen = database.session.get(PurchaseOrder, from_order_id) if from_order_id else None
    recepcion_origen = database.session.get(PurchaseReceipt, from_receipt_id) if from_receipt_id else None
    factura_origen = database.session.get(PurchaseInvoice, from_return_id) if from_return_id else None
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item)).all()
    ]
    uoms_disponibles = [
        {"code": u[0].code, "name": u[0].name}
        for u in database.session.execute(database.select(UOM)).all()
    ]
    titulo = "Nueva Factura de Compra - " + APPNAME
    if request.method == "POST":
        factura = PurchaseInvoice(
            supplier_id=request.form.get("supplier_id") or None,
            company=request.form.get("company") or None,
            posting_date=request.form.get("posting_date") or None,
            supplier_invoice_no=request.form.get("supplier_invoice_no"),
            purchase_order_id=request.form.get("from_order") or None,
            purchase_receipt_id=request.form.get("from_receipt") or None,
            is_return=bool(request.form.get("is_return")),
            reversal_of=request.form.get("from_return") or None,
            remarks=request.form.get("remarks"),
            docstatus=0,
        )
        database.session.add(factura)
        database.session.flush()
        _save_purchase_invoice_items(factura.id)
        database.session.commit()
        flash("Factura de compra creada correctamente.", "success")
        return redirect(url_for("compras.compras_factura_compra", invoice_id=factura.id))
    return render_template(
        "compras/factura_compra_nuevo.html",
        form=formulario,
        titulo=titulo,
        orden_origen=orden_origen,
        recepcion_origen=recepcion_origen,
        factura_origen=factura_origen,
        from_order_id=from_order_id,
        from_receipt_id=from_receipt_id,
        from_return_id=from_return_id,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
    )


@compras.route("/purchase-invoice/<invoice_id>")
@modulo_activo("purchases")
@login_required
def compras_factura_compra(invoice_id):
    """Detalle de factura de compra."""
    registro = database.session.get(PurchaseInvoice, invoice_id)
    if not registro:
        abort(404)
    items = database.session.execute(
        database.select(PurchaseInvoiceItem).filter_by(purchase_invoice_id=invoice_id)
    ).all()
    titulo = (registro.document_no or invoice_id) + " - " + APPNAME
    return render_template("compras/factura_compra.html", registro=registro, items=items, titulo=titulo)


@compras.route("/purchase-invoice/<invoice_id>/submit", methods=["POST"])
@modulo_activo("purchases")
@login_required
def compras_factura_compra_submit(invoice_id: str):
    """Aprueba una factura de compra."""
    registro = database.session.get(PurchaseInvoice, invoice_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    registro.docstatus = 1
    database.session.commit()
    flash("Factura de compra aprobada.", "success")
    return redirect(url_for("compras.compras_factura_compra", invoice_id=invoice_id))


@compras.route("/purchase-invoice/<invoice_id>/cancel", methods=["POST"])
@modulo_activo("purchases")
@login_required
def compras_factura_compra_cancel(invoice_id: str):
    """Cancela una factura de compra."""
    registro = database.session.get(PurchaseInvoice, invoice_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    registro.docstatus = 2
    database.session.commit()
    flash("Factura de compra cancelada.", "warning")
    return redirect(url_for("compras.compras_factura_compra", invoice_id=invoice_id))
