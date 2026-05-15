import os
import re

def fix_bancos_imports():
    filepath = 'cacao_accounting/bancos/__init__.py'
    with open(filepath, 'r') as f:
        content = f.read()

    # Remove imports from the very top
    content = content.replace('from flask_login import current_user\nfrom cacao_accounting.form_preferences import get_column_preferences\n', '')

    # Insert them correctly
    if 'from flask_login import login_required' in content:
        content = content.replace('from flask_login import login_required', 'from flask_login import current_user, login_required')

    if 'from cacao_accounting.bancos.forms import FormularioPago' in content:
        content = content.replace('from cacao_accounting.bancos.forms import FormularioPago',
                                  'from cacao_accounting.form_preferences import get_column_preferences\nfrom cacao_accounting.bancos.forms import FormularioPago')

    # Update _payment_source_rows to include outstanding
    content = content.replace('"document": invoice,', '"document": invoice, "outstanding": _invoice_outstanding(invoice),')

    with open(filepath, 'w') as f:
        f.write(content)

def fix_compras_structure():
    filepath = 'cacao_accounting/compras/__init__.py'
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Move get_column_preferences import to top
    if 'from cacao_accounting.form_preferences import get_column_preferences' not in lines[0]:
        lines.insert(0, 'from cacao_accounting.form_preferences import get_column_preferences\n')

    # Remove redundant imports inside functions
    new_lines = []
    for line in lines:
        if 'from cacao_accounting.form_preferences import get_column_preferences' in line and line.strip().startswith('from'):
             if line == lines[0]:
                 new_lines.append(line)
             continue
        new_lines.append(line)

    content = "".join(new_lines)

    # Fix the redundant detail view function before supplier-quotation/list
    # The redundant one is around line 230
    # Actually, it was already handled by sed but let's be sure.

    # Fix compras_factura_compra_nuevo flow
    pattern = r'def compras_factura_compra_nuevo.*?\n    return render_template\('
    match = re.search(pattern, content, re.DOTALL)
    if match:
        # I'll just rewrite the problematic function block
        pass

    with open(filepath, 'w') as f:
        f.write(content)

# Safe rewrite of compras_factura_compra_nuevo and ventas_factura_venta_nuevo
def fix_invoice_new(filepath, module_name, entity_type, key):
    with open(filepath, 'r') as f:
        content = f.read()

    # This is complex to do with regex perfectly, I'll try to find the start and end of the function
    func_name = f"{module_name}_factura_venta_nuevo" if module_name == 'ventas' else f"{module_name}_factura_compra_nuevo"

    # I will look for the whole function and replace it.
    # Since I know the structure, I will target the end of the POST block.

    if module_name == 'compras':
        old_block = r'_total_qty, total = _save_purchase_invoice_items\(factura.id\)\n        except \(DocumentFlowError, IdentifierConfigurationError\) as exc:'
        new_block = r'''_total_qty, total = _save_purchase_invoice_items(factura.id)
            factura.total = total
            factura.base_total = total
            factura.grand_total = total
            factura.base_grand_total = total
            factura.outstanding_amount = total
            factura.base_outstanding_amount = total
            database.session.commit()
            flash("Factura de compra creada correctamente.", "success")
            return redirect(url_for("compras.compras_factura_compra", invoice_id=factura.id))
        except (DocumentFlowError, IdentifierConfigurationError) as exc:'''
        content = re.sub(old_block, new_block, content)
    else:
        old_block = r'_total_qty, total = _save_sales_invoice_items\(factura.id\)\n        except \(DocumentFlowError, IdentifierConfigurationError\) as exc:'
        new_block = r'''_total_qty, total = _save_sales_invoice_items(factura.id)
            factura.total = total
            factura.base_total = total
            factura.grand_total = total
            factura.base_grand_total = total
            factura.outstanding_amount = total
            factura.base_outstanding_amount = total
            database.session.commit()
            flash("Factura de venta creada correctamente.", "success")
            return redirect(url_for("ventas.ventas_factura_venta", invoice_id=factura.id))
        except (DocumentFlowError, IdentifierConfigurationError) as exc:'''
        content = re.sub(old_block, new_block, content)

    # Cleanup the double return render_template that might be there
    # It usually looks like:
    #    return render_template(...)
    #    factura.total = total ...

    # After the replacement above, we might have:
    #    return redirect(...)
    #    except ...:
    #       ...
    #    transaction_config = ...
    #    return render_template(...)
    #    factura.total = total ...  <-- this tail needs to go

    pattern = r'(return render_template\(.*?\))\s*\n\s*factura\.total = total'
    content = re.sub(pattern, r'\1', content, flags=re.DOTALL)

    with open(filepath, 'w') as f:
        f.write(content)

fix_bancos_imports()
fix_compras_structure()
fix_invoice_new('cacao_accounting/compras/__init__.py', 'compras', 'PurchaseInvoice', 'purchases.purchase_invoice')
fix_invoice_new('cacao_accounting/ventas/__init__.py', 'ventas', 'SalesInvoice', 'sales.sales_invoice')
