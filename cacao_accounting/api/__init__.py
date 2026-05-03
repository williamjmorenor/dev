# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""End point para peticiones realizadas vía api."""

# ---------------------------------------------------------------------------------------
# Libreria estandar
# --------------------------------------------------------------------------------------
from functools import wraps

# ---------------------------------------------------------------------------------------
# Librerias de terceros
# ---------------------------------------------------------------------------------------
from flask import Blueprint, abort, current_app, jsonify, request
from flask_login import current_user, login_required
from jwt import decode

# ---------------------------------------------------------------------------------------
# Recursos locales
# ---------------------------------------------------------------------------------------
from cacao_accounting.database import (
    DeliveryNote,
    DeliveryNoteItem,
    PurchaseOrder,
    PurchaseOrderItem,
    SalesOrder,
    SalesOrderItem,
    database,
)

api = Blueprint("api", __name__, template_folder="templates")


def token_requerido(f):  # pragma: no cover
    """Decorador para proteger el acceso a la API vía tokens."""

    @wraps(f)
    def wrapper(*args, **kwds):
        """Protege la API con un token."""
        token = None

        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]

        if not token:
            return {
                "message": "Authentication Token is missing!",
                "data": None,
                "error": "Unauthorized",
            }, 401

        try:
            data = decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            assert data is not None  # nosec

            if not current_user:
                return {
                    "message": "Invalid Authentication token!",
                    "data": None,
                    "error": "Unauthorized",
                }, 401

            if not current_user.is_authenticated:
                abort(403)

        except Exception as e:
            return {
                "message": "Something went wrong",
                "data": None,
                "error": str(e),
            }, 500

        return f(*args, **kwds)

    return wrapper


@api.route("/api/test")
@token_requerido
def test_appy():
    """Vista de prueba para probar el API."""
    responde_data = {
        "Response": "Holis",
    }

    return jsonify(responde_data)


@api.route("/api/buying/purchase-order/<order_id>/items")
@login_required
def api_purchase_order_items(order_id: str):
    """Devuelve las líneas de una orden de compra en formato JSON."""
    orden = database.session.get(PurchaseOrder, order_id)
    if not orden:
        abort(404)
    lineas = database.session.execute(
        database.select(PurchaseOrderItem).filter_by(purchase_order_id=order_id)
    ).all()
    items = [
        {
            "item_code": li[0].item_code,
            "item_name": li[0].item_name or "",
            "qty": float(li[0].qty) if li[0].qty is not None else 1,
            "uom": li[0].uom or "",
            "rate": float(li[0].rate) if li[0].rate is not None else 0,
            "amount": float(li[0].amount) if li[0].amount is not None else 0,
        }
        for li in lineas
    ]
    return jsonify({"order_id": order_id, "items": items})


@api.route("/api/sales/sales-order/<order_id>/items")
@login_required
def api_sales_order_items(order_id: str):
    """Devuelve las líneas de una orden de venta en formato JSON."""
    orden = database.session.get(SalesOrder, order_id)
    if not orden:
        abort(404)
    lineas = database.session.execute(
        database.select(SalesOrderItem).filter_by(sales_order_id=order_id)
    ).all()
    items = [
        {
            "item_code": li[0].item_code,
            "item_name": li[0].item_name or "",
            "qty": float(li[0].qty) if li[0].qty is not None else 1,
            "uom": li[0].uom or "",
            "rate": float(li[0].rate) if li[0].rate is not None else 0,
            "amount": float(li[0].amount) if li[0].amount is not None else 0,
        }
        for li in lineas
    ]
    return jsonify({"order_id": order_id, "items": items})


@api.route("/api/buying/purchase-receipt/<receipt_id>/items")
@login_required
def api_purchase_receipt_items(receipt_id: str):
    """Devuelve las líneas de una recepción de compra en formato JSON."""
    from cacao_accounting.database import PurchaseReceipt, PurchaseReceiptItem

    recepcion = database.session.get(PurchaseReceipt, receipt_id)
    if not recepcion:
        abort(404)
    lineas = database.session.execute(
        database.select(PurchaseReceiptItem).filter_by(purchase_receipt_id=receipt_id)
    ).all()
    items = [
        {
            "item_code": li[0].item_code,
            "item_name": li[0].item_name or "",
            "qty": float(li[0].qty) if li[0].qty is not None else 1,
            "uom": li[0].uom or "",
            "rate": float(li[0].rate) if li[0].rate is not None else 0,
            "amount": float(li[0].amount) if li[0].amount is not None else 0,
        }
        for li in lineas
    ]
    return jsonify({"receipt_id": receipt_id, "items": items})


@api.route("/api/sales/delivery-note/<note_id>/items")
@login_required
def api_delivery_note_items(note_id: str):
    """Devuelve las líneas de una nota de entrega en formato JSON."""
    entrega = database.session.get(DeliveryNote, note_id)
    if not entrega:
        abort(404)
    lineas = database.session.execute(
        database.select(DeliveryNoteItem).filter_by(delivery_note_id=note_id)
    ).all()
    items = [
        {
            "item_code": li[0].item_code,
            "item_name": li[0].item_name or "",
            "qty": float(li[0].qty) if li[0].qty is not None else 1,
            "uom": li[0].uom or "",
            "rate": float(li[0].rate) if li[0].rate is not None else 0,
            "amount": float(li[0].amount) if li[0].amount is not None else 0,
        }
        for li in lineas
    ]
    return jsonify({"note_id": note_id, "items": items})
