# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Ventas."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from cacao_accounting.database import (
    DeliveryNote,
    DeliveryNoteItem,
    Item,
    Party,
    SalesInvoice,
    SalesInvoiceItem,
    SalesOrder,
    SalesOrderItem,
    UOM,
    database,
)
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
    registro = database.session.execute(
        database.select(Party).filter_by(id=customer_id, party_type="customer")
    ).first()
    if not registro:
        abort(404)
    titulo = registro[0].name + " - " + APPNAME
    return render_template("ventas/cliente.html", registro=registro[0], titulo=titulo)


def _save_sales_order_items(order_id: str) -> None:
    """Guarda las líneas de una orden de venta desde el formulario."""
    i = 0
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            linea = SalesOrderItem(
                sales_order_id=order_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=request.form.get(f"qty_{i}", 1),
                uom=request.form.get(f"uom_{i}") or None,
                rate=request.form.get(f"rate_{i}") or None,
                amount=request.form.get(f"amount_{i}") or None,
            )
            database.session.add(linea)
        i += 1


def _save_delivery_note_items(note_id: str) -> None:
    """Guarda las líneas de una nota de entrega desde el formulario."""
    i = 0
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            linea = DeliveryNoteItem(
                delivery_note_id=note_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=request.form.get(f"qty_{i}", 1),
                uom=request.form.get(f"uom_{i}") or None,
                rate=request.form.get(f"rate_{i}") or None,
                amount=request.form.get(f"amount_{i}") or None,
            )
            database.session.add(linea)
        i += 1


def _save_sales_invoice_items(invoice_id: str) -> None:
    """Guarda las líneas de una factura de venta desde el formulario."""
    i = 0
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            linea = SalesInvoiceItem(
                sales_invoice_id=invoice_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=request.form.get(f"qty_{i}", 1),
                uom=request.form.get(f"uom_{i}") or None,
                rate=request.form.get(f"rate_{i}") or None,
                amount=request.form.get(f"amount_{i}") or None,
            )
            database.session.add(linea)
        i += 1


