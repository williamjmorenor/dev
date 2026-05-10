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

## Entiendo que se ha creado un framework centralizado para la gestión de reportes financieros

Pero lamentablemente los contadores tradicionales en reportes como Balanza de Comprobación, Estado de Resultados y Balance General esperan ver el tree view con nodos colapsables y poder navegar el arbol de cuentas en el archivo requerimiento.md he agregado contexto adicional del cambio requerido
