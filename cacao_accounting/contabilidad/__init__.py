# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Contabilidad."""

# ---------------------------------------------------------------------------------------
# Libreria estandar
# --------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
# Librerias de terceros
# ---------------------------------------------------------------------------------------
from flask import Blueprint, flash, jsonify, redirect, render_template, request
from flask.helpers import url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

# ---------------------------------------------------------------------------------------
# Recursos locales
# ---------------------------------------------------------------------------------------
from cacao_accounting.contabilidad.auxiliares import (
    obtener_catalogo,
    obtener_catalogo_base,
    obtener_catalogo_centros_costo_base,
    obtener_centros_costos,
    obtener_entidad,
    obtener_entidades,
    obtener_lista_entidades_por_id_razonsocial,
    obtener_lista_monedas,
)
from cacao_accounting.setup.service import (
    available_catalog_files,
    create_company,
)
from cacao_accounting.contabilidad.gl import gl
from cacao_accounting.database import STATUS, database
from cacao_accounting.decorators import modulo_activo, verifica_acceso
from cacao_accounting.version import APPNAME

# <------------------------------------------------------------------------------------------------------------------------> #
contabilidad = Blueprint("contabilidad", __name__, template_folder="templates")
contabilidad.register_blueprint(gl, url_prefix="/gl")
LISTA_ENTIDADES = redirect("/accounting/entity/list")


