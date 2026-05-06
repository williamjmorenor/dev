# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo de Contabilidad."""

# ---------------------------------------------------------------------------------------
# Libreria estandar
# --------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
# Librerias de terceros
# ---------------------------------------------------------------------------------------
from flask import Blueprint, flash, redirect, render_template, request
from flask.helpers import url_for
from flask_login import login_required

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
    from cacao_accounting.database import Entity

    formulario = FormularioEntidad()
    formulario.moneda.choices = obtener_lista_monedas()

    TITULO = "Crear Nueva Entidad - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        ENTIDAD = Entity(
            code=request.form.get("id", None),
            company_name=request.form.get("razon_social", None),
            name=request.form.get("nombre_comercial", None),
            tax_id=request.form.get("id_fiscal", None),
            currency=request.form.get("moneda", None),
            entity_type=request.form.get("tipo_entidad", None),
            e_mail=request.form.get("correo_electronico", None),
            web=request.form.get("web", None),
            phone1=request.form.get("telefono1", None),
            phone2=request.form.get("telefono2", None),
            fax=request.form.get("fax", None),
            status="activo",
            enabled=True,
            default=False,
        )

        database.session.add(ENTIDAD)
        database.session.flush()

        from cacao_accounting.compras.purchase_reconciliation_service import seed_matching_config_for_company

        seed_matching_config_for_company(ENTIDAD.code)
        database.session.commit()

        return LISTA_ENTIDADES

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
    TITULO = "Crear Nuevo Libro de Contabilidad - " + APPNAME
    if formulario.validate_on_submit() or request.method == "POST":
        DATA = Book(
            code=request.form.get("id", None),
            name=request.form.get("nombre", None),
            entity=request.form.get("entidad", None),
            status="activo",
        )
        database.session.add(DATA)
        database.session.commit()

        return redirect(url_for("contabilidad.libros"))
    return render_template(
        "contabilidad/book_crear.html",
        titulo=TITULO,
        form=formulario,
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


@contabilidad.route("/costs_center/<id_cc>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def centro_costo(id_cc):
    """Centro de Costos."""
    from cacao_accounting.database import CostCenter

    registro = database.session.execute(database.select(CostCenter).filter_by(code=id_cc)).first()

    return render_template(
        "contabilidad/centro-costo.html",
        registro=registro[0],
        statusweb=STATUS,
    )


# <------------------------------------------------------------------------------------------------------------------------> #
# Proyectos
@contabilidad.route("/project/list")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def proyectos():
    """Listado de proyectos."""
    from cacao_accounting.database import Project

    CONSULTA = database.paginate(
        database.select(Project),
        page=request.args.get("page", default=1, type=int),
        max_per_page=10,
        count=True,
    )

    TITULO = "Listados de Proyectos - " + APPNAME

    return render_template(
        "contabilidad/proyecto_lista.html",
        titulo=TITULO,
        consulta=CONSULTA,
        statusweb=STATUS,
    )


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
@contabilidad.route("/journal/new", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def nuevo_comprobante():
    """Nuevo comprobante contable."""
    return redirect(url_for("contabilidad.gl.gl_new"))


@contabilidad.route("/journal/<identifier>")
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def ver_comprobante(identifier: str):
    """Ver comprobante contable."""
    return redirect(url_for("contabilidad.gl.gl_list"))


@contabilidad.route("/journal/edit/<identifier>", methods=["GET", "POST"])
@login_required
@modulo_activo("accounting")
@verifica_acceso("accounting")
def editar_comprobante(identifier: str):
    """Editar comprobante contable."""
    return redirect(url_for("contabilidad.gl.gl_list"))


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
