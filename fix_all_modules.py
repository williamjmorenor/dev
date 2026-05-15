import os
import re

def fix_module(filepath, module_name):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        content = f.read()

    # Import current_user if missing
    if "from flask_login import" not in content:
        content = content.replace("from flask import", "from flask import") # already there usually
        # Add it to the imports
        content = re.sub(r"from flask import (.*)", r"from flask import \1\nfrom flask_login import current_user", content)

    # Dictionary of function names to keys
    keys = {
        # Compras
        "compras_solicitud_compra_nuevo": "purchases.purchase_request",
        "compras_cotizacion_proveedor_nuevo": "purchases.supplier_quotation",
        "compras_orden_compra_nuevo": "purchases.purchase_order",
        "compras_solicitud_cotizacion_nuevo": "purchases.purchase_quotation",
        "compras_recepcion_nuevo": "purchases.purchase_receipt",
        "compras_factura_compra_nuevo": "purchases.purchase_invoice",
        # Ventas
        "ventas_pedido_venta_nuevo": "sales.sales_request",
        "ventas_cotizacion_nueva": "sales.sales_quotation",
        "ventas_orden_venta_nuevo": "sales.sales_order",
        "ventas_entrega_nuevo": "sales.delivery_note",
        "ventas_factura_venta_nuevo": "sales.sales_invoice",
        # Inventario
        "inventario_entrada_nuevo": "inventory.stock_entry",
        # Bancos
        "bancos_pago_nuevo": "banking.payment_entry",
    }

    for func, key in keys.items():
        if f"def {func}" in content:
            # Find the function block
            pattern = rf"def {func}\(.*?render_template\(.*?\)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                # We need to inject transaction_config before render_template and pass it
                block = match.group(0)
                if "transaction_config =" not in block:
                    insertion = f'    transaction_config = {{\n        "items": items_disponibles if "items_disponibles" in locals() else [],\n        "uoms": uoms_disponibles if "uoms_disponibles" in locals() else [],\n        "columns": get_column_preferences(current_user.id, "{key}"),\n    }}\n    return render_template('
                    block = re.sub(r"return render_template\(", insertion, block)
                    if "transaction_config=transaction_config" not in block:
                        block = block.replace(")", "        transaction_config=transaction_config,\n    )")
                content = content.replace(match.group(0), block)

    with open(filepath, 'w') as f:
        f.write(content)

fix_module('cacao_accounting/compras/__init__.py', 'purchases')
fix_module('cacao_accounting/ventas/__init__.py', 'sales')
fix_module('cacao_accounting/inventario/__init__.py', 'inventory')
fix_module('cacao_accounting/bancos/__init__.py', 'banking')
