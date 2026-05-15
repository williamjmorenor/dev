import os
import re

def fix_file(filepath, module_key, funcs):
    with open(filepath, 'r') as f:
        content = f.read()

    # Move get_column_preferences to top
    if 'from cacao_accounting.form_preferences import get_column_preferences' not in content:
        content = "from cacao_accounting.form_preferences import get_column_preferences\n" + content

    # Ensure current_user
    if "from flask_login import current_user" not in content:
        content = re.sub(r"from flask_login import (.*)", r"from flask_login import current_user, \1", content)

    # For each function, we will find the GET return render_template and insert config + param
    # and for Invoice we will also fix the POST flow.

    for func, pref_key in funcs.items():
        # Match function definition to next function or end of file
        pattern = rf"(def {func}\(.*?\):)(.*?)(\n@|\ndef |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            header, body, tail = match.groups()

            # 1. If it's an invoice, fix the POST flow (totals, commit, redirect)
            if 'factura_compra_nuevo' in func or 'factura_venta_nuevo' in func:
                # Find _save_purchase_invoice_items call and the except
                invoice_save_pattern = r"(_total_qty, total = _save_(?:purchase|sales)_invoice_items\(factura\.id\))\s*\n\s*except"
                if re.search(invoice_save_pattern, body):
                    module_name = 'compras' if 'purchase' in invoice_save_pattern else 'ventas'
                    entity_lower = 'factura_compra' if 'purchase' in invoice_save_pattern else 'factura_venta'

                    replacement = r'''\1
            factura.total = total
            factura.base_total = total
            factura.grand_total = total
            factura.base_grand_total = total
            factura.outstanding_amount = total
            factura.base_outstanding_amount = total
            database.session.commit()
            flash("''' + ("Factura de compra" if module_name == 'compras' else "Factura de venta") + r''' creada correctamente.", "success")
            return redirect(url_for("''' + module_name + "." + module_name + "_" + entity_lower + r'''", invoice_id=factura.id))
        except'''
                    body = re.sub(invoice_save_pattern, replacement, body)

            # 2. Find the GET return render_template (the one NOT inside a try or if POST block usually)
            # Actually, let's target all return render_template calls in this function and add config

            def rt_replacer(m):
                call = m.group(0)
                if 'transaction_config=' in call: return call
                config = f'''    transaction_config = {{
        "items": items_disponibles if "items_disponibles" in locals() else [],
        "uoms": uoms_disponibles if "uoms_disponibles" in locals() else [],
        "columns": get_column_preferences(current_user.id, "{pref_key}"),
    }}
    '''
                if ')' in call:
                    return config + call.replace(')', ', transaction_config=transaction_config)')
                return config + call

            # To avoid affecting multi-line ones that don't match, we do it line by line inside body
            lines = body.split('\n')
            new_body_lines = []
            bj = 0
            while bj < len(lines):
                line = lines[bj]
                if 'return render_template(' in line and 'transaction_config=' not in line:
                    new_body_lines.append(f'    transaction_config = {{')
                    new_body_lines.append(f'        "items": items_disponibles if "items_disponibles" in locals() else [],')
                    new_body_lines.append(f'        "uoms": uoms_disponibles if "uoms_disponibles" in locals() else [],')
                    new_body_lines.append(f'        "columns": get_column_preferences(current_user.id, "{pref_key}"),')
                    new_body_lines.append(f'    }}')

                    if ')' in line:
                        new_body_lines.append(line.replace(')', ', transaction_config=transaction_config)'))
                    else:
                        new_body_lines.append(line)
                        bj += 1
                        while bj < len(lines) and ')' not in lines[bj]:
                            new_body_lines.append(lines[bj])
                            bj += 1
                        if bj < len(lines):
                            new_body_lines.append(lines[bj].replace(')', '        transaction_config=transaction_config,\n    )'))
                else:
                    new_body_lines.append(line)
                bj += 1

            body = "\n".join(new_body_lines)
            content = content[:match.start()] + header + body + tail + content[match.end():]

    with open(filepath, 'w') as f:
        f.write(content)

# Define functions for each module
compras_funcs = {
    "compras_solicitud_compra_nueva": "purchases.purchase_request",
    "compras_cotizacion_proveedor_nueva": "purchases.supplier_quotation",
    "compras_orden_compra_nuevo": "purchases.purchase_order",
    "compras_solicitud_cotizacion_nueva": "purchases.purchase_quotation",
    "compras_recepcion_nuevo": "purchases.purchase_receipt",
    "compras_factura_compra_nuevo": "purchases.purchase_invoice",
}
ventas_funcs = {
    "ventas_pedido_venta_nuevo": "sales.sales_request",
    "ventas_cotizacion_nueva": "sales.sales_quotation",
    "ventas_orden_venta_nuevo": "sales.sales_order",
    "ventas_entrega_nuevo": "sales.delivery_note",
    "ventas_factura_venta_nuevo": "sales.sales_invoice",
}
inventario_funcs = {
    "inventario_entrada_nuevo": "inventory.stock_entry",
}
bancos_funcs = {
    "bancos_pago_nuevo": "banking.payment_entry",
}

fix_file('cacao_accounting/compras/__init__.py', 'purchases', compras_funcs)
fix_file('cacao_accounting/ventas/__init__.py', 'sales', ventas_funcs)
fix_file('cacao_accounting/inventario/__init__.py', 'inventory', inventario_funcs)
fix_file('cacao_accounting/bancos/__init__.py', 'banking', bancos_funcs)
