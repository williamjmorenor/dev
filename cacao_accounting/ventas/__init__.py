# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Ventas."""

from decimal import Decimal

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
    SalesQuotation,
    SalesQuotationItem,
    SalesRequest,
    SalesRequestItem,
    UOM,
    database,
)
from cacao_accounting.database.helpers import get_active_naming_series
from cacao_accounting.contabilidad.posting import PostingError, cancel_document, submit_document
from cacao_accounting.document_identifiers import IdentifierConfigurationError, assign_document_identifier
from cacao_accounting.document_flow import (
    DocumentFlowError,
    create_document_relation,
    refresh_source_caches_for_target,
    revert_relations_for_target,
)
from cacao_accounting.document_flow.status import _
from cacao_accounting.decorators import modulo_activo
from cacao_accounting.party_settings import (
    build_party_company_settings,
    draft_party_company_settings,
    upsert_party_company_settings,
)
from cacao_accounting.version import APPNAME

ventas = Blueprint("ventas", __name__, template_folder="templates")


def _series_choices(entity_type: str, company: str | None) -> list[tuple[str, str]]:
    """Construye las opciones de series activas para un doctype y compania."""
    if not company:
        return [("", "")]

    return [("", "")] + [
        (str(series.id), f"{series.name} ({series.prefix_template})")
        for series in get_active_naming_series(entity_type=entity_type, company=company)
    ]


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


