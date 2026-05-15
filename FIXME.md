# cacao_accounting/form_preferences.py
def get_column_preferences(user_id: str | None, form_key: str, view_key: str = DEFAULT_VIEW_KEY) -> list[dict[str, Any]]:
    """Obtiene solo la lista de columnas de la preferencia del usuario."""
    pref = get_form_preference(user_id, form_key, view_key)  # type: ignore[arg-type]
    return pref.get("columns") or []

Provide default columns for transaction grids

Every new transaction form wired to transaction_grid passes columns=get_column_preferences(...), but for any non-journal form without a saved UserFormPreference, default_form_preference returns columns: []; then visibleColumns is empty and the grid renders no item/qty/rate inputs, so new users can only create zero-line/zero-total documents. Return a shared default transaction column set for these form keys, or make the grid fall back when preferences are empty.

# cacao_accounting/compras/templates/compras/orden_compra_nuevo.html
Comment on lines +30 to +31
  {% set source_api_url = "/api/document-flow/pending-lines?source_type=purchase_request&target_type=purchase_order&source_id=" ~ from_request_id if from_request_id else None %}
  {{ tf_macros.transaction_grid(items_disponibles, uoms_disponibles, source_api_url=source_api_url, source_label="Solicitud de Compra") }}

Wire purchase-request context into purchase orders

The purchase request detail links here with ?from_request=<id>, but compras_orden_compra_nuevo never reads or passes from_request_id/solicitud_origen, so this expression is always false/undefined and the source API plus hidden source field are omitted. In that context, users cannot pull pending request lines into a purchase order, breaking the new “Crear Orden de Compra” flow from purchase requests.

# cacao_accounting/static/js/transaction-form.js
Comment on lines +119 to +122
                qty: i.pending_qty || i.qty,
                uom: i.uom,
                rate: i.rate,
                amount: (i.pending_qty || i.qty) * i.rate,

Honor edited quantities when applying source lines

In the “Actualizar Elementos” modal, the editable input is bound to si.qty, but this code imports i.pending_qty whenever it is nonzero. If a source line has 10 pending and the user changes “Traer” to 3, the form still adds/submits 10, so partial receipts/invoices/orders from a source document cannot be created through this UI.

# cacao_accounting/compras/purchase_reconciliation_service.py

- Refactor this method to not always return the same value:

def _reconcile_three_way(invoice: PurchaseInvoice, config: MatchingConfig) -> PurchaseReconciliationResult:
Refactor this method to not always return the same value.

- Refactor this method to not always return the same value:
  
def _reconcile_two_way(invoice: PurchaseInvoice, config: MatchingConfig) -> PurchaseReconciliationResult:
Refactor this method to not always return the same value.

# cacao_accounting/admin/__init__.py

- Define a constant instead of duplicating this literal "admin.lista_modulos" 3 times.
- Define a constant instead of duplicating this literal "admin.cuentas_predeterminadas" 4 times.
- Define a constant instead of duplicating this literal "Usuario no encontrado." 4 times.
- Define a constant instead of duplicating this literal "admin.lista_usuarios" 9 times.
- Define a constant instead of duplicating this literal "admin.lista_roles" 5 times.

# cacao_accounting/auth/__init__.py

- Define a constant instead of duplicating this literal "profile.html" 5 times.
- Define a constant instead of duplicating this literal "Mi Perfil - Cacao Accounting" 5 times.

# cacao_accounting/auth/forms.py

- Define a constant instead of duplicating this literal "Segundo Nombre" 3 times.
- Define a constant instead of duplicating this literal "Segundo Apellido" 3 times.
- Define a constant instead of duplicating this literal "Correo electrónico" 3 times.
- Define a constant instead of duplicating this literal "Teléfono" 3 times.
- Define a constant instead of duplicating this literal "Confirmar contraseña" 3 times.
- Define a constant instead of duplicating this literal "Las contraseñas deben coincidir" 3 times.

# cacao_accounting/bancos/__init__.py

- Define a constant instead of duplicating this literal "bancos/transaccion_lista.html" 3 times.
- Define a constant instead of duplicating this literal "bancos/banco_cuenta_nuevo.html" 3 times.
- Define a constant instead of duplicating this literal "bancos.bancos_pago" 5 times.

# cacao_accounting/compras/__init__.py

- Define a constant instead of duplicating this literal "Factura de Compra" 3 times.
- Define a constant instead of duplicating this literal "compras/factura_compra_devolucion_lista.html" 3 times.
- Define a constant instead of duplicating this literal "compras.compras_factura_compra_nuevo" 3 times.
- Define a constant instead of duplicating this literal "compras.compras_orden_compra" 3 times.
- Define a constant instead of duplicating this literal "compras.compras_recepcion" 3 times.
- Define a constant instead of duplicating this literal "compras.compras_factura_compra" 5 times.

