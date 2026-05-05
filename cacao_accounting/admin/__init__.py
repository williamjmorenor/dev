# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Modulo administrativo."""

# ---------------------------------------------------------------------------------------
# Libreria estandar
# --------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
# Librerias de terceros
# ---------------------------------------------------------------------------------------
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import delete

# ---------------------------------------------------------------------------------------
# Recursos locales
# ---------------------------------------------------------------------------------------
from cacao_accounting.auth import helpers
from cacao_accounting.auth.forms import (
    RoleForm,
    UserCreateForm,
    UserEditForm,
    UserPasswordForm,
    UserRoleForm,
)
from cacao_accounting.decorators import modulo_activo
from cacao_accounting.database import Modules, Roles, RolesAccess, RolesUser, User, database
from cacao_accounting.modulos import listado_modulos, obtener_modulos_disponibles, sincronizar_modulos

admin = Blueprint("admin", __name__, template_folder="templates")


@admin.route("/admin")
@admin.route("/ajustes")
@admin.route("/administracion")
@admin.route("/configuracion")
@admin.route("/settings")
@login_required
@modulo_activo("admin")
def admin_():
    """Definición del modulo administrativo."""
    return render_template("admin.html")


@admin.route("/settings/modules", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def lista_modulos():
    """Administra los módulos instalados en el sistema."""
    sincronizar_modulos()

    if request.method == "POST":
        module_id = request.form.get("module_id")
        action = request.form.get("action")
        module = database.session.get(Modules, module_id) if module_id else None

        if module is None:
            flash("Módulo no encontrado.", "danger")
            return redirect(url_for("admin.lista_modulos"))

        if module.module == "admin":
            flash("El módulo administrativo no puede deshabilitarse.", "danger")
            return redirect(url_for("admin.lista_modulos"))

        if action == "toggle":
            module.enabled = not module.enabled
            database.session.commit()
            estado = "habilitado" if module.enabled else "deshabilitado"
            flash(f"Módulo {module.module} {estado} correctamente.", "success")
            return redirect(url_for("admin.lista_modulos"))

    datos = listado_modulos()
    modulos_disponibles = obtener_modulos_disponibles()
    modulos_por_tipo = []
    standard_names = {item["module"] for item in modulos_disponibles if item["type"] == "estandar"}

    for registro in datos["modulos"]:
        modulos_por_tipo.append(
            {
                "id": registro.id,
                "module": registro.module,
                "enabled": registro.enabled,
                "default": registro.default,
                "type": "Estándar" if registro.module in standard_names else "Plugin",
                "package": next(
                    (item["package"] for item in modulos_disponibles if item["module"] == registro.module),
                    None,
                ),
            }
        )

    return render_template(
        "admin/modulos.html",
        modulos=modulos_por_tipo,
    )


def _obtener_usuario(usuario_id: str) -> User | None:
    """Devuelve un usuario por su identificador."""
    return database.session.get(User, usuario_id)


def _obtener_roles_disponibles() -> list[Roles]:
    """Lista los roles disponibles en el sistema."""
    return database.session.execute(database.select(Roles).order_by(Roles.name)).scalars().all()


def _obtener_roles_por_usuario(usuario_id: str) -> list[Roles]:
    """Devuelve los roles asignados a un usuario."""
    return (
        database.session.execute(
            database.select(Roles)
            .join(RolesUser, Roles.id == RolesUser.role_id)
            .filter(RolesUser.user_id == usuario_id)
        )
        .scalars()
        .all()
    )


def _obtener_rol(role_id: str) -> Roles | None:
    """Devuelve un rol por su identificador."""
    return database.session.get(Roles, role_id)


def _obtener_permisos_por_rol(role_id: str) -> list[RolesAccess]:
    """Devuelve permisos asignados a un rol."""
    return (
        database.session.execute(database.select(RolesAccess).filter_by(rol_id=role_id)).scalars().all()
    )


def _obtener_modulos_disponibles() -> list[Modules]:
    """Devuelve los modulos registrados en el sistema."""
    return database.session.execute(database.select(Modules).order_by(Modules.module)).scalars().all()


@admin.route("/settings/users", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def lista_usuarios():
    """Administra los usuarios del sistema."""
    if request.method == "POST":
        user_id = request.form.get("user_id")
        action = request.form.get("action")
        usuario = _obtener_usuario(user_id) if user_id else None

        if usuario is None:
            flash("Usuario no encontrado.", "danger")
            return redirect(url_for("admin.lista_usuarios"))

        if action == "toggle":
            usuario.active = not bool(usuario.active)
            database.session.commit()
            estado = "habilitado" if usuario.active else "deshabilitado"
            flash(f"Usuario {usuario.user} {estado} correctamente.", "success")
            return redirect(url_for("admin.lista_usuarios"))

    usuarios = database.session.execute(database.select(User).order_by(User.user)).scalars().all()
    roles_por_usuario = {
        usuario.id: ", ".join([rol.name for rol in _obtener_roles_por_usuario(usuario.id)])
        for usuario in usuarios
    }

    return render_template(
        "admin/usuarios.html",
        usuarios=usuarios,
        roles_por_usuario=roles_por_usuario,
    )


@admin.route("/settings/users/new", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def crear_usuario():
    """Crea un nuevo usuario en el sistema."""
    form = UserCreateForm()
    if form.validate_on_submit():
        existen_usuario = database.session.execute(
            database.select(User).filter_by(user=form.usuario.data)
        ).scalar_one_or_none()
        existe_email = None
        if form.e_mail.data:
            existe_email = database.session.execute(
                database.select(User).filter_by(e_mail=form.e_mail.data)
            ).scalar_one_or_none()

        if existen_usuario is not None:
            form.usuario.errors.append("El nombre de usuario ya está en uso.")
        elif existe_email is not None:
            form.e_mail.errors.append("El correo electrónico ya está en uso.")
        elif not helpers.validar_clave_segura(form.password.data):
            form.password.errors.append(
                "Contraseña muy débil. Use al menos 8 caracteres, mayúsculas, minúsculas, números y símbolos."
            )
        else:
            nuevo_usuario = User(
                user=form.usuario.data,
                name=form.name.data or None,
                name2=form.name2.data or None,
                last_name=form.last_name.data or None,
                last_name2=form.last_name2.data or None,
                e_mail=form.e_mail.data or None,
                phone=form.phone.data or None,
                classification=form.classification.data or None,
                active=bool(form.active.data),
                password=helpers.proteger_passwd(form.password.data),
            )
            database.session.add(nuevo_usuario)
            database.session.commit()
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("admin.lista_usuarios"))

    return render_template(
        "admin/usuario_form.html",
        form=form,
        titulo="Crear Usuario",
        accion="Nuevo Usuario",
        tiene_clave=True,
    )


@admin.route("/settings/users/<string:user_id>/edit", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def editar_usuario(user_id: str):
    """Edita los datos básicos de un usuario."""
    usuario = _obtener_usuario(user_id)
    if usuario is None:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("admin.lista_usuarios"))

    form = UserEditForm(obj=usuario)
    if form.validate_on_submit():
        existe_usuario = database.session.execute(
            database.select(User)
            .filter(User.user == form.usuario.data)
            .filter(User.id != usuario.id)
        ).scalar_one_or_none()
        existe_email = None
        if form.e_mail.data:
            existe_email = database.session.execute(
                database.select(User)
                .filter(User.e_mail == form.e_mail.data)
                .filter(User.id != usuario.id)
            ).scalar_one_or_none()

        if existe_usuario is not None:
            form.usuario.errors.append("El nombre de usuario ya está en uso.")
        elif existe_email is not None:
            form.e_mail.errors.append("El correo electrónico ya está en uso.")
        else:
            usuario.user = form.usuario.data
            usuario.name = form.name.data or None
            usuario.name2 = form.name2.data or None
            usuario.last_name = form.last_name.data or None
            usuario.last_name2 = form.last_name2.data or None
            usuario.e_mail = form.e_mail.data or None
            usuario.phone = form.phone.data or None
            usuario.classification = form.classification.data or None
            usuario.active = bool(form.active.data)
            database.session.commit()
            flash("Usuario actualizado correctamente.", "success")
            return redirect(url_for("admin.lista_usuarios"))

    return render_template(
        "admin/usuario_form.html",
        form=form,
        titulo="Editar Usuario",
        accion="Actualizar Usuario",
        usuario=usuario,
        tiene_clave=False,
    )


@admin.route("/settings/users/<string:user_id>/roles", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def usuario_roles(user_id: str):
    """Asigna roles a un usuario."""
    usuario = _obtener_usuario(user_id)
    if usuario is None:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("admin.lista_usuarios"))

    roles = _obtener_roles_disponibles()
    form = UserRoleForm()
    form.roles.choices = [(rol.id, rol.name) for rol in roles]

    if request.method == "GET":
        form.roles.data = [rol.id for rol in _obtener_roles_por_usuario(usuario.id)]

    if form.validate_on_submit():
        seleccionado = [rol_id for rol_id in form.roles.data if rol_id]
        database.session.execute(delete(RolesUser).where(RolesUser.user_id == usuario.id))
        for rol_id in seleccionado:
            database.session.add(RolesUser(user_id=usuario.id, role_id=rol_id, active=True))
        database.session.commit()
        flash("Roles actualizados correctamente.", "success")
        return redirect(url_for("admin.lista_usuarios"))

    return render_template(
        "admin/usuario_roles.html",
        form=form,
        usuario=usuario,
    )


@admin.route("/settings/users/<string:user_id>/password", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def usuario_password(user_id: str):
    """Cambia la contraseña de un usuario."""
    usuario = _obtener_usuario(user_id)
    if usuario is None:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("admin.lista_usuarios"))

    form = UserPasswordForm()
    if form.validate_on_submit():
        if not helpers.validar_clave_segura(form.password.data):
            form.password.errors.append(
                "Contraseña muy débil. Use al menos 8 caracteres, mayúsculas, minúsculas, números y símbolos."
            )
        else:
            usuario.password = helpers.proteger_passwd(form.password.data)
            database.session.commit()
            flash("Contraseña actualizada correctamente.", "success")
            return redirect(url_for("admin.lista_usuarios"))

    return render_template(
        "admin/usuario_password.html",
        form=form,
        usuario=usuario,
    )


@admin.route("/settings/roles")
@login_required
@modulo_activo("admin")
def lista_roles():
    """Lista los roles disponibles en el sistema."""
    roles = database.session.execute(database.select(Roles).order_by(Roles.name)).scalars().all()
    return render_template("admin/roles.html", roles=roles)


@admin.route("/settings/roles/new", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def crear_rol():
    """Crea un nuevo rol."""
    form = RoleForm()
    if form.validate_on_submit():
        existe_rol = database.session.execute(database.select(Roles).filter_by(name=form.name.data)).scalar_one_or_none()
        if existe_rol is not None:
            form.name.errors.append("El nombre del rol ya está en uso.")
        else:
            nuevo_rol = Roles(name=form.name.data, note=form.note.data or "")
            database.session.add(nuevo_rol)
            database.session.commit()
            flash("Rol creado correctamente.", "success")
            return redirect(url_for("admin.lista_roles"))

    return render_template(
        "admin/rol_form.html",
        form=form,
        titulo="Crear Rol",
        accion="Guardar rol",
    )


@admin.route("/settings/roles/<string:role_id>/edit", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def editar_rol(role_id: str):
    """Edita un rol existente."""
    rol = _obtener_rol(role_id)
    if rol is None:
        flash("Rol no encontrado.", "danger")
        return redirect(url_for("admin.lista_roles"))

    form = RoleForm(obj=rol)
    if form.validate_on_submit():
        existe_rol = database.session.execute(
            database.select(Roles)
            .filter(Roles.name == form.name.data)
            .filter(Roles.id != rol.id)
        ).scalar_one_or_none()
        if existe_rol is not None:
            form.name.errors.append("El nombre del rol ya está en uso.")
        else:
            rol.name = form.name.data
            rol.note = form.note.data or ""
            database.session.commit()
            flash("Rol actualizado correctamente.", "success")
            return redirect(url_for("admin.lista_roles"))

    return render_template(
        "admin/rol_form.html",
        form=form,
        titulo="Editar Rol",
        accion="Actualizar rol",
        rol=rol,
    )


@admin.route("/settings/roles/<string:role_id>/permissions", methods=["GET", "POST"])
@login_required
@modulo_activo("admin")
def rol_permisos(role_id: str):
    """Asigna permisos a un rol por módulo."""
    rol = _obtener_rol(role_id)
    if rol is None:
        flash("Rol no encontrado.", "danger")
        return redirect(url_for("admin.lista_roles"))

    modulos = _obtener_modulos_disponibles()
    acciones = [
        ("access", "Acceso"),
        ("update", "Actualizar"),
        ("set_null", "Anular"),
        ("approve", "Autorizar"),
        ("bi", "BI"),
        ("close", "Cerrar"),
        ("setup", "Configurar"),
        ("view", "Consultar"),
        ("create", "Crear"),
        ("edit", "Editar"),
        ("delete", "Eliminar"),
        ("import_", "Importar"),
        ("report", "Reportes"),
        ("request", "Solicitar"),
        ("validate", "Validar"),
    ]
    permisos_existentes = {
        perm.module_id: {
            accion: getattr(perm, accion, False)
            for accion, _ in acciones
        }
        for perm in _obtener_permisos_por_rol(role_id)
    }

    if request.method == "POST":
        database.session.execute(database.delete(RolesAccess).where(RolesAccess.rol_id == role_id))
        for modulo in modulos:
            permiso_kwargs = {"rol_id": role_id, "module_id": modulo.id}
            for accion, _ in acciones:
                permiso_kwargs[accion] = request.form.get(f"perm_{modulo.id}_{accion}") == "on"
            if any(permiso_kwargs[action] for action, _ in acciones):
                database.session.add(RolesAccess(**permiso_kwargs))
        database.session.commit()
        flash("Permisos del rol actualizados correctamente.", "success")
        return redirect(url_for("admin.lista_roles"))

    return render_template(
        "admin/rol_permisos.html",
        rol=rol,
        modulos=modulos,
        permisos_existentes=permisos_existentes,
        acciones=acciones,
    )
