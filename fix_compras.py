import sys

def process_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'def ' in line and '_nuevo():' in line:
            # We found a nuevo function
            func_name = line.split('def ')[1].split('(')[0]
            new_lines.append(line)
            i += 1
            # Look for the end of the function or render_template
            while i < len(lines) and 'def ' not in lines[i]:
                if 'return render_template(' in lines[i]:
                    # Insert transaction_config before render_template if not already there
                    # But we need columns based on function name
                    key_map = {
                        "compras_solicitud_compra_nuevo": "purchases.purchase_request",
                        "compras_cotizacion_proveedor_nuevo": "purchases.supplier_quotation",
                        "compras_orden_compra_nuevo": "purchases.purchase_order",
                        "compras_solicitud_cotizacion_nuevo": "purchases.purchase_quotation",
                        "compras_recepcion_nuevo": "purchases.purchase_receipt",
                        "compras_factura_compra_nuevo": "purchases.purchase_invoice",
                    }
                    key = key_map.get(func_name)
                    if key:
                        new_lines.append(f'    transaction_config = {{\n')
                        new_lines.append(f'        "items": items_disponibles,\n')
                        new_lines.append(f'        "uoms": uoms_disponibles,\n')
                        new_lines.append(f'        "columns": get_column_preferences(current_user.id, "{key}"),\n')
                        new_lines.append(f'    }}\n')

                    # Now update render_template call
                    # We need to find the closing parenthesis of render_template
                    rt_call = lines[i]
                    j = i + 1
                    while ')' not in rt_call and j < len(lines):
                        rt_call += lines[j]
                        j += 1

                    if 'transaction_config=transaction_config' not in rt_call:
                        rt_call = rt_call.replace(')', '        transaction_config=transaction_config,\n    )')

                    new_lines.append(rt_call)
                    i = j
                    break
                new_lines.append(lines[i])
                i += 1
            continue
        new_lines.append(line)
        i += 1

    with open(filepath, 'w') as f:
        f.writelines(new_lines)

process_file('cacao_accounting/compras/__init__.py')
