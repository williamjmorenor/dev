# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes


"""Modulo de Inventarios."""

from flask import Blueprint, redirect, render_template, request
from flask_login import login_required

from cacao_accounting.database import Item, StockEntry, UOM, Warehouse, database
from cacao_accounting.decorators import modulo_activo
from cacao_accounting.version import APPNAME

inventario = Blueprint("inventario", __name__, template_folder="templates")


@inventario.route("/")
@inventario.route("/inventario")
@inventario.route("/inventory")
@modulo_activo("inventory")
@login_required
def inventario_():
    """Definición de vista principal de inventarios."""
    return render_template("inventario.html")


@inventario.route("/item/list")
@modulo_activo("inventory")
@login_required
def inventario_articulo_lista():
    """Listado de articulos."""
    consulta = database.paginate(
        database.select(Item),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Articulos - " + APPNAME
    return render_template("inventario/articulo_lista.html", consulta=consulta, titulo=titulo)


@inventario.route("/uom/list")
@modulo_activo("inventory")
@login_required
def inventario_uom_lista():
    """Listado de unidades de medida."""
    consulta = database.paginate(
        database.select(UOM),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Unidades de Medida - " + APPNAME
    return render_template("inventario/uom_lista.html", consulta=consulta, titulo=titulo)


@inventario.route("/warehouse/list")
@modulo_activo("inventory")
@login_required
def inventario_bodega_lista():
    """Listado de bodegas."""
    consulta = database.paginate(
        database.select(Warehouse),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Bodegas - " + APPNAME
    return render_template("inventario/bodega_lista.html", consulta=consulta, titulo=titulo)


@inventario.route("/stock-entry/list")
@modulo_activo("inventory")
@login_required
def inventario_entrada_lista():
    """Listado de entradas de almacen."""
    consulta = database.paginate(
        database.select(StockEntry),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    titulo = "Listado de Entradas de Almacen - " + APPNAME
    return render_template("inventario/entrada_lista.html", consulta=consulta, titulo=titulo)


@inventario.route("/item/new", methods=["GET", "POST"])
@modulo_activo("inventory")
@login_required
def inventario_articulo_nuevo():
    """Formulario para crear un nuevo artículo."""
    from cacao_accounting.inventario.forms import FormularioArticulo

    formulario = FormularioArticulo()
    formulario.default_uom.choices = [
        (u[0].code, u[0].name)
        for u in database.session.execute(database.select(UOM)).all()
    ]
    titulo = "Nuevo Artículo - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        articulo = Item(
            code=request.form.get("code"),
            name=request.form.get("name"),
            description=request.form.get("description"),
            item_type=request.form.get("item_type", "goods"),
            is_stock_item=bool(request.form.get("is_stock_item")),
            default_uom=request.form.get("default_uom"),
        )
        database.session.add(articulo)
        database.session.commit()
        return redirect("/inventory/item/list")
    return render_template("inventario/articulo_nuevo.html", form=formulario, titulo=titulo)


@inventario.route("/item/<item_id>")
@modulo_activo("inventory")
@login_required
def inventario_articulo(item_id):
    """Detalle de artículo."""
    from flask import abort

    registro = database.session.execute(database.select(Item).filter_by(code=item_id)).first()
    if not registro:
        abort(404)
    titulo = registro[0].name + " - " + APPNAME
    return render_template("inventario/articulo.html", registro=registro[0], titulo=titulo)


@inventario.route("/uom/new", methods=["GET", "POST"])
@modulo_activo("inventory")
@login_required
def inventario_uom_nuevo():
    """Formulario para crear una nueva unidad de medida."""
    from cacao_accounting.inventario.forms import FormularioUOM

    formulario = FormularioUOM()
    titulo = "Nueva Unidad de Medida - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        uom = UOM(
            code=request.form.get("code"),
            name=request.form.get("name"),
        )
        database.session.add(uom)
        database.session.commit()
        return redirect("/inventory/uom/list")
    return render_template("inventario/uom_nuevo.html", form=formulario, titulo=titulo)


@inventario.route("/uom/<uom_id>")
@modulo_activo("inventory")
@login_required
def inventario_uom(uom_id):
    """Detalle de unidad de medida."""
    from flask import abort

    registro = database.session.execute(database.select(UOM).filter_by(code=uom_id)).first()
    if not registro:
        abort(404)
    titulo = registro[0].name + " - " + APPNAME
    return render_template("inventario/uom.html", registro=registro[0], titulo=titulo)


@inventario.route("/warehouse/new", methods=["GET", "POST"])
@modulo_activo("inventory")
@login_required
def inventario_bodega_nuevo():
    """Formulario para crear una nueva bodega."""
    from cacao_accounting.contabilidad.auxiliares import obtener_lista_entidades_por_id_razonsocial
    from cacao_accounting.inventario.forms import FormularioBodega

    formulario = FormularioBodega()
    formulario.company.choices = obtener_lista_entidades_por_id_razonsocial()
    titulo = "Nueva Bodega - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        bodega = Warehouse(
            code=request.form.get("code"),
            name=request.form.get("name"),
            company=request.form.get("company"),
        )
        database.session.add(bodega)
        database.session.commit()
        return redirect("/inventory/warehouse/list")
    return render_template("inventario/bodega_nuevo.html", form=formulario, titulo=titulo)


@inventario.route("/warehouse/<warehouse_id>")
@modulo_activo("inventory")
@login_required
def inventario_bodega(warehouse_id):
    """Detalle de bodega."""
    from flask import abort

    registro = database.session.execute(database.select(Warehouse).filter_by(code=warehouse_id)).first()
    if not registro:
        abort(404)
    titulo = registro[0].name + " - " + APPNAME
    return render_template("inventario/bodega.html", registro=registro[0], titulo=titulo)


@inventario.route("/stock-entry/new", methods=["GET", "POST"])
@modulo_activo("inventory")
@login_required
def inventario_entrada_nuevo():
    """Formulario para crear una entrada de almacén."""
    from cacao_accounting.inventario.forms import FormularioEntradaAlmacen

    formulario = FormularioEntradaAlmacen()
    titulo = "Nueva Entrada de Almacén - " + APPNAME
    return render_template("inventario/entrada_nuevo.html", form=formulario, titulo=titulo)


@inventario.route("/stock-entry/<entry_id>")
@modulo_activo("inventory")
@login_required
def inventario_entrada(entry_id):
    """Detalle de entrada de almacén."""
    from flask import abort

    registro = database.session.get(StockEntry, entry_id)
    if not registro:
        abort(404)
    titulo = (registro.document_no or entry_id) + " - " + APPNAME
    return render_template("inventario/entrada.html", registro=registro, titulo=titulo)
