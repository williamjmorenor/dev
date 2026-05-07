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

- smart-select.js:1  Failed to load resource: the server responded with a status of 404 ()
   Al parecer el archivo cacao_accounting/static/js/smart-select.js no se esta distribuyendo correctamente al instalar como un paquete python, hay que asegurar que todo el contenido del directorio cacao_accounting se distribuya correctamente.

- URL: /accounting/costs_center:

   BuildError: werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'contabilidad.centro_costo' with values ['id_cc']. Did you mean 'contabilidad.nuevo_centro_costo' instead?

   Estos errores debería detectarlos el test tests/test_routes_map.py

- URl: /accounting/currency/list

   Nueva Moneda esta deshabilitado

- URL: /accounting/accounts y /accounting/costs_center

   El arbol de cuentas contables y de centros de costos debe de mostrarse como un treeview colapsible, prefiero en el treeview
   usar iconos como + para expandir y - para colaparsar

   Tener las opciones "Expandir todo" y "Colapsar todo" es útil

- URL: /accounting/accounting_period/new

   Vincula a la entidad año fiscal pero no observo el CRUD de año fiscal implementado por lo que en la practica esta URL no es funcional

   No me queda claro actualmente la diferencia entre Año y Fiscal y Periodo Contable

   Supongo que los periodos contable son mensuales y agrupados en un año fiscal, si es así al crear una compañia al crearse debería crear los doce periodos contables y el año fiscal actual como predeterminado.

   Dejar documentada desición de desarrollo Año Fiscal es en la practica padre de Perido Contable, conversar perido contable para cierres mensuales

- URL: /accounting/exchange

  No hay opción "Nuevo Tipo de Cambio"

- URL: /accounting/entity/new

   Seleccionar catalogo en cero debería de deshabilitar el selector de catalogos de cuenta predeterminado.

   Agregar opción Activa/Inactiva como bandera booleana

- URL: /accounting/accounts

   No hay opción nueva cuenta, verificar mismo patron para centros de costos

- URL: /accounting/unit/new

   Agregar opción Activa/Inactiva como bandera booleana

- URL: /accounting/project/new

   Agregar enum de estados: Abierto, Cerrado, Detenido solo Abierto y Habilitado debe haceptar movimientos en el ledger

Extender el posting service para atender los nuevos status y banderas booleanas de Activo/Inactivo

- URL: /settings

   Las opciones Inicio /Compras/Panel de Conciliación y Inicio/Compras/Conciliacion de Compras Pendiente no corresponden al menú de administración deben estar en el menú de Compras.