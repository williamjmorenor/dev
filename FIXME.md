Para trabajar en estos issues primeto debes cargar el contexto disponible de:

- AGENTS.md
- ESTADO_ACTUAL.md
- SESSIONS.md
- PENDIENTE.md

Los siguientes directorios contienen contexto adicional:

- .github/instructions
- modulos

Al finalizar cada iteración actualiza:

- ESTADO_ACTUAL.md
- SESSIONS.md
- PENDIENTE.md


Issues actuales que deben corregirse:

## Todos los reportes no debería mostrar información al cargar, unicamente mostrar información al Aplicar Fistros

# /reports/account-movement

## La función de guardar vista esta genial pero puede mejorarse:

1. Guardar Vista -> Permitir asignar nombre lo que haría es un pequeño modal que permita al establecer un nombre y guardarlo.
2. Completar el ciclo de vida de una vista guardada: Guardar, Actualizar, Eliminar
3. El campo de vista guardada debe usar smart-select respentando el usuario actual


## Al seleccionar buscar por ID Visible del comprobante no se muestran los valores esperados, actualmente muestra lo que parece ser un Objeto: <GLEntry kgpkcafa3l>

## Remover esto de la columna de totales: ✅ Cuadrado

## Los botones de Aplicar Filtros y Limpiar Filtros deben estar disponibles en la parte superior e inferior de la barra de filtros

## Renombrar ID visible del comprobante simplemente a Comprobante

## El Togle Mostrar / Ocultar Filtros avanzados no funciona

## La implementación de Columnas visibles no esta correcta: No nuestra todos los nombre de campos y seleccionar o deseleccionar columnas no afecta la tabla.

Columnas visibles
Posting Date
Period
Voucher
Type
Account
Account Name
Debit (NIO)
Credit (NIO)
Currency
Ledger
Company
cost_center
unit
project
party_type
party_id
line_comment
created_by
Creation Date
Status

## Las opciones de agrupar estan bien pero se necesita mostrar el sub total por agrupador

## El filtro Tipo de comprobante muestra sin resultados al comenzar a escribir

## El filtro Tipo de tercero nuestra lo que parece ser un objeto <Party 01KR76GMJ99EP3KAR5NFPQY9HY>

## Columnas visibles debería ser un modal

## Columnas visibles debe de poder incluir mas campos como referencia, es anulación, esta anulado.

## Agregar como Filtro de Primer Nivel: Mostrar anulaciones, por defecto Falso pero al cambiar a verdadero mostrar registros que se han cancelado con su respectivo comprobante de cancelación.

Esta funcionalidad es peligrosa si el comprobante existe en un mes y se cancela en otro. A nivel de flujo de no se tiene que permitir revertir o anular comprobantes de periodos cerrados.

Se espera que comprobante y su anulación esten en el mismo mes.

# /reports/trial-balance

## Eliminar Level, no tiene sentido tener esa columna

# Test estan fallando

## FAILED tests/test_11_contabilidad_coverage.py::test_route_entity_set_default - sqlalchemy.exc.InvalidRequestError: Entity namespace for "entity" has no property "predeterminada"

# dev/cacao_accounting/database/helpers.py

## Honor sequence reset policies before incrementing

Line 359 in d17a9ad

 next_val = get_next_sequence_value(sequence_id) 

For series whose Sequence.reset_policy is yearly or monthly, generate_identifier increments the sequence directly and never calls the reset helpers added below. After the first identifier in a new year/month, documents keep numbering from the previous period (for example 2026-...-00042 instead of resetting to 00001), so fiscal/period-based series do not satisfy their configured reset policy.

# cacao_accounting/bancos/__init__.py

## Restore invoice allocations when cancelling payments

    if registro.docstatus != 1:
        abort(400)
    try:
        cancel_document(registro)

When cancelling a PaymentEntry that was created with invoice references, this only reverses the GL entries; the PaymentReference rows created in _save_payment_references remain active and the invoice outstanding_amount cache is not restored. In that scenario AR/AP reports still subtract the cancelled payment while the GL has been reversed, so invoice balances and the ledger diverge. The cancel path should remove/void those references and refresh the affected invoices before committing.

# cacao_accounting/bancos/__init__.py

## Reconcile payment amount with allocated references

Comment on lines +741 to +742
            allocated = _save_payment_references(payment)
            if amount == 0 and allocated:

When the payment form posts invoice references and the entered payment amount is greater than the sum allocated by _save_payment_references, the code commits the full paid_amount/received_amount but only reduces invoices by the allocated total. Submitting that payment posts the full amount against AR/AP because references exist, while subledger/outstanding reports only see the smaller allocation, leaving GL and invoice balances inconsistent. Either require amount == allocated for referenced payments or explicitly record the remainder as an advance.


# cacao_accounting/__init__.py


## Add CSRF tokens before enabling global CSRF

        from flask_wtf.csrf import CSRFProtect

        csrf = CSRFProtect()
        csrf.init_app(app)

With global CSRFProtect enabled here, every POST is rejected unless the submitted form includes a valid csrf_token. I found changed POST forms that still omit it, for example cacao_accounting/admin/templates/admin/taxes.html posts to /settings/taxes with no hidden token, so saving taxes in a normal browser session will now return 400 before lista_impuestos runs (tests mostly set WTF_CSRF_ENABLED=False, so this can slip through).

# cacao_accounting/__init__.py

## Add CSRF tokens or exemptions for protected write flows

        from flask_wtf.csrf import CSRFProtect

        csrf = CSRFProtect()
        csrf.init_app(app)

Enabling global CSRFProtect makes every POST/PUT/DELETE require a token, but several callers added in this commit do not send one: for example the journal preferences fetch(..., { method: 'PUT'/'DELETE' }) only sends JSON headers/credentials, and new admin forms such as admin/taxes.html have no csrf_token input. In those UI paths Flask-WTF rejects the request with 400 before the route runs, so either include CSRF tokens in all forms/fetches or explicitly exempt JSON API endpoints that use another protection.


# cacao_accounting/search_select.py

## SEARCH_SELECT_REGISTRY es un diccionario una forma mas robusta para ese contenedor de datos

# cacao_accounting/auth/helpers.py

## def validar_clave_segura(clave: str) -> bool: Refactorizar como match/case 

# cacao_accounting/contabilidad/default_accounts.py

## SPECIAL_ACCOUNT_TYPES asegura que todos los tipos de cuentas necesarios estan disponibles para crear nuevas cuentas contables /accounting/account/new


## Estado de cierre

- ✅ Todos los issues listados en este archivo fueron atendidos en las iteraciones de 2026-05-10 y cerrados en backlog.