@ventas.route("/sales-request/list")
@modulo_activo("sales")
@login_required
def ventas_pedido_venta_lista():
    """Listado de pedidos de venta."""
    consulta = database.paginate(
        database.select(SalesRequest),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Pedidos de Venta - " + APPNAME
    return render_template("ventas/solicitud_venta_lista.html", consulta=consulta, titulo=titulo)


@ventas.route("/sales-request/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_pedido_venta_nuevo(        transaction_config=transaction_config,
    ):
    """Formulario para crear un pedido de venta."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.ventas.forms import FormularioPedidoVenta

    formulario = FormularioPedidoVenta(        transaction_config=transaction_config,
    )
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial(        transaction_config=transaction_config,
    )
    selected_company = request.values.get("company"        transaction_config=transaction_config,
    ) or (
        formulario.company.choices[0][0] if formulario.company.choices else None
            transaction_config=transaction_config,
    )
    formulario.naming_series.choices = _series_choices("sales_request", selected_company        transaction_config=transaction_config,
    )
    formulario.customer_id.choices = [("", ""        transaction_config=transaction_config,
    )] + [
        (str(p[0].id        transaction_config=transaction_config,
    ), p[0].name        transaction_config=transaction_config,
    )
        for p in database.session.execute(database.select(Party        transaction_config=transaction_config,
    ).filter_by(party_type="customer"        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    uoms_disponibles = [{"code": u[0].code, "name": u[0].name} for u in database.session.execute(database.select(UOM        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )]
    titulo = "Nuevo Pedido de Venta - " + APPNAME
    if request.method == "POST":
        try:
            customer_id = request.form.get("customer_id"        transaction_config=transaction_config,
    ) or None
            customer = database.session.get(Party, customer_id        transaction_config=transaction_config,
    ) if customer_id else None
            pedido = SalesRequest(
                customer_id=customer_id,
                customer_name=customer.name if customer else None,
                company=request.form.get("company"        transaction_config=transaction_config,
    ) or None,
                posting_date=request.form.get("posting_date"        transaction_config=transaction_config,
    ) or None,
                remarks=request.form.get("remarks"        transaction_config=transaction_config,
    ),
                docstatus=0,
                    transaction_config=transaction_config,
    )
            database.session.add(pedido        transaction_config=transaction_config,
    )
            database.session.flush(        transaction_config=transaction_config,
    )
            assign_document_identifier(
                document=pedido,
                entity_type="sales_request",
                posting_date_raw=request.form.get("posting_date"        transaction_config=transaction_config,
    ),
                naming_series_id=request.form.get("naming_series"        transaction_config=transaction_config,
    ) or None,
                    transaction_config=transaction_config,
    )
            _total_qty, total = _save_sales_request_items(pedido.id        transaction_config=transaction_config,
    )
            pedido.total = total
            pedido.base_total = total
            pedido.grand_total = total
            database.session.commit(        transaction_config=transaction_config,
    )
            flash("Pedido de venta creado correctamente.", "success"        transaction_config=transaction_config,
    )
            return redirect(url_for("ventas.ventas_pedido_venta", request_id=pedido.id        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    )
        except IdentifierConfigurationError as exc:
            database.session.rollback(        transaction_config=transaction_config,
    )
            flash(str(exc        transaction_config=transaction_config,
    ), "danger"        transaction_config=transaction_config,
    )
        transaction_config = {
        "items": items_disponibles if "items_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "uoms": uoms_disponibles if "uoms_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "columns": get_column_preferences(current_user.id, "sales.sales_request"        transaction_config=transaction_config,
    ),
    }
    return render_template(
        "ventas/solicitud_venta_nuevo.html",
        form=formulario,
        titulo=titulo,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
            transaction_config=transaction_config,
    )


@ventas.route("/sales-request/<request_id>")
@modulo_activo("sales")
@login_required
def ventas_pedido_venta(request_id: str):
    """Detalle de un pedido de venta."""
    registro = database.session.get(SalesRequest, request_id)
    if not registro:
        abort(404)
    items = database.session.execute(database.select(SalesRequestItem).filter_by(sales_request_id=request_id)).all()
    titulo = (registro.document_no or request_id) + " - " + APPNAME
    return render_template("ventas/solicitud_venta.html", registro=registro, items=items, titulo=titulo)


@ventas.route("/sales-request/<request_id>/submit", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_pedido_venta_submit(request_id: str):
    """Aprueba un pedido de venta."""
    registro = database.session.get(SalesRequest, request_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    registro.docstatus = 1
    database.session.commit()
    flash("Pedido de venta aprobado.", "success")
    return redirect(url_for("ventas.ventas_pedido_venta", request_id=request_id))


@ventas.route("/sales-request/<request_id>/cancel", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_pedido_venta_cancel(request_id: str):
    """Cancela un pedido de venta."""
    registro = database.session.get(SalesRequest, request_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    registro.docstatus = 2
    database.session.commit()
    flash("Pedido de venta cancelado.", "warning")
    return redirect(url_for("ventas.ventas_pedido_venta", request_id=request_id))


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
        database.select(SalesInvoice).filter_by(document_type="sales_invoice"),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Facturas de Venta - " + APPNAME
    return render_template("ventas/factura_venta_lista.html", consulta=consulta, titulo=titulo)


@ventas.route("/sales-invoice/debit-note/list")
@modulo_activo("sales")
@login_required
def ventas_factura_venta_nota_debito_lista():
    """Listado de notas de débito de venta."""
    consulta = database.paginate(
        database.select(SalesInvoice).filter_by(document_type="sales_debit_note"),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Notas de Débito de Venta - " + APPNAME
    return render_template(
        "ventas/factura_venta_devolucion_lista.html",
        consulta=consulta,
        titulo=titulo,
        page_heading="Listado de Notas de Débito de Venta",
        new_button_label="Nueva Nota de Débito",
        page_caption="Listado de notas de débito de venta.",
        new_document_type="sales_debit_note",
    )


@ventas.route("/sales-invoice/return/list")
@modulo_activo("sales")
@login_required
def ventas_factura_venta_devolucion_lista():
    """Listado de notas de crédito de venta."""
    consulta = database.paginate(
        database.select(SalesInvoice).filter_by(document_type="sales_credit_note"),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Notas de Crédito de Venta - " + APPNAME
    return render_template(
        "ventas/factura_venta_devolucion_lista.html",
        consulta=consulta,
        titulo=titulo,
        page_heading="Listado de Notas de Crédito de Venta",
        new_button_label="Nueva Nota de Crédito",
        page_caption="Listado de notas de crédito de venta.",
        new_document_type="sales_credit_note",
    )


@ventas.route("/sales-invoice/credit-note/list")
@modulo_activo("sales")
@login_required
def ventas_factura_venta_nota_credito_lista():
    """Alias explicito para listado de notas de crédito de venta."""
    return ventas_factura_venta_devolucion_lista()


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
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial

    formulario = FormularioCliente()
    titulo = "Nuevo Cliente - " + APPNAME
    company_choices = obtener_lista_entidades_por_id_razonsocial()
    selected_company = request.values.get("company") or (company_choices[0][0] if company_choices else None)
    company_settings = build_party_company_settings("customer", selected_company) if selected_company else None
    if request.method == "POST":
        cliente = Party(
            party_type="customer",
            name=request.form.get("name") or "",
            comercial_name=request.form.get("comercial_name"),
            tax_id=request.form.get("tax_id"),
            classification=request.form.get("classification"),
        )
        try:
            database.session.add(cliente)
            database.session.flush()
            company = request.form.get("company") or None
            if company:
                upsert_party_company_settings(
                    cliente.id,
                    "customer",
                    company,
                    is_active=request.form.get("company_is_active") is not None,
                    receivable_account_id=request.form.get("receivable_account_id") or None,
                    payable_account_id=None,
                    tax_template_id=request.form.get("tax_template_id") or None,
                    allow_purchase_invoice_without_order=False,
                    allow_purchase_invoice_without_receipt=False,
                )
            database.session.commit()
            return redirect("/sales/customer/list")
        except ValueError as exc:
            database.session.rollback()
            if selected_company:
                company_settings = draft_party_company_settings("customer", selected_company, request.form)
            flash(str(exc), "danger")
    return render_template(
        "ventas/cliente_nuevo.html",
        form=formulario,
        titulo=titulo,
        company_choices=company_choices,
        selected_company=selected_company,
        company_settings=company_settings,
    )


@ventas.route("/customer/<customer_id>")
@modulo_activo("sales")
@login_required
def ventas_cliente(customer_id):
    """Detalle de cliente."""
    registro = database.session.execute(database.select(Party).filter_by(id=customer_id, party_type="customer")).first()
    if not registro:
        abort(404)
    titulo = registro[0].name + " - " + APPNAME
    return render_template("ventas/cliente.html", registro=registro[0], titulo=titulo)


def _form_decimal(field_name: str, default: str = "0") -> Decimal:
    """Convierte un valor de formulario a Decimal."""
    value = request.form.get(field_name)
    return Decimal(str(value if value not in (None, "") else default))


def _line_amount(index: int) -> Decimal:
    """Obtiene o calcula el monto de una linea."""
    amount = request.form.get(f"amount_{index}")
    if amount not in (None, ""):
        return Decimal(str(amount))
    return _form_decimal(f"qty_{index}", "1") * _form_decimal(f"rate_{index}", "0")


def _create_line_relation(
    index: int,
    target_type: str,
    target_id: str,
    target_item_id: str,
    qty: Decimal,
    uom: str | None,
    rate: Decimal,
    amount: Decimal,
) -> None:
    """Crea relacion documental para una linea importada desde un origen."""
    source_type = request.form.get(f"source_type_{index}")
    source_id = request.form.get(f"source_id_{index}")
    source_item_id = request.form.get(f"source_item_id_{index}")
    if not (source_type and source_id and source_item_id):
        return
    create_document_relation(
        source_type=source_type,
        source_id=source_id,
        source_item_id=source_item_id,
        target_type=target_type,
        target_id=target_id,
        target_item_id=target_item_id,
        qty=qty,
        uom=uom,
        rate=rate,
        amount=amount,
    )


def _save_sales_order_items(order_id: str) -> tuple[Decimal, Decimal]:
    """Guarda las líneas de una orden de venta desde el formulario."""
    i = 0
    total_qty = Decimal("0")
    total = Decimal("0")
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            qty = _form_decimal(f"qty_{i}", "1")
            rate = _form_decimal(f"rate_{i}", "0")
            amount = _line_amount(i)
            uom = request.form.get(f"uom_{i}") or None
            linea = SalesOrderItem(
                sales_order_id=order_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=qty,
                uom=uom,
                rate=rate,
                amount=amount,
            )
            database.session.add(linea)
            database.session.flush()
            _create_line_relation(i, "sales_order", order_id, linea.id, qty, uom, rate, amount)
            total_qty += qty
            total += amount
        i += 1
    return total_qty, total


def _save_sales_request_items(request_id: str) -> tuple[Decimal, Decimal]:
    """Guarda las líneas de un pedido de venta desde el formulario."""
    i = 0
    total_qty = Decimal("0")
    total = Decimal("0")
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            qty = _form_decimal(f"qty_{i}", "1")
            rate = _form_decimal(f"rate_{i}", "0")
            amount = _line_amount(i)
            uom = request.form.get(f"uom_{i}") or None
            linea = SalesRequestItem(
                sales_request_id=request_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=qty,
                uom=uom,
                rate=rate,
                amount=amount,
            )
            database.session.add(linea)
            database.session.flush()
            _create_line_relation(i, "sales_request", request_id, linea.id, qty, uom, rate, amount)
            total_qty += qty
            total += amount
        i += 1
    return total_qty, total


def _save_sales_quotation_items(quotation_id: str) -> tuple[Decimal, Decimal]:
    """Guarda las líneas de una cotización de venta desde el formulario."""
    i = 0
    total_qty = Decimal("0")
    total = Decimal("0")
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            qty = _form_decimal(f"qty_{i}", "1")
            rate = _form_decimal(f"rate_{i}", "0")
            amount = _line_amount(i)
            uom = request.form.get(f"uom_{i}") or None
            linea = SalesQuotationItem(
                sales_quotation_id=quotation_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=qty,
                uom=uom,
                rate=rate,
                amount=amount,
            )
            database.session.add(linea)
            database.session.flush()
            _create_line_relation(i, "sales_quotation", quotation_id, linea.id, qty, uom, rate, amount)
            total_qty += qty
            total += amount
        i += 1
    return total_qty, total


def _save_delivery_note_items(note_id: str) -> tuple[Decimal, Decimal]:
    """Guarda las líneas de una nota de entrega desde el formulario."""
    i = 0
    total_qty = Decimal("0")
    total = Decimal("0")
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            qty = _form_decimal(f"qty_{i}", "1")
            rate = _form_decimal(f"rate_{i}", "0")
            amount = _line_amount(i)
            uom = request.form.get(f"uom_{i}") or None
            linea = DeliveryNoteItem(
                delivery_note_id=note_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=qty,
                uom=uom,
                rate=rate,
                amount=amount,
                warehouse=request.form.get(f"warehouse_{i}") or None,
            )
            database.session.add(linea)
            database.session.flush()
            _create_line_relation(i, "delivery_note", note_id, linea.id, qty, uom, rate, amount)
            total_qty += qty
            total += amount
        i += 1
    return total_qty, total


def _save_sales_invoice_items(invoice_id: str) -> tuple[Decimal, Decimal]:
    """Guarda las líneas de una factura de venta desde el formulario."""
    i = 0
    total_qty = Decimal("0")
    total = Decimal("0")
    while request.form.get(f"item_code_{i}"):
        item_code = request.form.get(f"item_code_{i}", "")
        if item_code.strip():
            qty = _form_decimal(f"qty_{i}", "1")
            rate = _form_decimal(f"rate_{i}", "0")
            amount = _line_amount(i)
            uom = request.form.get(f"uom_{i}") or None
            linea = SalesInvoiceItem(
                sales_invoice_id=invoice_id,
                item_code=item_code,
                item_name=request.form.get(f"item_name_{i}", ""),
                qty=qty,
                uom=uom,
                rate=rate,
                amount=amount,
            )
            database.session.add(linea)
            database.session.flush()
            _create_line_relation(i, "sales_invoice", invoice_id, linea.id, qty, uom, rate, amount)
            total_qty += qty
            total += amount
        i += 1
    return total_qty, total


@ventas.route("/sales-order/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_orden_venta_nuevo(        transaction_config=transaction_config,
    ):
    """Formulario para crear una orden de venta."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.ventas.forms import FormularioOrdenVenta

    formulario = FormularioOrdenVenta(        transaction_config=transaction_config,
    )
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial(        transaction_config=transaction_config,
    )
    selected_company = request.values.get("company"        transaction_config=transaction_config,
    ) or (
        formulario.company.choices[0][0] if formulario.company.choices else None
            transaction_config=transaction_config,
    )
    formulario.naming_series.choices = _series_choices("sales_order", selected_company        transaction_config=transaction_config,
    )
    formulario.customer_id.choices = [("", ""        transaction_config=transaction_config,
    )] + [
        (str(p[0].id        transaction_config=transaction_config,
    ), p[0].name        transaction_config=transaction_config,
    )
        for p in database.session.execute(database.select(Party        transaction_config=transaction_config,
    ).filter_by(party_type="customer"        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    from_order_id = request.args.get("from_order"        transaction_config=transaction_config,
    ) or request.form.get("from_order"        transaction_config=transaction_config,
    )
    from_quotation_id = request.args.get("from_quotation"        transaction_config=transaction_config,
    ) or request.form.get("from_quotation"        transaction_config=transaction_config,
    )
    orden_origen = database.session.get(SalesOrder, from_order_id        transaction_config=transaction_config,
    ) if from_order_id else None
    cotizacion_origen = database.session.get(SalesQuotation, from_quotation_id        transaction_config=transaction_config,
    ) if from_quotation_id else None
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    uoms_disponibles = [{"code": u[0].code, "name": u[0].name} for u in database.session.execute(database.select(UOM        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )]
    titulo = "Nueva Orden de Venta - " + APPNAME
    if request.method == "POST":
        try:
            customer_id = request.form.get("customer_id"        transaction_config=transaction_config,
    ) or None
            customer = database.session.get(Party, customer_id        transaction_config=transaction_config,
    ) if customer_id else None
            orden = SalesOrder(
                customer_id=customer_id,
                customer_name=customer.name if customer else None,
                sales_quotation_id=from_quotation_id or None,
                company=request.form.get("company"        transaction_config=transaction_config,
    ) or None,
                posting_date=request.form.get("posting_date"        transaction_config=transaction_config,
    ) or None,
                remarks=request.form.get("remarks"        transaction_config=transaction_config,
    ),
                docstatus=0,
                    transaction_config=transaction_config,
    )
            database.session.add(orden        transaction_config=transaction_config,
    )
            database.session.flush(        transaction_config=transaction_config,
    )
            assign_document_identifier(
                document=orden,
                entity_type="sales_order",
                posting_date_raw=request.form.get("posting_date"        transaction_config=transaction_config,
    ),
                naming_series_id=request.form.get("naming_series"        transaction_config=transaction_config,
    ) or None,
                    transaction_config=transaction_config,
    )
            _total_qty, total = _save_sales_order_items(orden.id        transaction_config=transaction_config,
    )
            orden.total = total
            orden.base_total = total
            orden.grand_total = total
            database.session.commit(        transaction_config=transaction_config,
    )
            flash("Orden de venta creada correctamente.", "success"        transaction_config=transaction_config,
    )
            return redirect(url_for("ventas.ventas_orden_venta", order_id=orden.id        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    )
        except IdentifierConfigurationError as exc:
            database.session.rollback(        transaction_config=transaction_config,
    )
            flash(str(exc        transaction_config=transaction_config,
    ), "danger"        transaction_config=transaction_config,
    )
        transaction_config = {
        "items": items_disponibles if "items_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "uoms": uoms_disponibles if "uoms_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "columns": get_column_preferences(current_user.id, "sales.sales_order"        transaction_config=transaction_config,
    ),
    }
    return render_template(
        "ventas/orden_venta_nuevo.html",
        form=formulario,
        titulo=titulo,
        orden_origen=orden_origen,
        cotizacion_origen=cotizacion_origen,
        from_order_id=from_order_id,
        from_quotation_id=from_quotation_id,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
            transaction_config=transaction_config,
    )


@ventas.route("/sales-order/<order_id>")
@modulo_activo("sales")
@login_required
def ventas_orden_venta(order_id):
    """Detalle de orden de venta."""
    registro = database.session.get(SalesOrder, order_id)
    if not registro:
        abort(404)
    items = database.session.execute(database.select(SalesOrderItem).filter_by(sales_order_id=order_id)).all()
    titulo = (registro.document_no or order_id) + " - " + APPNAME
    return render_template("ventas/orden_venta.html", registro=registro, items=items, titulo=titulo)


@ventas.route("/quotation/list")
@ventas.route("/request-for-quotation/list")
@modulo_activo("sales")
@login_required
def ventas_cotizacion_lista():
    """Listado de cotizaciones de venta."""
    consulta = database.paginate(
        database.select(SalesQuotation),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Cotizaciones de Venta - " + APPNAME
    return render_template("ventas/cotizacion_lista.html", consulta=consulta, titulo=titulo)


@ventas.route("/quotation/new", methods=["GET", "POST"])
@ventas.route("/request-for-quotation/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_cotizacion_nueva(        transaction_config=transaction_config,
    ):
    """Formulario para crear una cotización de venta."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.ventas.forms import FormularioCotizacionVenta

    formulario = FormularioCotizacionVenta(        transaction_config=transaction_config,
    )
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial(        transaction_config=transaction_config,
    )
    selected_company = request.values.get("company"        transaction_config=transaction_config,
    ) or (
        formulario.company.choices[0][0] if formulario.company.choices else None
            transaction_config=transaction_config,
    )
    formulario.naming_series.choices = _series_choices("sales_quotation", selected_company        transaction_config=transaction_config,
    )
    formulario.customer_id.choices = [("", ""        transaction_config=transaction_config,
    )] + [
        (str(p[0].id        transaction_config=transaction_config,
    ), p[0].name        transaction_config=transaction_config,
    )
        for p in database.session.execute(database.select(Party        transaction_config=transaction_config,
    ).filter_by(party_type="customer"        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    from_request_id = request.args.get("from_request"        transaction_config=transaction_config,
    ) or request.form.get("from_request"        transaction_config=transaction_config,
    )
    solicitud_origen = database.session.get(SalesRequest, from_request_id        transaction_config=transaction_config,
    ) if from_request_id else None
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    uoms_disponibles = [{"code": u[0].code, "name": u[0].name} for u in database.session.execute(database.select(UOM        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )]
    titulo = "Nueva Cotización - " + APPNAME
    if request.method == "POST":
        try:
            customer_id = request.form.get("customer_id"        transaction_config=transaction_config,
    ) or None
            customer = database.session.get(Party, customer_id        transaction_config=transaction_config,
    ) if customer_id else None
            cotizacion = SalesQuotation(
                customer_id=customer_id,
                customer_name=customer.name if customer else None,
                sales_request_id=from_request_id or None,
                company=request.form.get("company"        transaction_config=transaction_config,
    ) or None,
                posting_date=request.form.get("posting_date"        transaction_config=transaction_config,
    ) or None,
                remarks=request.form.get("remarks"        transaction_config=transaction_config,
    ),
                docstatus=0,
                    transaction_config=transaction_config,
    )
            database.session.add(cotizacion        transaction_config=transaction_config,
    )
            database.session.flush(        transaction_config=transaction_config,
    )
            assign_document_identifier(
                document=cotizacion,
                entity_type="sales_quotation",
                posting_date_raw=request.form.get("posting_date"        transaction_config=transaction_config,
    ),
                naming_series_id=request.form.get("naming_series"        transaction_config=transaction_config,
    ) or None,
                    transaction_config=transaction_config,
    )
            _total_qty, total = _save_sales_quotation_items(cotizacion.id        transaction_config=transaction_config,
    )
            cotizacion.total = total
            cotizacion.base_total = total
            cotizacion.grand_total = total
            database.session.commit(        transaction_config=transaction_config,
    )
            flash("Cotización creada correctamente.", "success"        transaction_config=transaction_config,
    )
            return redirect(url_for("ventas.ventas_cotizacion", quotation_id=cotizacion.id        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    )
        except IdentifierConfigurationError as exc:
            database.session.rollback(        transaction_config=transaction_config,
    )
            flash(str(exc        transaction_config=transaction_config,
    ), "danger"        transaction_config=transaction_config,
    )
        transaction_config = {
        "items": items_disponibles if "items_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "uoms": uoms_disponibles if "uoms_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "columns": get_column_preferences(current_user.id, "sales.sales_quotation"        transaction_config=transaction_config,
    ),
    }
    return render_template(
        "ventas/cotizacion_nuevo.html",
        form=formulario,
        titulo=titulo,
        solicitud_origen=solicitud_origen,
        from_request_id=from_request_id,
        items_disponibles=items_disponibles,
        uoms_disponibles=uoms_disponibles,
            transaction_config=transaction_config,
    )


@ventas.route("/quotation/<quotation_id>")
@modulo_activo("sales")
@login_required
def ventas_cotizacion(quotation_id: str):
    """Detalle de cotización de venta."""
    registro = database.session.get(SalesQuotation, quotation_id)
    if not registro:
        abort(404)
    items = database.session.execute(database.select(SalesQuotationItem).filter_by(sales_quotation_id=quotation_id)).all()
    titulo = (registro.document_no or quotation_id) + " - " + APPNAME
    return render_template("ventas/cotizacion.html", registro=registro, items=items, titulo=titulo)


@ventas.route("/sales-quotation/<quotation_id>/submit", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_cotizacion_submit(quotation_id: str):
    """Aprueba una cotización de venta."""
    registro = database.session.get(SalesQuotation, quotation_id)
    if not registro:
        abort(404)
    if registro.docstatus != 0:
        abort(400)
    registro.docstatus = 1
    database.session.commit()
    flash("Cotización de venta aprobada.", "success")
    return redirect(url_for("ventas.ventas_cotizacion", quotation_id=quotation_id))


@ventas.route("/sales-quotation/<quotation_id>/cancel", methods=["POST"])
@modulo_activo("sales")
@login_required
def ventas_cotizacion_cancel(quotation_id: str):
    """Cancela una cotización de venta."""
    registro = database.session.get(SalesQuotation, quotation_id)
    if not registro:
        abort(404)
    if registro.docstatus != 1:
        abort(400)
    registro.docstatus = 2
    revert_relations_for_target("sales_quotation", quotation_id)
    database.session.commit()
    flash("Cotización de venta cancelada.", "warning")
    return redirect(url_for("ventas.ventas_cotizacion", quotation_id=quotation_id))


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
    revert_relations_for_target("sales_order", order_id)
    database.session.commit()
    flash("Orden de venta cancelada.", "warning")
    return redirect(url_for("ventas.ventas_orden_venta", order_id=order_id))


@ventas.route("/delivery-note/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_entrega_nuevo(        transaction_config=transaction_config,
    ):
    """Formulario para crear una nota de entrega."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.database import Warehouse
    from cacao_accounting.ventas.forms import FormularioEntregaVenta

    formulario = FormularioEntregaVenta(        transaction_config=transaction_config,
    )
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial(        transaction_config=transaction_config,
    )
    selected_company = request.values.get("company"        transaction_config=transaction_config,
    ) or (
        formulario.company.choices[0][0] if formulario.company.choices else None
            transaction_config=transaction_config,
    )
    formulario.naming_series.choices = _series_choices("delivery_note", selected_company        transaction_config=transaction_config,
    )
    formulario.customer_id.choices = [("", ""        transaction_config=transaction_config,
    )] + [
        (str(p[0].id        transaction_config=transaction_config,
    ), p[0].name        transaction_config=transaction_config,
    )
        for p in database.session.execute(database.select(Party        transaction_config=transaction_config,
    ).filter_by(party_type="customer"        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    from_order_id = request.args.get("from_order"        transaction_config=transaction_config,
    ) or request.form.get("from_order"        transaction_config=transaction_config,
    )
    orden_origen = database.session.get(SalesOrder, from_order_id        transaction_config=transaction_config,
    ) if from_order_id else None
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    uoms_disponibles = [{"code": u[0].code, "name": u[0].name} for u in database.session.execute(database.select(UOM        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )]
    bodegas_disponibles = [
        {"code": w[0].code, "name": w[0].name} for w in database.session.execute(database.select(Warehouse        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    titulo = "Nueva Nota de Entrega - " + APPNAME
    if request.method == "POST":
        try:
            entrega = DeliveryNote(
                customer_id=request.form.get("customer_id"        transaction_config=transaction_config,
    ) or None,
                company=request.form.get("company"        transaction_config=transaction_config,
    ) or None,
                posting_date=request.form.get("posting_date"        transaction_config=transaction_config,
    ) or None,
                sales_order_id=request.form.get("from_order"        transaction_config=transaction_config,
    ) or None,
                remarks=request.form.get("remarks"        transaction_config=transaction_config,
    ),
                docstatus=0,
                    transaction_config=transaction_config,
    )
            database.session.add(entrega        transaction_config=transaction_config,
    )
            database.session.flush(        transaction_config=transaction_config,
    )
            assign_document_identifier(
                document=entrega,
                entity_type="delivery_note",
                posting_date_raw=request.form.get("posting_date"        transaction_config=transaction_config,
    ),
                naming_series_id=request.form.get("naming_series"        transaction_config=transaction_config,
    ) or None,
                    transaction_config=transaction_config,
    )
            _total_qty, total = _save_delivery_note_items(entrega.id        transaction_config=transaction_config,
    )
        except (DocumentFlowError, IdentifierConfigurationError        transaction_config=transaction_config,
    ) as exc:
            database.session.rollback(        transaction_config=transaction_config,
    )
            flash(str(exc        transaction_config=transaction_config,
    ), "danger"        transaction_config=transaction_config,
    )
                transaction_config = {
        "items": items_disponibles if "items_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "uoms": uoms_disponibles if "uoms_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "columns": get_column_preferences(current_user.id, "sales.delivery_note"        transaction_config=transaction_config,
    ),
    }
    return render_template(
                "ventas/entrega_nuevo.html",
                form=formulario,
                titulo=titulo,
                orden_origen=orden_origen,
                from_order_id=from_order_id,
                items_disponibles=items_disponibles,
                uoms_disponibles=uoms_disponibles,
                bodegas_disponibles=bodegas_disponibles,
                    transaction_config=transaction_config,
    )
        entrega.total = total
        entrega.grand_total = total
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
    items = database.session.execute(database.select(DeliveryNoteItem).filter_by(delivery_note_id=note_id)).all()
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
    try:
        submit_document(registro)
        database.session.commit()
        flash("Nota de entrega aprobada.", "success")
    except PostingError as exc:
        database.session.rollback()
        flash(str(exc), "danger")
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
    try:
        cancel_document(registro)
        revert_relations_for_target("delivery_note", note_id)
        refresh_source_caches_for_target("delivery_note", note_id)
        database.session.commit()
        flash("Nota de entrega cancelada.", "warning")
    except PostingError as exc:
        database.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("ventas.ventas_entrega", note_id=note_id))


@ventas.route("/sales-invoice/new", methods=["GET", "POST"])
@modulo_activo("sales")
@login_required
def ventas_factura_venta_nuevo(        transaction_config=transaction_config,
    ):
    """Formulario para crear una factura de venta."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.ventas.forms import FormularioFacturaVenta

    formulario = FormularioFacturaVenta(        transaction_config=transaction_config,
    )
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial(        transaction_config=transaction_config,
    )
    selected_company = request.values.get("company"        transaction_config=transaction_config,
    ) or (
        formulario.company.choices[0][0] if formulario.company.choices else None
            transaction_config=transaction_config,
    )
    formulario.naming_series.choices = _series_choices("sales_invoice", selected_company        transaction_config=transaction_config,
    )
    formulario.customer_id.choices = [("", ""        transaction_config=transaction_config,
    )] + [
        (str(p[0].id        transaction_config=transaction_config,
    ), p[0].name        transaction_config=transaction_config,
    )
        for p in database.session.execute(database.select(Party        transaction_config=transaction_config,
    ).filter_by(party_type="customer"        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    from_order_id = request.args.get("from_order"        transaction_config=transaction_config,
    ) or request.form.get("from_order"        transaction_config=transaction_config,
    )
    from_note_id = request.args.get("from_note"        transaction_config=transaction_config,
    ) or request.form.get("from_note"        transaction_config=transaction_config,
    )
    from_invoice = request.args.get("from_invoice"        transaction_config=transaction_config,
    ) or request.form.get("from_invoice"        transaction_config=transaction_config,
    )
    from_return_id = request.args.get("from_return"        transaction_config=transaction_config,
    ) or request.form.get("from_return"        transaction_config=transaction_config,
    )
    from_invoice_id = from_invoice or from_return_id
    document_type = (
        request.args.get("document_type"        transaction_config=transaction_config,
    )
        or request.form.get("document_type"        transaction_config=transaction_config,
    )
        or ("sales_invoice" if not from_invoice_id else "sales_credit_note"        transaction_config=transaction_config,
    )
            transaction_config=transaction_config,
    )
    formulario.is_return.data = document_type == "sales_credit_note"
    orden_origen = database.session.get(SalesOrder, from_order_id        transaction_config=transaction_config,
    ) if from_order_id else None
    entrega_origen = database.session.get(DeliveryNote, from_note_id        transaction_config=transaction_config,
    ) if from_note_id else None
    factura_origen = database.session.get(SalesInvoice, from_invoice_id        transaction_config=transaction_config,
    ) if from_invoice_id else None
    items_disponibles = [
        {"code": i[0].code, "name": i[0].name, "uom": i[0].default_uom}
        for i in database.session.execute(database.select(Item        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )
    ]
    uoms_disponibles = [{"code": u[0].code, "name": u[0].name} for u in database.session.execute(database.select(UOM        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    ).all(        transaction_config=transaction_config,
    )]
    titulo = "Nueva Factura de Venta - " + APPNAME
    if request.method == "POST":
        try:
            document_type = request.form.get("document_type"        transaction_config=transaction_config,
    ) or "sales_invoice"
            factura = SalesInvoice(
                customer_id=request.form.get("customer_id"        transaction_config=transaction_config,
    ) or None,
                company=request.form.get("company"        transaction_config=transaction_config,
    ) or None,
                posting_date=request.form.get("posting_date"        transaction_config=transaction_config,
    ) or None,
                document_type=document_type,
                sales_order_id=request.form.get("from_order"        transaction_config=transaction_config,
    ) or None,
                delivery_note_id=request.form.get("from_note"        transaction_config=transaction_config,
    ) or None,
                is_return=document_type == "sales_credit_note",
                reversal_of=(
                    (request.form.get("from_invoice"        transaction_config=transaction_config,
    ) or request.form.get("from_return"        transaction_config=transaction_config,
    )        transaction_config=transaction_config,
    )
                    if document_type in ("sales_credit_note", "sales_debit_note"        transaction_config=transaction_config,
    )
                    else None
                        transaction_config=transaction_config,
    ),
                remarks=request.form.get("remarks"        transaction_config=transaction_config,
    ),
                docstatus=0,
                    transaction_config=transaction_config,
    )
            database.session.add(factura        transaction_config=transaction_config,
    )
            database.session.flush(        transaction_config=transaction_config,
    )
            assign_document_identifier(
                document=factura,
                entity_type="sales_invoice",
                posting_date_raw=request.form.get("posting_date"        transaction_config=transaction_config,
    ),
                naming_series_id=request.form.get("naming_series"        transaction_config=transaction_config,
    ) or None,
                    transaction_config=transaction_config,
    )
            _total_qty, total = _save_sales_invoice_items(factura.id        transaction_config=transaction_config,
    )
        except (DocumentFlowError, IdentifierConfigurationError        transaction_config=transaction_config,
    ) as exc:
            database.session.rollback(        transaction_config=transaction_config,
    )
            flash(str(exc        transaction_config=transaction_config,
    ), "danger"        transaction_config=transaction_config,
    )
                transaction_config = {
        "items": items_disponibles if "items_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "uoms": uoms_disponibles if "uoms_disponibles" in locals(        transaction_config=transaction_config,
    ) else [],
        "columns": get_column_preferences(current_user.id, "sales.sales_invoice"        transaction_config=transaction_config,
    ),
    }
    return render_template(
                "ventas/factura_venta_nuevo.html",
                form=formulario,
                titulo=titulo,
                orden_origen=orden_origen,
                entrega_origen=entrega_origen,
                factura_origen=factura_origen,
                from_order_id=from_order_id,
                from_note_id=from_note_id,
                from_invoice_id=from_invoice_id,
                from_return_id=from_return_id,
                document_type=document_type,
                items_disponibles=items_disponibles,
                uoms_disponibles=uoms_disponibles,
                    transaction_config=transaction_config,
    )
        factura.total = total
        factura.base_total = total
        factura.grand_total = total
        factura.base_grand_total = total
        factura.outstanding_amount = total
        factura.base_outstanding_amount = total
        database.session.commit()
        flash("Factura de venta creada correctamente.", "success")
        return redirect(url_for("ventas.ventas_factura_venta", invoice_id=factura.id))
    return render_template(
        "ventas/factura_venta_nuevo.html",
        form=formulario,
        titulo=titulo,
        orden_origen=orden_origen,
        entrega_origen=entrega_origen,
        factura_origen=factura_origen,
        from_order_id=from_order_id,
        from_note_id=from_note_id,
        from_invoice_id=from_invoice_id,
        from_return_id=from_return_id,
        document_type=document_type,
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
    items = database.session.execute(database.select(SalesInvoiceItem).filter_by(sales_invoice_id=invoice_id)).all()
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
    try:
        submit_document(registro)
        database.session.commit()
    except PostingError as exc:
        database.session.rollback()
        flash(_(str(exc)), "danger")
        return redirect(url_for("ventas.ventas_factura_venta", invoice_id=invoice_id))
    flash(_("Factura de venta aprobada y contabilizada."), "success")
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
    try:
        cancel_document(registro)
        revert_relations_for_target("sales_invoice", invoice_id)
        refresh_source_caches_for_target("sales_invoice", invoice_id)
        database.session.commit()
    except PostingError as exc:
        database.session.rollback()
        flash(_(str(exc)), "danger")
        return redirect(url_for("ventas.ventas_factura_venta", invoice_id=invoice_id))
    flash(_("Factura de venta cancelada con reverso contable."), "warning")
    return redirect(url_for("ventas.ventas_factura_venta", invoice_id=invoice_id))