@ventas.route("/sales-order/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_orden_venta_nuevo():
    """Formulario para crear una orden de venta."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.ventas.forms import FormularioOrdenVenta

    formulario = FormularioOrdenVenta()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.customer_id.choices = [("", "")] + [
        (str(p[0].id), p[0].name)
        for p in database.session.execute(database.select(Party).filter_by(party_type="customer")).all()
    ]
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item)).all()
    ]
    uoms_disponibles = [
        {"code": u[0].code, "name": u[0].name}
        for u in database.session.execute(database.select(UOM)).all()
    ]
    titulo = "Nueva Orden de Venta - " + APPNAME
    if request.method == "POST":
        orden = SalesOrder(
            customer_id=request.form.get("customer_id") or None,
            company=request.form.get("company") or None,
            posting_date=request.form.get("posting_date") or None,
            remarks=request.form.get("remarks"),
            docstatus=0,
        )
        database.session.add(orden)
        database.session.flush()
        _save_sales_order_items(orden.id)
        database.session.commit()
        flash("Orden de venta creada correctamente.", "success")
        return redirect(url_for("ventas.ventas_orden_venta", order_id=orden.id))
    return render_template(
        "ventas/orden_venta_nuevo.html",
        form=formulario,
        titulo=titulo,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
    )


@ventas.route("/sales-order/<order_id>")
@modulo_activo("sales")
@login_required
def ventas_orden_venta(order_id):
    """Detalle de orden de venta."""
    registro = database.session.get(SalesOrder, order_id)
    if not registro:
        abort(404)
    items = database.session.execute(
        database.select(SalesOrderItem).filter_by(sales_order_id=order_id)
    ).all()
    titulo = (registro.document_no or order_id) + " - " + APPNAME
    return render_template("ventas/orden_venta.html", registro=registro, items=items, titulo=titulo)


@ventas.route("/sales-order/<order_id>/submit", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_orden_venta_submit(order_id: str):
    """Aprueba una orden de venta."""
    registro = database.session.get(SalesOrder, order_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    registro.docstatus = 1
    database.session.commit()
    flash("Orden de venta aprobada.", "success")
    return redirect(url_for("ventas.ventas_orden_venta", order_id=order_id))


@ventas.route("/sales-order/<order_id>/cancel", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_orden_venta_cancel(order_id: str):
    """Cancela una orden de venta."""
    registro = database.session.get(SalesOrder, order_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    registro.docstatus = 2
    database.session.commit()
    flash("Orden de venta cancelada.", "warning")
    return redirect(url_for("ventas.ventas_orden_venta", order_id=order_id))


@ventas.route("/delivery-note/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_entrega_nuevo():
    """Formulario para crear una nota de entrega."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.database import Warehouse
    from cacao_accounting.ventas.forms import FormularioEntregaVenta

    formulario = FormularioEntregaVenta()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.customer_id.choices = [("", "")] + [
        (str(p[0].id), p[0].name)
        for p in database.session.execute(database.select(Party).filter_by(party_type="customer")).all()
    ]
    from_order_id = request.args.get("from_order") or request.form.get("from_order")
    orden_origen = database.session.get(SalesOrder, from_order_id) if from_order_id else None
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
    titulo = "Nueva Nota de Entrega - " + APPNAME
    if request.method == "POST":
        entrega = DeliveryNote(
            customer_id=request.form.get("customer_id") or None,
            company=request.form.get("company") or None,
            posting_date=request.form.get("posting_date") or None,
            sales_order_id=request.form.get("from_order") or None,
            remarks=request.form.get("remarks"),
            docstatus=0,
        )
        database.session.add(entrega)
        database.session.flush()
        _save_delivery_note_items(entrega.id)
        database.session.commit()
        flash("Nota de entrega creada correctamente.", "success")
        return redirect(url_for("ventas.ventas_entrega", note_id=entrega.id))
    return render_template(
        "ventas/entrega_nuevo.html",
        form=formulario,
        titulo=titulo,
        orden_origen=orden_origen,
        from_order_id=from_order_id,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
        bodegas_disponibles=bodegas_disponibles,
    )


@ventas.route("/delivery-note/<note_id>")
@modulo_activo("sales")
@login_required
def ventas_entrega(note_id):
    """Detalle de nota de entrega."""
    registro = database.session.get(DeliveryNote, note_id)
    if not registro:
        abort(404)
    items = database.session.execute(
        database.select(DeliveryNoteItem).filter_by(delivery_note_id=note_id)
    ).all()
    titulo = (registro.document_no or note_id) + " - " + APPNAME
    return render_template("ventas/entrega.html", registro=registro, items=items, titulo=titulo)


@ventas.route("/delivery-note/<note_id>/submit", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_entrega_submit(note_id: str):
    """Aprueba una nota de entrega."""
    registro = database.session.get(DeliveryNote, note_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    registro.docstatus = 1
    database.session.commit()
    flash("Nota de entrega aprobada.", "success")
    return redirect(url_for("ventas.ventas_entrega", note_id=note_id))


@ventas.route("/delivery-note/<note_id>/cancel", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_entrega_cancel(note_id: str):
    """Cancela una nota de entrega."""
    registro = database.session.get(DeliveryNote, note_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    registro.docstatus = 2
    database.session.commit()
    flash("Nota de entrega cancelada.", "warning")
    return redirect(url_for("ventas.ventas_entrega", note_id=note_id))


@ventas.route("/sales-invoice/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_factura_venta_nuevo():
    """Formulario para crear una factura de venta."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.ventas.forms import FormularioFacturaVenta

    formulario = FormularioFacturaVenta()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.customer_id.choices = [("", "")] + [
        (str(p[0].id), p[0].name)
        for p in database.session.execute(database.select(Party).filter_by(party_type="customer")).all()
    ]
    from_order_id = request.args.get("from_order") or request.form.get("from_order")
    from_note_id = request.args.get("from_note") or request.form.get("from_note")
    orden_origen = database.session.get(SalesOrder, from_order_id) if from_order_id else None
    entrega_origen = database.session.get(DeliveryNote, from_note_id) if from_note_id else None
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item)).all()
    ]
    uoms_disponibles = [
        {"code": u[0].code, "name": u[0].name}
        for u in database.session.execute(database.select(UOM)).all()
    ]
    titulo = "Nueva Factura de Venta - " + APPNAME
    if request.method == "POST":
        factura = SalesInvoice(
            customer_id=request.form.get("customer_id") or None,
            company=request.form.get("company") or None,
            posting_date=request.form.get("posting_date") or None,
            sales_order_id=request.form.get("from_order") or None,
            delivery_note_id=request.form.get("from_note") or None,
            remarks=request.form.get("remarks"),
            docstatus=0,
        )
        database.session.add(factura)
        database.session.flush()
        _save_sales_invoice_items(factura.id)
        database.session.commit()
        flash("Factura de venta creada correctamente.", "success")
        return redirect(url_for("ventas.ventas_factura_venta", invoice_id=factura.id))
    return render_template(
        "ventas/factura_venta_nuevo.html",
        form=formulario,
        titulo=titulo,
        orden_origen=orden_origen,
        entrega_origen=entrega_origen,
        from_order_id=from_order_id,
        from_note_id=from_note_id,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
    )


@ventas.route("/sales-invoice/<invoice_id>")
@modulo_activo("sales")
@login_required
def ventas_factura_venta(invoice_id):
    """Detalle de factura de venta."""
    registro = database.session.get(SalesInvoice, invoice_id)
    if not registro:
        abort(404)
    items = database.session.execute(
        database.select(SalesInvoiceItem).filter_by(sales_invoice_id=invoice_id)
    ).all()
    titulo = (registro.document_no or invoice_id) + " - " + APPNAME
    return render_template("ventas/factura_venta.html", registro=registro, items=items, titulo=titulo)


@ventas.route("/sales-invoice/<invoice_id>/submit", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_factura_venta_submit(invoice_id: str):
    """Aprueba una factura de venta."""
    registro = database.session.get(SalesInvoice, invoice_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    registro.docstatus = 1
    database.session.commit()
    flash("Factura de venta aprobada.", "success")
    return redirect(url_for("ventas.ventas_factura_venta", invoice_id=invoice_id))


@ventas.route("/sales-invoice/<invoice_id>/cancel", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_factura_venta_cancel(invoice_id: str):
    """Cancela una factura de venta."""
    registro = database.session.get(SalesInvoice, invoice_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    registro.docstatus = 2
    database.session.commit()
    flash("Factura de venta cancelada.", "warning")
    return redirect(url_for("ventas.ventas_factura_venta", invoice_id=invoice_id))
