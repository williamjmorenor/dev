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
from cacao_accounting.document_flow import DocumentFlowError, get_document_flow_items
from cacao_accounting.document_flow.service import get_source_items

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
    items = _source_items_or_abort("purchase_order", order_id)
    return jsonify({"order_id": order_id, "items": items})


@api.route("/api/sales/sales-order/<order_id>/items")
@login_required
def api_sales_order_items(order_id: str):
    """Devuelve las líneas de una orden de venta en formato JSON."""
    items = _source_items_or_abort("sales_order", order_id)
    return jsonify({"order_id": order_id, "items": items})


@api.route("/api/sales/sales-request/<request_id>/items")
@login_required
def api_sales_request_items(request_id: str):
    """Devuelve las líneas de un pedido de venta en formato JSON."""
    items = _source_items_or_abort("sales_request", request_id)
    return jsonify({"request_id": request_id, "items": items})


@api.route("/api/sales/sales-quotation/<quotation_id>/items")
@login_required
def api_sales_quotation_items(quotation_id: str):
    """Devuelve las líneas de una cotización de venta en formato JSON."""
    items = _source_items_or_abort("sales_quotation", quotation_id)
    return jsonify({"quotation_id": quotation_id, "items": items})


@api.route("/api/buying/purchase-receipt/<receipt_id>/items")
@login_required
def api_purchase_receipt_items(receipt_id: str):
    """Devuelve las líneas de una recepción de compra en formato JSON."""
    items = _source_items_or_abort("purchase_receipt", receipt_id)
    return jsonify({"receipt_id": receipt_id, "items": items})


@api.route("/api/sales/delivery-note/<note_id>/items")
@login_required
def api_delivery_note_items(note_id: str):
    """Devuelve las líneas de una nota de entrega en formato JSON."""
    items = _source_items_or_abort("delivery_note", note_id)
    return jsonify({"note_id": note_id, "items": items})


@api.route("/api/buying/purchase-invoice/<invoice_id>/items")
@login_required
def api_purchase_invoice_items(invoice_id: str):
    """Devuelve las líneas de una factura de compra en formato JSON."""
    items = _source_items_or_abort("purchase_invoice", invoice_id)
    return jsonify({"invoice_id": invoice_id, "items": items})


@api.route("/api/sales/sales-invoice/<invoice_id>/items")
@login_required
def api_sales_invoice_items(invoice_id: str):
    """Devuelve las líneas de una factura de venta en formato JSON."""
    items = _source_items_or_abort("sales_invoice", invoice_id)
    return jsonify({"invoice_id": invoice_id, "items": items})


@api.route("/api/document-flow/items")
@login_required
def api_document_flow_items():
    """Devuelve lineas pendientes para uno o mas documentos origen."""
    target_type = request.args.get("target_type", "")
    sources = request.args.getlist("source")
    if not target_type or not sources:
        abort(400)
    try:
        items = get_document_flow_items(target_type, sources)
    except DocumentFlowError as exc:
        abort(exc.status_code)
    return jsonify({"target_type": target_type, "items": items})


def _source_items_or_abort(source_type: str, source_id: str):
    """Helper para endpoints legacy de items por documento."""
    try:
        return get_source_items(source_type, source_id, request.args.get("target_type"))
    except DocumentFlowError as exc:
        abort(exc.status_code)