# <------------------------------------------------------------------------------------------------------------------------> #
# Monedas
@contabilidad.route("/currency/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def monedas():
    """Listado de monedas registradas en el sistema."""
    from cacao_accounting.database import Currency

    CONSULTA = database.paginate(
        database.select(Currency),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )

    TITULO = "Listado de Monedas - " + " - " + APPNAME
    return render_template(
        "contabilidad/moneda_lista.html",
        consulta=CONSULTA,
        titulo=TITULO,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Contabilidad
@contabilidad.route("/")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def conta():
    """Pantalla principal del modulo contabilidad."""
    TITULO = "Módulo Contabilidad - " + APPNAME
    return render_template(
        "contabilidad.html",
        titulo=TITULO,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Entidades
@contabilidad.route("/entity/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def entidades():
    """Listado de entidades."""
    from cacao_accounting.database import Entity

    CONSULTA = database.paginate(
        database.select(Entity),  # noqa: E712
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    TITULO = "Listado de Entidades - " + APPNAME
    return render_template(
        "contabilidad/entidad_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


@contabilidad.route("/entity/<entidad_id>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def entidad(entidad_id):
    """Entidad individual."""
    from cacao_accounting.database import Entity

    registro = database.session.execute(database.select(Entity).filter_by(code=entidad_id)).first()

    return render_template(
        "contabilidad/entidad.html",
        registro=registro[0],
    )


@contabilidad.route("/entity/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nueva_entidad():
    """Formulario para crear una nueva entidad."""
    from cacao_accounting.contabilidad.forms import FormularioEntidad

    formulario = FormularioEntidad()
    formulario.moneda.choices = obtener_lista_monedas()
    formulario.catalogo_origen.choices = [("", "Seleccione un catálogo existente")] + available_catalog_files()

    TITULO = "Crear Nueva Entidad - " + APPNAME
    if formulario.validate_on_submit():
        try:
            ENTIDAD = create_company(
                {
                    "id": formulario.id.data,
                    "razon_social": formulario.razon_social.data,
                    "nombre_comercial": formulario.nombre_comercial.data,
                    "id_fiscal": formulario.id_fiscal.data,
                    "moneda": formulario.moneda.data,
                    "pais": formulario.pais.data,
                    "tipo_entidad": formulario.tipo_entidad.data,
                },
                catalogo_tipo=formulario.catalogo.data,
                country=formulario.pais.data,
                idioma=formulario.idioma.data,
                catalogo_archivo=formulario.catalogo_origen.data if formulario.catalogo.data == "preexistente" else None,
                status="activo",
                default=False,
            )
        except ValueError as exc:
            database.session.rollback()
            flash(str(exc), "danger")
            return render_template(
                "contabilidad/entidad_crear.html",
                form=formulario,
                titulo=TITULO,
            )

        from cacao_accounting.compras.purchase_reconciliation_service import seed_matching_config_for_company

        seed_matching_config_for_company(ENTIDAD.code)
        database.session.commit()

        return LISTA_ENTIDADES
    elif request.method == "POST":
        flash("Complete los campos correctamente.", "danger")

    return render_template(
        "contabilidad/entidad_crear.html",
        form=formulario,
        titulo=TITULO,
    )


@contabilidad.route("/entity/edit/<id_entidad>", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def editar_entidad(id_entidad):
    """Formulario para editar una entidad."""
    from cacao_accounting.contabilidad.forms import FormularioEntidad
    from cacao_accounting.database import Entity

    ENTIDAD = database.session.execute(database.select(Entity).filter_by(code=id_entidad)).first()
    ENTIDAD = ENTIDAD[0]

    if request.method == "POST":
        ENTIDAD.tax_id = request.form.get("id_fiscal", None)
        ENTIDAD.name = request.form.get("nombre_comercial", None)
        ENTIDAD.company_name = request.form.get("razon_social", None)
        ENTIDAD.phone1 = request.form.get("telefono1", None)
        ENTIDAD.phone2 = request.form.get("telefono2", None)
        ENTIDAD.e_mail = request.form.get("correo_electronico", None)
        ENTIDAD.fax = request.form.get("fax", None)
        ENTIDAD.web = request.form.get("web", None)
        database.session.add(ENTIDAD)
        database.session.commit()
        return redirect(url_for("contabilidad.entidad", entidad_id=ENTIDAD.entidad))
    else:
        DATA = {
            "nombre_comercial": ENTIDAD.name,
            "razon_social": ENTIDAD.company_name,
            "id_fiscal": ENTIDAD.tax_id,
            "correo_electronico": ENTIDAD.e_mail,
            "telefono1": ENTIDAD.phone1,
            "telefono2": ENTIDAD.phone2,
            "fax": ENTIDAD.fax,
            "web": ENTIDAD.web,
        }

        formulario = FormularioEntidad(data=DATA)
        formulario.moneda.choices = obtener_lista_monedas()
        return render_template("contabilidad/entidad_editar.html", entidad=ENTIDAD, form=formulario)


@contabilidad.route("/entity/delete/<id_entidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def eliminar_entidad(id_entidad):
    """Elimina una entidad de sistema."""
    from cacao_accounting.database import Entity

    ENTIDAD = database.session.execute(database.select(Entity).filter_by(id=id_entidad)).first()
    database.session.delete(ENTIDAD[0])
    database.session.commit()

    return LISTA_ENTIDADES


@contabilidad.route("/entity/set_inactive/<id_entidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def inactivar_entidad(id_entidad):
    """Estable una entidad como inactiva."""
    from cacao_accounting.database import Entity

    ENTIDAD = database.session.execute(database.select(Entity).filter_by(id=id_entidad)).first()
    ENTIDAD[0].habilitada = False
    database.session.commit()

    return LISTA_ENTIDADES


@contabilidad.route("/entity/set_active/<id_entidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def activar_entidad(id_entidad):
    """Estable una entidad como inactiva."""
    from cacao_accounting.database import Entity

    ENTIDAD = database.session.execute(database.select(Entity).filter_by(id=id_entidad)).first()
    ENTIDAD[0].habilitada = True
    database.session.commit()

    return LISTA_ENTIDADES


@contabilidad.route("/entity/set_default/<id_entidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def predeterminar_entidad(id_entidad):
    """Establece una entidad como predeterminada."""
    from cacao_accounting.database import Entity

    # Establece cualquier entidad establecida como predeterminada a falso
    ENTIDAD_PREDETERMINADA = database.session.execute(database.select(Entity).filter_by(predeterminada=True)).all()

    if ENTIDAD_PREDETERMINADA:
        for e in ENTIDAD_PREDETERMINADA:
            e[0].predeterminada = False

    ENTIDAD = database.session.execute(database.select(Entity).filter_by(id=id_entidad)).first()
    ENTIDAD[0].predeterminada = True
    database.session.commit()

    return LISTA_ENTIDADES


# <------------------------------------------------------------------------------------------------------------------------> #
# Unidades de Negocio
@contabilidad.route("/unit/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def unidades():
    """Listado de unidades de negocios."""
    from cacao_accounting.database import Unit, database

    CONSULTA = database.paginate(
        database.select(Unit),  # noqa: E712
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )

    TITULO = "Listado de Unidades de Negocio - " + APPNAME
    return render_template(
        "contabilidad/unidad_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


@contabilidad.route("/unit/<id_unidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def unidad(id_unidad):
    """Unidad de negocios."""
    from cacao_accounting.database import Unit

    REGISTRO = database.session.execute(database.select(Unit).filter_by(code=id_unidad)).first()
    return render_template("contabilidad/unidad.html", registro=REGISTRO[0])


@contabilidad.route("/unit/delete/<id_unidad>")
@modulo_activo("accounting")
@login_required
def eliminar_unidad(id_unidad):
    """Elimina una unidad de negocios de la base de datos."""
    from cacao_accounting.database import Unit

    unidad = database.session.execute(database.select(Unit).filter_by(code=id_unidad)).scalar_one_or_none()
    if unidad:
        database.session.delete(unidad)
        database.session.commit()
    return redirect(url_for("contabilidad.unidades"))


@contabilidad.route("/unit/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nueva_unidad():
    """Formulario para crear una nueva unidad de negocios."""
    from cacao_accounting.contabilidad.forms import FormularioUnidad
    from cacao_accounting.database import Unit

    formulario = FormularioUnidad()
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    TITULO = "Crear Nueva Unidad de Negocio - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        DATA = Unit(
            code=request.form.get("id", None),
            name=request.form.get("nombre", None),
            entity=request.form.get("entidad", None),
            status="activo",
        )
        database.session.add(DATA)
        database.session.commit()

        return redirect(url_for("contabilidad.unidades"))
    return render_template(
        "contabilidad/unidad_crear.html",
        titulo=TITULO,
        form=formulario,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Libro de Contabilidad
@contabilidad.route("/book/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def libros():
    """Listado de libros de contabilidad."""
    from cacao_accounting.database import Book, database

    CONSULTA = database.paginate(
        database.select(Book),  # noqa: E712
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )

    TITULO = "Listado de Libros de Contabilidad - " + APPNAME
    return render_template(
        "contabilidad/book_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


@contabilidad.route("/book/<id_unidad>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def libro(id_unidad):
    """Libro de Contabilidad."""
    from cacao_accounting.database import Book

    REGISTRO = database.session.execute(database.select(Book).filter_by(code=id_unidad)).first()
    return render_template("contabilidad/book.html", registro=REGISTRO[0])


@contabilidad.route("/book/delete/<id_unidad>")
@modulo_activo("accounting")
@login_required
def eliminar_libro(id_unidad):
    """Elimina un libro de contabilidad de la base de datos."""
    from cacao_accounting.database import Book

    libro = database.session.execute(database.select(Book).filter_by(code=id_unidad)).scalar_one_or_none()
    if libro:
        database.session.delete(libro)
        database.session.commit()
    return redirect(url_for("contabilidad.libros"))


@contabilidad.route("/book/edit/<id_libro>", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def editar_libro(id_libro):
    """Editar un libro de contabilidad."""
    from cacao_accounting.contabilidad.forms import FormularioLibro
    from cacao_accounting.database import Book

    libro = database.session.execute(database.select(Book).filter_by(code=id_libro)).scalar_one_or_none()
    if libro is None:
        return redirect(url_for("contabilidad.libros"))

    formulario = FormularioLibro(obj=libro)
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.moneda.choices = obtener_lista_monedas()
    formulario.id.data = libro.code
    formulario.moneda.data = libro.currency
    formulario.estado.data = libro.status or "activo"
    TITULO = "Editar Libro de Contabilidad - " + APPNAME

    if formulario.validate_on_submit():
        libro.name = formulario.nombre.data
        libro.entity = formulario.entidad.data
        libro.currency = formulario.moneda.data
        libro.status = formulario.estado.data
        database.session.commit()
        return redirect(url_for("contabilidad.libros"))

    return render_template(
        "contabilidad/book_crear.html",
        titulo=TITULO,
        form=formulario,
        edit=True,
    )


@contabilidad.route("/book/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nuevo_libro():
    """Formulario para crear un nuevo libro de contabilidad."""
    from cacao_accounting.contabilidad.forms import FormularioLibro
    from cacao_accounting.database import Book

    formulario = FormularioLibro()
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.moneda.choices = obtener_lista_monedas()
    TITULO = "Crear Nuevo Libro de Contabilidad - " + APPNAME
    if formulario.validate_on_submit():
        DATA = Book(
            code=formulario.id.data,
            name=formulario.nombre.data,
            entity=formulario.entidad.data,
            currency=formulario.moneda.data,
            status=formulario.estado.data,
        )
        database.session.add(DATA)
        database.session.commit()

        return redirect(url_for("contabilidad.libros"))
    return render_template(
        "contabilidad/book_crear.html",
        titulo=TITULO,
        form=formulario,
    )


@contabilidad.route("/journal/books")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def journal_books():
    """Lista libros activos disponibles para un comprobante contable."""
    from cacao_accounting.database import Book

    company = request.args.get("company", type=str)
    if not company:
        return jsonify({"results": []})

    books = (
        database.session.execute(
            database.select(Book)
            .where(Book.entity == company, or_(Book.status == "activo", Book.status.is_(None)))
            .order_by(Book.is_primary.desc(), Book.code)
        )
        .scalars()
        .all()
    )
    return jsonify(
        {
            "results": [
                {
                    "value": book.code,
                    "display_name": f"{book.code} - {book.name}",
                    "currency": book.currency,
                    "is_primary": bool(book.is_primary),
                }
                for book in books
            ]
        }
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Cuentas Contables


@contabilidad.route("/accounts", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def cuentas():
    """Catalogo de cuentas contables."""
    TITULO = "Catalogo de Cuentas Contables - " + APPNAME

    return render_template(
        "contabilidad/cuenta_lista.html",
        base_cuentas=obtener_catalogo_base(entidad_=request.args.get("entidad", None)),
        cuentas=obtener_catalogo(entidad_=request.args.get("entidad", None)),
        entidades=obtener_entidades(),
        entidad=obtener_entidad(ent=request.args.get("entidad")),
        titulo=TITULO,
    )


@contabilidad.route("/account/<entity>/<id_cta>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def cuenta(entity, id_cta):
    """Cuenta Contable."""
    from cacao_accounting.database import Accounts

    registro = database.session.execute(
        database.select(Accounts).filter(Accounts.code == id_cta, Accounts.entity == entity)
    ).first()

    return render_template(
        "contabilidad/cuenta.html",
        registro=registro[0],
        statusweb=STATUS,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Centros de Costos
@contabilidad.route("/costs_center", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def ccostos():
    """Catalogo de centros de costos."""
    TITULO = "Catalogo de Centros de Costos - " + APPNAME

    return render_template(
        "contabilidad/centro-costo_lista.html",
        base_centro_costos=obtener_catalogo_centros_costo_base(entidad_=request.args.get("entidad", None)),
        ccostos=obtener_centros_costos(entidad_=request.args.get("entidad", None)),
        entidades=obtener_entidades(),
        entidad=obtener_entidad(ent=request.args.get("entidad", None)),
        titulo=TITULO,
    )


@contabilidad.route("/costs_center/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nuevo_centro_costo():
    """Formulario para crear un nuevo centro de costos."""
    from cacao_accounting.contabilidad.forms import FormularioCentroCosto
    from cacao_accounting.database import CostCenter

    formulario = FormularioCentroCosto()
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.padre.choices = [("", "Sin padre")]
    TITULO = "Nuevo Centro de Costos - " + APPNAME

    if formulario.validate_on_submit():
        DATA = CostCenter(
            entity=formulario.entidad.data,
            code=request.form.get("id", None),
            name=request.form.get("nombre", None),
            active=bool(formulario.activo.data),
            enabled=bool(formulario.habilitado.data),
            default=bool(formulario.predeterminado.data),
            group=bool(formulario.grupo.data),
            parent=request.form.get("padre") or None,
            status="activo",
        )
        database.session.add(DATA)
        database.session.commit()
        return redirect(url_for("contabilidad.ccostos"))

    return render_template(
        "contabilidad/centro-costo_crear.html",
        titulo=TITULO,
        form=formulario,
    )


@contabilidad.route("/costs_center/<id_cc>/edit", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def editar_centro_costo(id_cc):
    """Editar un centro de costos existente."""
    from cacao_accounting.contabilidad.forms import FormularioCentroCosto
    from cacao_accounting.database import CostCenter

    registro = database.session.execute(database.select(CostCenter).filter_by(code=id_cc)).scalar_one_or_none()
    if registro is None:
        return redirect(url_for("contabilidad.ccostos"))

    formulario = FormularioCentroCosto(obj=registro)
    formulario.id.data = registro.code
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.padre.choices = [("", "Sin padre")]
    TITULO = "Editar Centro de Costos - " + APPNAME

    if formulario.validate_on_submit():
        registro.name = request.form.get("nombre", registro.name)
        registro.entity = request.form.get("entidad", registro.entity)
        registro.active = bool(formulario.activo.data)
        registro.enabled = bool(formulario.habilitado.data)
        registro.default = bool(formulario.predeterminado.data)
        registro.group = bool(formulario.grupo.data)
        registro.parent = request.form.get("padre") or None
        database.session.commit()
        return redirect(url_for("contabilidad.centro_costo", id_cc=registro.code))

    return render_template(
        "contabilidad/centro-costo_crear.html",
        titulo=TITULO,
        form=formulario,
        edit=True,
    )


@contabilidad.route("/costs_center/<id_cc>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def centro_costo(id_cc: str):
    """Detalle de un centro de costos."""
    from cacao_accounting.database import CostCenter

    registro = database.session.execute(database.select(CostCenter).filter_by(code=id_cc)).scalars().first()
    if registro is None:
        return redirect(url_for("contabilidad.ccostos"))

    return render_template(
        "contabilidad/centro-costo.html",
        registro=registro,
        statusweb=STATUS,
    )


@contabilidad.route("/costs_center/<id_cc>/delete")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def eliminar_centro_costo(id_cc):
    """Elimina un centro de costos."""
    from cacao_accounting.database import CostCenter

    registro = database.session.execute(database.select(CostCenter).filter_by(code=id_cc)).scalar_one_or_none()
    if registro:
        database.session.delete(registro)
        database.session.commit()
    return redirect(url_for("contabilidad.ccostos"))


# <------------------------------------------------------------------------------------------------------------------------> #
# Proyectos
@contabilidad.route("/project/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def proyectos():
    """Listado de proyectos."""
    from cacao_accounting.database import Project

    consulta = database.paginate(
        database.select(Project),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )

    return render_template(
        "contabilidad/proyecto_lista.html",
        consulta=consulta,
        titulo="Listado de Proyectos - " + APPNAME,
        statusweb=STATUS,
    )


@contabilidad.route("/project/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nuevo_proyecto():
    """Formulario para crear un nuevo proyecto."""
    from cacao_accounting.contabilidad.forms import FormularioProyecto
    from cacao_accounting.database import Project

    formulario = FormularioProyecto()
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    TITULO = "Nuevo Proyecto - " + APPNAME

    if formulario.validate_on_submit():
        DATA = Project(
            code=request.form.get("id", None),
            name=request.form.get("nombre", None),
            entity=request.form.get("entidad", None),
            start=formulario.inicio.data,
            end=formulario.fin.data,
            budget=float(formulario.presupuesto.data or 0),
            enabled=bool(formulario.habilitado.data),
            status="activo",
        )
        database.session.add(DATA)
        database.session.commit()
        return redirect(url_for("contabilidad.proyectos"))

    return render_template(
        "contabilidad/proyecto_crear.html",
        titulo=TITULO,
        form=formulario,
    )


@contabilidad.route("/project/<project_id>/edit", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def editar_proyecto(project_id):
    """Editar un proyecto existente."""
    from cacao_accounting.contabilidad.forms import FormularioProyecto
    from cacao_accounting.database import Project

    proyecto = database.session.execute(database.select(Project).filter_by(code=project_id)).scalar_one_or_none()
    if proyecto is None:
        return redirect(url_for("contabilidad.proyectos"))

    formulario = FormularioProyecto(obj=proyecto)
    formulario.id.data = proyecto.code
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    TITULO = "Editar Proyecto - " + APPNAME

    if formulario.validate_on_submit():
        proyecto.name = request.form.get("nombre", proyecto.name)
        proyecto.entity = request.form.get("entidad", proyecto.entity)
        proyecto.start = formulario.inicio.data
        proyecto.end = formulario.fin.data
        proyecto.budget = float(formulario.presupuesto.data or 0)
        proyecto.enabled = bool(formulario.habilitado.data)
        database.session.commit()
        return redirect(url_for("contabilidad.proyectos"))

    return render_template(
        "contabilidad/proyecto_crear.html",
        titulo=TITULO,
        form=formulario,
        edit=True,
    )


@contabilidad.route("/project/<project_id>/delete")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def eliminar_proyecto(project_id):
    """Elimina un proyecto."""
    from cacao_accounting.database import Project

    proyecto = database.session.execute(database.select(Project).filter_by(code=project_id)).scalar_one_or_none()
    if proyecto:
        database.session.delete(proyecto)
        database.session.commit()
    return redirect(url_for("contabilidad.proyectos"))


# <------------------------------------------------------------------------------------------------------------------------> #
# Proyectos
@contabilidad.route("/fiscal_year/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def fiscal_year_list():
    """Listado de años fiscales."""
    from cacao_accounting.database import FiscalYear

    CONSULTA = database.paginate(
        database.select(FiscalYear),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )

    return render_template(
        "contabilidad/fiscal_year_lista.html",
        titulo="Años Fiscales - " + APPNAME,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


@contabilidad.route("/fiscal_year/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def fiscal_year_new():
    """Crear un nuevo año fiscal."""
    from cacao_accounting.contabilidad.forms import FormularioFiscalYear
    from cacao_accounting.database import FiscalYear

    formulario = FormularioFiscalYear()
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    TITULO = "Nuevo Año Fiscal - " + APPNAME

    if formulario.validate_on_submit():
        DATA = FiscalYear(
            entity=request.form.get("entidad", None),
            name=request.form.get("id", None),
            year_start_date=formulario.inicio.data,
            year_end_date=formulario.fin.data,
            is_closed=bool(formulario.cerrado.data),
        )
        database.session.add(DATA)
        database.session.commit()
        return redirect(url_for("contabilidad.fiscal_year_list"))

    return render_template(
        "contabilidad/fiscal_year_crear.html",
        titulo=TITULO,
        form=formulario,
    )


@contabilidad.route("/fiscal_year/<fy_id>/edit", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def fiscal_year_edit(fy_id):
    """Editar un año fiscal."""
    from cacao_accounting.contabilidad.forms import FormularioFiscalYear
    from cacao_accounting.database import FiscalYear

    fiscal_year = database.session.execute(database.select(FiscalYear).filter_by(id=fy_id)).scalar_one_or_none()
    if fiscal_year is None:
        return redirect(url_for("contabilidad.fiscal_year_list"))

    formulario = FormularioFiscalYear(obj=fiscal_year)
    formulario.id.data = fiscal_year.name
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    TITULO = "Editar Año Fiscal - " + APPNAME

    if formulario.validate_on_submit():
        fiscal_year.entity = request.form.get("entidad", fiscal_year.entity)
        fiscal_year.name = request.form.get("id", fiscal_year.name)
        fiscal_year.year_start_date = formulario.inicio.data
        fiscal_year.year_end_date = formulario.fin.data
        fiscal_year.is_closed = bool(formulario.cerrado.data)
        database.session.commit()
        return redirect(url_for("contabilidad.fiscal_year_list"))

    return render_template(
        "contabilidad/fiscal_year_crear.html",
        titulo=TITULO,
        form=formulario,
        edit=True,
    )


@contabilidad.route("/fiscal_year/<fy_id>/delete")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def fiscal_year_delete(fy_id):
    """Elimina un año fiscal."""
    from cacao_accounting.database import FiscalYear

    fiscal_year = database.session.execute(database.select(FiscalYear).filter_by(id=fy_id)).scalar_one_or_none()
    if fiscal_year:
        database.session.delete(fiscal_year)
        database.session.commit()
    return redirect(url_for("contabilidad.fiscal_year_list"))


# <------------------------------------------------------------------------------------------------------------------------> #
# Años Fiscales
@contabilidad.route("/accounting_period/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def accounting_period_new():
    """Crear un nuevo período contable."""
    from cacao_accounting.contabilidad.forms import FormularioAccountingPeriod
    from cacao_accounting.database import AccountingPeriod, FiscalYear

    formulario = FormularioAccountingPeriod()
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    formulario.fiscal_year.choices = [("", "Seleccione un año fiscal")]
    fiscal_years = database.session.execute(database.select(FiscalYear)).scalars().all()
    formulario.fiscal_year.choices += [
        (fy.id, fy.name)
        for fy in fiscal_years
    ]
    TITULO = "Nuevo Período Contable - " + APPNAME

    if formulario.validate_on_submit():
        DATA = AccountingPeriod(
            entity=request.form.get("entidad", None),
            fiscal_year_id=request.form.get("fiscal_year", None),
            name=request.form.get("nombre", None),
            status=request.form.get("status", None),
            enabled=bool(formulario.habilitado.data),
            is_closed=bool(formulario.cerrado.data),
            start=formulario.inicio.data,
            end=formulario.fin.data,
        )
        database.session.add(DATA)
        database.session.commit()
        return redirect(url_for("contabilidad.periodo_contable"))

    return render_template(
        "contabilidad/periodo_crear.html",
        titulo=TITULO,
        form=formulario,
    )


@contabilidad.route("/accounting_period/<period_id>/edit", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def accounting_period_edit(period_id):
    """Editar un período contable."""
    from cacao_accounting.contabilidad.forms import FormularioAccountingPeriod
    from cacao_accounting.database import AccountingPeriod, FiscalYear

    period = database.session.execute(database.select(AccountingPeriod).filter_by(id=period_id)).scalar_one_or_none()
    if period is None:
        return redirect(url_for("contabilidad.periodo_contable"))

    formulario = FormularioAccountingPeriod(obj=period)
    formulario.id.data = period.name
    fiscal_years = database.session.execute(database.select(FiscalYear)).scalars().all()
    formulario.fiscal_year.choices = [
        (fy.id, fy.name)
        for fy in fiscal_years
    ]
    formulario.entidad.choices = obtener_lista_entidades_por_id_razonsocial()
    TITULO = "Editar Período Contable - " + APPNAME

    if formulario.validate_on_submit():
        period.entity = request.form.get("entidad", period.entity)
        period.fiscal_year_id = request.form.get("fiscal_year", period.fiscal_year_id)
        period.name = request.form.get("nombre", period.name)
        period.status = request.form.get("status", period.status)
        period.enabled = bool(formulario.habilitado.data)
        period.is_closed = bool(formulario.cerrado.data)
        period.start = formulario.inicio.data
        period.end = formulario.fin.data
        database.session.commit()
        return redirect(url_for("contabilidad.periodo_contable"))

    return render_template(
        "contabilidad/periodo_crear.html",
        titulo=TITULO,
        form=formulario,
        edit=True,
    )


@contabilidad.route("/accounting_period/<period_id>/delete")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def accounting_period_delete(period_id):
    """Elimina un período contable."""
    from cacao_accounting.database import AccountingPeriod

    period = database.session.execute(database.select(AccountingPeriod).filter_by(id=period_id)).scalar_one_or_none()
    if period:
        database.session.delete(period)
        database.session.commit()
    return redirect(url_for("contabilidad.periodo_contable"))


# <------------------------------------------------------------------------------------------------------------------------> #
# Tipos de Cambio
@contabilidad.route("/exchange")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def tasa_cambio():
    """Listado de tasas de cambio."""
    from cacao_accounting.database import ExchangeRate

    CONSULTA = database.paginate(
        database.select(ExchangeRate),  # noqa: E712
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )
    TITULO = "Listado de Tasas de Cambio - " + APPNAME

    return render_template(
        "contabilidad/tc_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Períodos Contables
@contabilidad.route("/accounting_period")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def periodo_contable():
    """Lista de periodos contables."""
    from cacao_accounting.database import AccountingPeriod

    CONSULTA = database.paginate(
        database.select(AccountingPeriod),  # noqa: E712
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )

    TITULO = "Listado de Períodos Contables - " + APPNAME

    return render_template(
        "contabilidad/periodo_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Comprobante contable
@contabilidad.route("/journal/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def listar_comprobantes():
    """Lista comprobantes contables manuales."""
    from cacao_accounting.contabilidad.journal_repository import list_journals

    return render_template(
        "contabilidad/journal_lista.html",
        consulta=list_journals(),
        titulo="Comprobantes Contables - " + APPNAME,
    )


@contabilidad.route("/journal/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nuevo_comprobante():
    """Nuevo comprobante contable."""
    from cacao_accounting.contabilidad.journal_service import (
        JournalValidationError,
        create_journal_draft,
        parse_journal_form,
    )
    from cacao_accounting.form_preferences import DEFAULT_VIEW_KEY, JOURNAL_FORM_KEY, get_form_preference

    if request.method == "POST":
        try:
            journal = create_journal_draft(parse_journal_form(request.form), user_id=str(current_user.id))
        except JournalValidationError as exc:
            flash(str(exc), "danger")
        else:
            flash("Comprobante contable guardado como borrador.", "success")
            return redirect(url_for("contabilidad.ver_comprobante", identifier=journal.id))

    TITULO = "Nuevo Comprobante Contable - " + APPNAME
    column_preferences = get_form_preference(str(current_user.id), JOURNAL_FORM_KEY, DEFAULT_VIEW_KEY)
    return render_template(
        "contabilidad/journal_nuevo.html",
        titulo=TITULO,
        column_preferences=column_preferences,
        form_key=JOURNAL_FORM_KEY,
        view_key=DEFAULT_VIEW_KEY,
        initial_journal=None,
        submit_url=url_for("contabilidad.nuevo_comprobante"),
    )


@contabilidad.route("/journal/<identifier>/submit", methods=["POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def contabilizar_comprobante(identifier: str):
    """Contabiliza un comprobante contable manual."""
    from cacao_accounting.contabilidad.journal_service import JournalValidationError, submit_journal

    try:
        submit_journal(identifier)
    except JournalValidationError as exc:
        flash(str(exc), "danger")
    else:
        flash("Comprobante contable contabilizado.", "success")
    return redirect(url_for("contabilidad.ver_comprobante", identifier=identifier))


@contabilidad.route("/journal/<identifier>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def ver_comprobante(identifier: str):
    """Ver comprobante contable."""
    from cacao_accounting.contabilidad.journal_repository import get_journal, list_journal_lines
    from cacao_accounting.contabilidad.journal_service import serialize_journal_for_form

    journal = get_journal(identifier)
    if journal is None:
        flash("El comprobante contable indicado no existe.", "warning")
        return redirect(url_for("contabilidad.conta"))
    return render_template(
        "contabilidad/journal.html",
        registro=journal,
        lineas=list_journal_lines(identifier),
        selected_books=(serialize_journal_for_form(journal).get("books") or []),
        titulo="Comprobante Contable - " + APPNAME,
    )


@contabilidad.route("/journal/edit/<identifier>", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def editar_comprobante(identifier: str):
    """Editar comprobante contable."""
    from cacao_accounting.contabilidad.journal_repository import get_journal
    from cacao_accounting.contabilidad.journal_service import (
        JournalValidationError,
        parse_journal_form,
        serialize_journal_for_form,
        update_journal_draft,
    )
    from cacao_accounting.form_preferences import DEFAULT_VIEW_KEY, JOURNAL_FORM_KEY, get_form_preference

    journal = get_journal(identifier)
    if journal is None:
        flash("El comprobante contable indicado no existe.", "warning")
        return redirect(url_for("contabilidad.listar_comprobantes"))
    if journal.status != "draft":
        flash("Solo se puede editar un comprobante en borrador.", "warning")
        return redirect(url_for("contabilidad.ver_comprobante", identifier=identifier))

    if request.method == "POST":
        try:
            journal = update_journal_draft(identifier, parse_journal_form(request.form), user_id=str(current_user.id))
        except JournalValidationError as exc:
            flash(str(exc), "danger")
        else:
            flash("Comprobante contable actualizado.", "success")
            return redirect(url_for("contabilidad.ver_comprobante", identifier=journal.id))

    TITULO = "Editar Comprobante Contable - " + APPNAME
    column_preferences = get_form_preference(str(current_user.id), JOURNAL_FORM_KEY, DEFAULT_VIEW_KEY)
    return render_template(
        "contabilidad/journal_nuevo.html",
        titulo=TITULO,
        column_preferences=column_preferences,
        form_key=JOURNAL_FORM_KEY,
        view_key=DEFAULT_VIEW_KEY,
        initial_journal=serialize_journal_for_form(journal),
        submit_url=url_for("contabilidad.editar_comprobante", identifier=identifier),
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# NamingSeries — CRUD robusto de series de numeracion

# NamingSeries — CRUD robusto de series de numeracion


@contabilidad.route("/naming-series/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def naming_series_list():
    """Lista de series de numeracion (NamingSeries)."""
    from cacao_accounting.database import NamingSeries, Sequence, SeriesExternalCounterMap, SeriesSequenceMap

    company_filter = request.args.get("company", type=str)

    if company_filter:
        query = database.select(NamingSeries).filter_by(company=company_filter)
    else:
        query = database.select(NamingSeries)

    consulta = database.paginate(
        query.order_by(NamingSeries.entity_type, NamingSeries.name),
        page=request.args.get("page", default=1, type=int),
        max_per_page=20,
        count=True,
    )

    from cacao_accounting.database import Entity

    entidades = database.session.execute(database.select(Entity)).scalars().all()
    sequence_rows = database.session.execute(
        database.select(SeriesSequenceMap.naming_series_id, Sequence)
        .join(Sequence, SeriesSequenceMap.sequence_id == Sequence.id)
        .order_by(SeriesSequenceMap.priority.asc())
    ).all()
    series_sequences = {series_id: sequence for series_id, sequence in sequence_rows}
    external_counter_counts = {
        series_id: count
        for series_id, count in database.session.execute(
            database.select(
                SeriesExternalCounterMap.naming_series_id, database.func.count(SeriesExternalCounterMap.id)
            ).group_by(SeriesExternalCounterMap.naming_series_id)
        ).all()
    }

    return render_template(
        "contabilidad/naming_series_lista.html",
        consulta=consulta,
        entidades=entidades,
        external_counter_counts=external_counter_counts,
        series_sequences=series_sequences,
        company_filter=company_filter,
        titulo="Series de Numeracion - " + APPNAME,
    )


@contabilidad.route("/naming-series/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def naming_series_new():
    """Nueva serie de numeracion."""
    from cacao_accounting.contabilidad.forms import FormularioNamingSeries
    from cacao_accounting.database import Entity, NamingSeries, Sequence, SeriesSequenceMap
    from cacao_accounting.document_identifiers import enforce_single_default_series

    form = FormularioNamingSeries()
    entidades = database.session.execute(database.select(Entity)).scalars().all()
    company_choices = [("", "— Global (sin compania) —")] + [(e.code, e.name) for e in entidades]
    form.company.choices = company_choices

    if form.validate_on_submit():
        company = form.company.data or None
        is_default = bool(form.is_default.data)

        if is_default:
            enforce_single_default_series(
                entity_type=form.entity_type.data,
                company=company,
                exclude_id=None,
            )

        secuencia = Sequence(
            name=f"{form.nombre.data} sequence",
            current_value=form.current_value.data or 0,
            increment=form.increment.data or 1,
            padding=form.padding.data or 5,
            reset_policy=form.reset_policy.data or "never",
        )
        database.session.add(secuencia)
        database.session.flush()

        nueva = NamingSeries(
            name=form.nombre.data,
            entity_type=form.entity_type.data,
            company=company,
            prefix_template=form.prefix_template.data,
            is_active=bool(form.is_active.data),
            is_default=is_default,
        )
        database.session.add(nueva)
        database.session.flush()
        database.session.add(
            SeriesSequenceMap(
                naming_series_id=nueva.id,
                sequence_id=secuencia.id,
                priority=0,
                condition=None,
            )
        )
        database.session.commit()
        return redirect(url_for("contabilidad.naming_series_list"))

    return render_template(
        "contabilidad/naming_series_nueva.html",
        form=form,
        titulo="Nueva Serie de Numeracion - " + APPNAME,
    )


@contabilidad.route("/naming-series/<series_id>/toggle-default", methods=["POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def naming_series_toggle_default(series_id: str):
    """Alterna el estado predeterminado de una serie de numeracion."""
    from cacao_accounting.database import NamingSeries
    from cacao_accounting.document_identifiers import enforce_single_default_series

    serie = database.session.get(NamingSeries, series_id)
    if not serie:
        return redirect(url_for("contabilidad.naming_series_list"))

    if not serie.is_default:
        enforce_single_default_series(
            entity_type=serie.entity_type,
            company=serie.company,
            exclude_id=serie.id,
        )
        serie.is_default = True
    else:
        serie.is_default = False

    database.session.commit()
    return redirect(url_for("contabilidad.naming_series_list"))


@contabilidad.route("/naming-series/<series_id>/edit", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def naming_series_edit(series_id: str):
    """Editar una serie de numeracion."""
    from cacao_accounting.contabilidad.forms import FormularioNamingSeries
    from cacao_accounting.database import Entity, NamingSeries, Sequence, SeriesSequenceMap
    from cacao_accounting.document_identifiers import enforce_single_default_series

    serie = database.session.get(NamingSeries, series_id)
    if serie is None:
        return redirect(url_for("contabilidad.naming_series_list"))

    form = FormularioNamingSeries(obj=serie)
    entidades = database.session.execute(database.select(Entity)).scalars().all()
    form.company.choices = [("", "— Global (sin compania) —")] + [(e.code, e.name) for e in entidades]
    form.company.data = serie.company or ""
    form.current_value.data = database.session.execute(
        database.select(Sequence.current_value)
        .join(SeriesSequenceMap, SeriesSequenceMap.sequence_id == Sequence.id)
        .filter(SeriesSequenceMap.naming_series_id == series_id)
    ).scalar_one_or_none() or 0

    if form.validate_on_submit():
        company = form.company.data or None
        if form.is_default.data:
            enforce_single_default_series(
                entity_type=form.entity_type.data,
                company=company,
                exclude_id=serie.id,
            )
        serie.name = form.nombre.data
        serie.entity_type = form.entity_type.data
        serie.company = company
        serie.prefix_template = form.prefix_template.data
        serie.is_active = bool(form.is_active.data)
        serie.is_default = bool(form.is_default.data)

        sequence_id = database.session.execute(
            database.select(SeriesSequenceMap.sequence_id)
            .filter_by(naming_series_id=serie.id)
        ).scalar_one_or_none()
        if sequence_id:
            sequence = database.session.get(Sequence, sequence_id)
            if sequence is not None:
                sequence.current_value = form.current_value.data or 0
                sequence.increment = form.increment.data or 1
                sequence.padding = form.padding.data or 5
                sequence.reset_policy = form.reset_policy.data or "never"
            else:
                from cacao_accounting.logs import log

                log.warning(f"Sequence record not found for sequence_id={sequence_id} on series={serie.id}")

        database.session.commit()
        return redirect(url_for("contabilidad.naming_series_list"))

    return render_template(
        "contabilidad/naming_series_nueva.html",
        form=form,
        titulo="Editar Serie de Numeracion - " + APPNAME,
        edit=True,
    )


@contabilidad.route("/naming-series/<series_id>/delete", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def naming_series_delete(series_id: str):
    """Eliminar una serie de numeracion si no ha sido utilizada."""
    from cacao_accounting.database import GeneratedIdentifierLog, NamingSeries, SeriesSequenceMap

    serie = database.session.get(NamingSeries, series_id)
    if serie is None:
        return redirect(url_for("contabilidad.naming_series_list"))

    has_history = (
        database.session.execute(
            database.select(GeneratedIdentifierLog)
            .join(SeriesSequenceMap, GeneratedIdentifierLog.sequence_id == SeriesSequenceMap.sequence_id)
            .filter(SeriesSequenceMap.naming_series_id == series_id)
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )
    if not has_history:
        database.session.delete(serie)
        database.session.commit()

    return redirect(url_for("contabilidad.naming_series_list"))


@contabilidad.route("/naming-series/<series_id>/toggle-active", methods=["POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def naming_series_toggle_active(series_id: str):
    """Activa o desactiva una serie de numeracion."""
    from cacao_accounting.database import GeneratedIdentifierLog, NamingSeries, SeriesSequenceMap

    serie = database.session.get(NamingSeries, series_id)
    if not serie:
        return redirect(url_for("contabilidad.naming_series_list"))

    if serie.is_active:
        # Comprobar si la serie ya genero identificadores (no se puede eliminar, solo desactivar)
        series_has_generated_identifiers = (
            database.session.execute(
                database.select(GeneratedIdentifierLog)
                .join(SeriesSequenceMap, GeneratedIdentifierLog.sequence_id == SeriesSequenceMap.sequence_id)
                .filter(SeriesSequenceMap.naming_series_id == series_id)
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )
        # Serie utilizada — solo marcarla inactiva, nunca eliminar aunque no haya generado documentos
        _ = series_has_generated_identifiers
        serie.is_active = False
        if serie.is_default:
            serie.is_default = False
    else:
        serie.is_active = True

    database.session.commit()
    return redirect(url_for("contabilidad.naming_series_list"))


# <------------------------------------------------------------------------------------------------------------------------> #
# ExternalCounter — CRUD de contadores externos con auditoria


@contabilidad.route("/external-counter/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def external_counter_list():
    """Lista de contadores externos."""
    from cacao_accounting.database import ExternalCounter

    company_filter = request.args.get("company", type=str)

    if company_filter:
        query = database.select(ExternalCounter).filter_by(company=company_filter)
    else:
        query = database.select(ExternalCounter)

    consulta = database.paginate(
        query.order_by(ExternalCounter.company, ExternalCounter.name),
        page=request.args.get("page", default=1, type=int),
        max_per_page=20,
        count=True,
    )

    from cacao_accounting.database import Entity

    entidades = database.session.execute(database.select(Entity)).scalars().all()

    return render_template(
        "contabilidad/external_counter_lista.html",
        consulta=consulta,
        entidades=entidades,
        company_filter=company_filter,
        titulo="Contadores Externos - " + APPNAME,
    )


@contabilidad.route("/external-counter/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def external_counter_new():
    """Nuevo contador externo."""
    from cacao_accounting.contabilidad.forms import FormularioExternalCounter
    from cacao_accounting.database import Entity, ExternalCounter, NamingSeries, SeriesExternalCounterMap

    form = FormularioExternalCounter()
    entidades = database.session.execute(database.select(Entity)).scalars().all()
    form.company.choices = [(e.code, e.name) for e in entidades]

    series_list = (
        database.session.execute(database.select(NamingSeries).filter_by(is_active=True).order_by(NamingSeries.name))
        .scalars()
        .all()
    )
    form.naming_series_id.choices = [("", "— Sin asociar —")] + [(s.id, f"{s.name} ({s.entity_type})") for s in series_list]

    if form.validate_on_submit():
        naming_series_id = form.naming_series_id.data or None
        nuevo = ExternalCounter(
            company=form.company.data,
            name=form.nombre.data,
            counter_type=form.counter_type.data,
            prefix=form.prefix.data or None,
            last_used=form.last_used.data or 0,
            padding=form.padding.data or 5,
            is_active=bool(form.is_active.data),
            description=form.description.data or None,
            naming_series_id=naming_series_id,
        )
        database.session.add(nuevo)
        database.session.flush()
        if naming_series_id:
            database.session.add(
                SeriesExternalCounterMap(
                    naming_series_id=naming_series_id,
                    external_counter_id=nuevo.id,
                    priority=0,
                    condition_json=None,
                )
            )
        database.session.commit()
        return redirect(url_for("contabilidad.external_counter_list"))

    return render_template(
        "contabilidad/external_counter_nuevo.html",
        form=form,
        titulo="Nuevo Contador Externo - " + APPNAME,
    )


@contabilidad.route("/external-counter/<counter_id>/adjust", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def external_counter_adjust(counter_id: str):
    """Ajusta el ultimo numero usado de un contador externo con auditoria obligatoria."""
    from flask_login import current_user

    from cacao_accounting.contabilidad.forms import FormularioAjusteContadorExterno
    from cacao_accounting.database import ExternalCounter
    from cacao_accounting.document_identifiers import IdentifierConfigurationError, adjust_external_counter

    counter = database.session.get(ExternalCounter, counter_id)
    if not counter:
        return redirect(url_for("contabilidad.external_counter_list"))

    form = FormularioAjusteContadorExterno()

    if form.validate_on_submit():
        try:
            adjust_external_counter(
                external_counter_id=counter_id,
                new_last_used=form.new_last_used.data,
                reason=form.reason.data,
                changed_by=current_user.id if current_user.is_authenticated else None,
            )
            database.session.commit()
            flash("Contador externo ajustado correctamente.", "success")
        except IdentifierConfigurationError as exc:
            from cacao_accounting.logs import log

            log.warning(f"Error al ajustar contador externo {counter_id}: {exc}")
            flash(str(exc), "danger")
        return redirect(url_for("contabilidad.external_counter_list"))

    return render_template(
        "contabilidad/external_counter_ajuste.html",
        form=form,
        counter=counter,
        titulo="Ajustar Contador Externo - " + APPNAME,
    )


@contabilidad.route("/external-counter/<counter_id>/audit-log")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def external_counter_audit_log(counter_id: str):
    """Bitacora de auditoria de un contador externo."""
    from cacao_accounting.database import ExternalCounter, ExternalCounterAuditLog

    counter = database.session.get(ExternalCounter, counter_id)
    if not counter:
        return redirect(url_for("contabilidad.external_counter_list"))

    registros = (
        database.session.execute(
            database.select(ExternalCounterAuditLog)
            .filter_by(external_counter_id=counter_id)
            .order_by(ExternalCounterAuditLog.changed_at.desc())
        )
        .scalars()
        .all()
    )

    return render_template(
        "contabilidad/external_counter_auditoria.html",
        counter=counter,
        registros=registros,
        titulo="Auditoria de Contador Externo - " + APPNAME,
    )
