import os
import re

def add_imports(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Imports
    if "from flask_login import" in content and "current_user" not in content:
        content = re.sub(r"from flask_login import (.*)", r"from flask_login import current_user, \1", content)

    if "from cacao_accounting.form_preferences import get_column_preferences" not in content:
        # Find any other cacao_accounting import and prepend
        match = re.search(r"from cacao_accounting\.(.*) import", content)
        if match:
            content = content[:match.start()] + "from cacao_accounting.form_preferences import get_column_preferences\n" + content[match.start():]
        else:
            content = "from cacao_accounting.form_preferences import get_column_preferences\n" + content

    with open(filepath, 'w') as f:
        f.write(content)

def apply_config(filepath, module_key_prefix):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match def func_name_nuevo(): or similar
        match = re.search(r"def (\w+_(?:nuevo|nueva|pago_nuevo|entrada_nuevo))\((.*?)\):", line)
        if match:
            func_name = match.group(1)
            params = match.group(2)

            # Map function name to preference key
            key_map = {
                "compras_solicitud_compra_nueva": "purchases.purchase_request",
                "compras_cotizacion_proveedor_nueva": "purchases.supplier_quotation",
                "compras_orden_compra_nuevo": "purchases.purchase_order",
                "compras_solicitud_cotizacion_nueva": "purchases.purchase_quotation",
                "compras_recepcion_nuevo": "purchases.purchase_receipt",
                "compras_factura_compra_nuevo": "purchases.purchase_invoice",
                "ventas_pedido_venta_nuevo": "sales.sales_request",
                "ventas_cotizacion_nueva": "sales.sales_quotation",
                "ventas_orden_venta_nuevo": "sales.sales_order",
                "ventas_entrega_nuevo": "sales.delivery_note",
                "ventas_factura_venta_nuevo": "sales.sales_invoice",
                "inventario_entrada_nuevo": "inventory.stock_entry",
                "bancos_pago_nuevo": "banking.payment_entry",
            }

            key = key_map.get(func_name)
            if key:
                new_lines.append(line)
                i += 1

                func_body = []
                while i < len(lines) and not lines[i].startswith('def ') and not lines[i].startswith('@'):
                    func_body.append(lines[i])
                    i += 1

                # Find all return render_template calls in this function
                body_str = "".join(func_body)

                # Insert transaction_config BEFORE each render_template if not already present in body
                if "transaction_config =" not in body_str:
                    # We can't easily insert before each if there are many.
                    # Usually there is only one at the end for GET.
                    pass

                # Let's do a simpler approach: insert config at the start of the function and pass it to all render_template
                config_lines = [
                    '    transaction_config = {\n',
                    '        "items": items_disponibles if "items_disponibles" in locals() else [],\n',
                    '        "uoms": uoms_disponibles if "uoms_disponibles" in locals() else [],\n',
                    f'        "columns": get_column_preferences(current_user.id, "{key}"),\n',
                    '    }\n'
                ]

                # Actually, items_disponibles and others are defined LATER in the function.
                # So we must insert it just before render_template.

                # Find occurrences of render_template in body_str
                # and replace them with config + call

                def replacer(m):
                    call = m.group(0)
                    config = f'''    transaction_config = {{
        "items": items_disponibles if "items_disponibles" in locals() else [],
        "uoms": uoms_disponibles if "uoms_disponibles" in locals() else [],
        "columns": get_column_preferences(current_user.id, "{key}"),
    }}
    '''
                    if 'transaction_config=' not in call:
                        if ')' in call:
                            return config + call.replace(')', ', transaction_config=transaction_config)')
                        else:
                             # Multi-line: this is harder. Let's assume we can find the closing )
                             return config + call
                    return call

                # We need to handle multi-line render_template
                # This regex is still a bit risky but better.
                body_str = re.sub(r"return render_template\(.*?\)", replacer, body_str, flags=re.DOTALL)

                # Handle multi-line render_template calls that don't match above
                # Search for return render_template( and find its matching )

                new_body = []
                body_lines = body_str.split('\n')
                bj = 0
                while bj < len(body_lines):
                    bline = body_lines[bj]
                    if 'return render_template(' in bline and 'transaction_config=' not in bline:
                        # Insert config
                        new_body.append(f'    transaction_config = {{')
                        new_body.append(f'        "items": items_disponibles if "items_disponibles" in locals() else [],')
                        new_body.append(f'        "uoms": uoms_disponibles if "uoms_disponibles" in locals() else [],')
                        new_body.append(f'        "columns": get_column_preferences(current_user.id, "{key}"),')
                        new_body.append(f'    }}')

                        # Find closing )
                        curr_line = bline
                        if ')' not in curr_line:
                            while bj + 1 < len(body_lines) and ')' not in curr_line:
                                new_body.append(curr_line)
                                bj += 1
                                curr_line = body_lines[bj]

                        new_body.append(curr_line.replace(')', '        transaction_config=transaction_config,\n    )'))
                        bj += 1
                    else:
                        new_body.append(bline)
                        bj += 1

                new_lines.append("\n".join(new_body))
                continue

        new_lines.append(line)
        i += 1

    with open(filepath, 'w') as f:
        f.write("".join(new_lines))

for fp in ['cacao_accounting/bancos/__init__.py', 'cacao_accounting/compras/__init__.py',
           'cacao_accounting/inventario/__init__.py', 'cacao_accounting/ventas/__init__.py']:
    add_imports(fp)
    apply_config(fp, '')
