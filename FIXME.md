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

- URL: /accounting/accounts y /accounting/costs_center
  La opción de expandir o colapsar solo se esta aplicando a cuentas y centros de costos de primer nivel. La logica debe ser para expandir o colapsar si la cuenta o centro de costos es tipo parent y tiene hijos asociados. Si cumple esa caracteristica debe de poder expandirse y colapsarse.

  Pendiente opción de expandir / colapsar todos.
  
- URL: /accounting/book/list
  Al crear una compañia el libro contable por defecto llamarlo Local y no Fiscal
  
- URL: /accounting/journal/new
  En el selector de compañia dado que el principal campo actualizar cacao_accounting/static/js/smart-select.js para aceptar x-data-preload para cargar la lista de entidades antes que el usuario comienze a escribir, es decir cuando el usuario se ubica en el campo ya estan precargadas las compañias y puede comenzar a escribir o seleccionar una compañia de la lista.

  En el selector de secuencia dado que la secuencia tiene un valor predeterminado actualizar cacao_accounting/static/js/smart-select.js para que si existe un campo predeterminado llenar el campo con el valor predeterminado, otros casos de uso a crear un Nuevo Cliente llenar la cuenta por cobrar por defecto o crear un nuevo proveedor llenar la cuenta por cobrar por defecto.
  
- He intentado llenar un comprobante de prueba pero no me permite grabar porque hay campos requeridos sin llenar pero no me indica cuales
  <img width="1702" height="787" alt="image" src="https://github.com/user-attachments/assets/d9aedacc-d6e4-4b68-afef-f03858c09dfe" />

- En el modal para ingresar información adicional en una linea de un comprobante ningun campo funciona y en cuenta esta mostrando el id interno de el registro
  <img width="1902" height="913" alt="image" src="https://github.com/user-attachments/assets/811c378a-fb10-49c8-908a-f7c99c0e49be" />

  Este modal requiere una revisión completa.