# cacao_accounting/compras/forms.py

- Define a constant instead of duplicating this literal "Compañía" 7 times.
- Define a constant instead of duplicating this literal "Fecha de Publicación" 6 times.

# cacao_accounting/contabilidad/__init__.py

- Define a constant instead of duplicating this literal "contabilidad.libros" 4 times.
- Define a constant instead of duplicating this literal "Sin padre" 4 times.
- Define a constant instead of duplicating this literal "contabilidad.ccostos" 4 times.
- Define a constant instead of duplicating this literal "contabilidad.proyectos" 5 times.
- Define a constant instead of duplicating this literal "contabilidad.fiscal_year_list" 5 times.
- Define a constant instead of duplicating this literal "contabilidad.periodo_contable" 5 times.
- Define a constant instead of duplicating this literal "contabilidad.ver_plantilla_recurrente" 3 times.
- Define a constant instead of duplicating this literal "contabilidad.asistente_cierre_mensual" 3 times.
- Define a constant instead of duplicating this literal "contabilidad.ver_cierre_mensual" 4 times.
- Define a constant instead of duplicating this literal "contabilidad.ver_comprobante" 9 times.
- Define a constant instead of duplicating this literal "contabilidad.editar_comprobante" 3 times.
- Define a constant instead of duplicating this literal "contabilidad.naming_series_list" 9 times.
- Define a constant instead of duplicating this literal "contabilidad.external_counter_list" 4 times.
- Define a constant instead of duplicating this literal "contabilidad.fiscal_year_closing_list" 4 times.

# cacao_accounting/contabilidad/forms.py

- Define a constant instead of duplicating this literal "Padding (digitos)" 3 times.
- Define a constant instead of duplicating this literal "Código" 3 times.
- Define a constant instead of duplicating this literal "Fecha Inicio" 4 times.
- Define a constant instead of duplicating this literal "Fecha Fin" 4 times.

# cacao_accounting/contabilidad/journal_service.py

- Define a constant instead of duplicating this literal "El comprobante indicado no existe." 6 times.

# cacao_accounting/contabilidad/recurring_journal_service.py

- Define a constant instead of duplicating this literal "Plantilla no encontrada." 3 times.

# cacao_accounting/database/__init__.py

- Define a constant instead of duplicating this literal "book.code" 3 times.
- Define a constant instead of duplicating this literal "naming_series.id" 9 times.
- Define a constant instead of duplicating this literal "external_counter.id" 5 times.
- Define a constant instead of duplicating this literal "user.id" 14 times.
- Define a constant instead of duplicating this literal "fiscal_year.id" 3 times.
- Define a constant instead of duplicating this literal "contact.id" 4 times.
- Define a constant instead of duplicating this literal "address.id" 7 times.
- Define a constant instead of duplicating this literal "tax_template.id" 4 times.
- Define a constant instead of duplicating this literal "batch.id" 5 times.
- Define a constant instead of duplicating this literal "purchase_order.id" 4 times.
- Define a constant instead of duplicating this literal "purchase_receipt.id" 3 times.
- Define a constant instead of duplicating this literal "sales_order.id" 3 times.
- Define a constant instead of duplicating this literal "bank_account.id" 5 times.
- Define a constant instead of duplicating this literal "recurring_journal_template.id" 3 times.
- Define a constant instead of duplicating this literal "book.id" 3 times.
- Define a constant instead of duplicating this literal "workflow_state.id" 3 times.

# cacao_accounting/datos/dev/data.py

- Define a constant instead of duplicating this literal "Chocolate 100g" 7 times.

# cacao_accounting/document_flow/registry.py

- Define a constant instead of duplicating this literal "compras.compras_factura_compra_nuevo" 3 times.
- Define a constant instead of duplicating this literal "Crear Factura" 4 times.
- Define a constant instead of duplicating this literal "ventas.ventas_factura_venta_nuevo" 3 times.

# cacao_accounting/document_identifiers.py

- Define a constant instead of duplicating this literal "El contador externo no existe." 3 times.
- Define a constant instead of duplicating this literal "El contador externo esta inactivo." 3 times.

# cacao_accounting/inventario/__init__.py

- Define a constant instead of duplicating this literal "inventario.inventario_entrada_nuevo" 8 times.
- Define a constant instead of duplicating this literal "inventario/entrada_lista.html" 8 times.
- Define a constant instead of duplicating this literal "inventario.inventario_entrada" 5 times.

# cacao_accounting/inventario/forms.py

- Define a constant instead of duplicating this literal "Código" 3 times.
- Define a constant instead of duplicating this literal "reportes/report_table.html" 5 times.

