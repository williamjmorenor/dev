# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Formularios web del modulo de bancos."""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired


class FormularioBanco(FlaskForm):
    """Formulario para crear o editar un banco."""

    name = StringField("Nombre", validators=[DataRequired()])
    swift_code = StringField("Código SWIFT")


class FormularioCuentaBancaria(FlaskForm):
    """Formulario para crear o editar una cuenta bancaria."""

    bank_id = SelectField("Banco", choices=[])
    company = SelectField("Compañía", choices=[])
    account_name = StringField("Nombre de Cuenta", validators=[DataRequired()])
    account_no = StringField("Número de Cuenta")
    iban = StringField("IBAN")
    currency = SelectField("Moneda", choices=[])


class FormularioPago(FlaskForm):
    """Formulario para crear una entrada de pago."""

    payment_type = SelectField(
        "Tipo de Pago",
        choices=[("receive", "Cobro"), ("pay", "Pago"), ("internal_transfer", "Transferencia Interna")],
    )
    company = SelectField("Compañía", choices=[])
    posting_date = StringField("Fecha")
    party_type = SelectField(
        "Tipo de Tercero", choices=[("customer", "Cliente"), ("supplier", "Proveedor")]
    )
    party_id = SelectField("Tercero", choices=[])
    paid_amount = StringField("Monto Pagado")
    remarks = TextAreaField("Observaciones")
