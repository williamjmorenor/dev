import os
import re

def fix_configs(filepath, module_name):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        content = f.read()

    # Dictionary of function names to keys
    keys = {
        # Compras
        "compras_solicitud_compra_nueva": "purchases.purchase_request",
        "compras_cotizacion_proveedor_nueva": "purchases.supplier_quotation",
        "compras_orden_compra_nuevo": "purchases.purchase_order",
        "compras_solicitud_cotizacion_nueva": "purchases.purchase_quotation",
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
        if f"def {func}" not in content:
            continue

        # If it already has transaction_config, skip it
        # Note: I might have partial implementations. Let's be careful.

        # Check if function has return render_template and NO transaction_config defined just before it
        # Actually, let's just use a script to ensure it's there correctly.
        pass

    # I'll rewrite the safer_fix logic to be more robust
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        matched_func = None
        for func in keys:
            if f"def {func}" in line:
                matched_func = func
                break

        if matched_func:
            key = keys[matched_func]
            new_lines.append(line)
            i += 1
            # Read until the LAST return render_template in the function
            # Functions usually end with return render_template for GET requests

            func_lines = []
            while i < len(lines) and not lines[i].startswith('def ') and not lines[i].startswith('@'):
                func_lines.append(lines[i])
                i += 1

            # Now find the last return render_template in func_lines
            rt_index = -1
            for j in range(len(func_lines)-1, -1, -1):
                if 'return render_template(' in func_lines[j]:
                    rt_index = j
                    break

            if rt_index != -1:
                # Insert config if missing
                has_config = any('transaction_config =' in fl for fl in func_lines)
                if not has_config:
                    config_block = [
                        '    transaction_config = {',
                        '        "items": items_disponibles if "items_disponibles" in locals() else [],',
                        '        "uoms": uoms_disponibles if "uoms_disponibles" in locals() else [],',
                        f'        "columns": get_column_preferences(current_user.id, "{key}"),',
                        '    }'
                    ]
                    func_lines.insert(rt_index, "\n".join(config_block))
                    rt_index += 1 # shift because of insertion

                # Ensure passed to render_template
                if 'transaction_config=transaction_config' not in func_lines[rt_index]:
                    if ')' in func_lines[rt_index]:
                        func_lines[rt_index] = func_lines[rt_index].replace(')', ', transaction_config=transaction_config)')
                    else:
                        # Find the closing parenthesis
                        for k in range(rt_index + 1, len(func_lines)):
                            if ')' in func_lines[k]:
                                func_lines[k] = func_lines[k].replace(')', '    transaction_config=transaction_config,\n    )')
                                break

            new_lines.extend(func_lines)
            continue

        new_lines.append(line)
        i += 1

    with open(filepath, 'w') as f:
        f.write('\n'.join(new_lines))

fix_configs('cacao_accounting/compras/__init__.py', 'purchases')
fix_configs('cacao_accounting/ventas/__init__.py', 'sales')
fix_configs('cacao_accounting/inventario/__init__.py', 'inventory')
fix_configs('cacao_accounting/bancos/__init__.py', 'cash')
