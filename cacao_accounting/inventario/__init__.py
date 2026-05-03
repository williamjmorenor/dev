# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes


"""Modulo de Inventarios."""

from flask import Blueprint, render_template, request
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
