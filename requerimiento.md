Sí: con lo que describes, el problema está claramente en el contrato de comportamiento del frontend, no en la API.

El archivo actual permite preload, loadOnFilterChange y lógica activa en onFocus, por eso un campo puede mostrar resultados solo al recibir foco. Ese comportamiento existe explícitamente en onFocus() y preloadOptions() dentro de smart-select.js. 
Tu requerimiento funcional confirma que solo compañía debe precargar, y que los demás campos solo deben consultar backend cuando el usuario escriba. 

Diagnóstico del issue

El comportamiento incorrecto viene de esta regla actual:

onFocus: function () {
  if ((this.preload || this.loadOnFilterChange) && !this.open && !this.loading) {
    ...
    this.preloadOptions();
  }
}

Eso permite que un campo como naming_series abra opciones solo por foco, especialmente si tiene:

loadOnFilterChange: true

o

preload: true

Para tu caso ERP, eso es incorrecto.


---

Requerimiento técnico propuesto

Título

Corrección del comportamiento de Smart Select para evitar precarga no deseada en campos dependientes

Contexto

En formularios contables y operativos, la compañía funciona como dimensión principal del documento. El campo compañía puede precargar registros activos porque normalmente el volumen es bajo y porque define el contexto operativo del formulario.

Los demás campos dependientes —secuencia, tercero, cuenta, producto, centro de costo, proyecto, unidad, etc.— no deben precargar resultados al recibir foco ni al cambiar filtros. Deben esperar interacción explícita del usuario mediante escritura.

Problema

En /accounting/journal/new, el campo de secuencia muestra resultados al recibir foco. Este comportamiento no es esperado.

Además, al escribir en el campo de secuencia, la API recibe parámetros incorrectos como:

company=[object Object]

Esto indica que el frontend está enviando un objeto completo como filtro en lugar del valor real esperado, probablemente company_id o código de compañía.

Comportamiento esperado

Campo compañía

Debe:

1. Precargar compañías activas.


2. Mostrar opciones al recibir foco.


3. Filtrar localmente o vía backend al escribir.


4. Al seleccionarse, establecer el filtro de compañía para el resto del formulario.


5. Disparar actualización contextual de campos dependientes.



Campo secuencia / naming series

Debe:

1. No mostrar lista al recibir foco.


2. No consultar backend al recibir foco.


3. No precargar todas las secuencias de la compañía.


4. Al cambiar compañía, cargar únicamente la secuencia predeterminada aplicable.


5. Permitir que el usuario borre la secuencia predeterminada.


6. Al comenzar a escribir, consultar backend usando:

doctype=naming_series

q=<texto digitado>

company=<valor real de compañía>

entity_type=journal_entry

limit=20




Campos dependientes en general

Deben:

1. Limpiarse cuando cambia un filtro del que dependen.


2. No consultar backend automáticamente por foco.


3. No consultar backend automáticamente por cambio de filtro, salvo que el campo tenga una acción explícita de carga de default.


4. Consultar backend únicamente cuando el usuario escriba el mínimo de caracteres requerido.


5. Enviar filtros normalizados, nunca objetos JavaScript crudos.




---

Cambio requerido en la librería

1. Separar dos conceptos

Actualmente loadOnFilterChange mezcla dos comportamientos:

reaccionar al cambio de filtro;

cargar opciones.


Debe separarse en:

clearOnFilterChange: true
loadDefaultOnFilterChange: false
preloadOptionsOnFocus: false

2. Nuevo contrato recomendado

{
  preload: false,
  openOnFocus: false,
  searchOnFocus: false,
  clearOnFilterChange: true,
  loadDefaultOnFilterChange: false,
  searchOnlyOnInput: true
}

3. Regla global

Para todos los Smart Select excepto compañía:

El evento focus no debe ejecutar fetch.

4. Regla específica para compañía

Solo compañía puede usar:

preload: true,
openOnFocus: true

5. Regla específica para secuencia

Secuencia debe usar:

preload: false,
openOnFocus: false,
loadOnFilterChange: false,
clearOnFilterChange: true,
autoLoadDefaultOnCompanyChange: true


---

Corrección importante de filtros

El log muestra:

company=[object Object]

Eso debe corregirse. El frontend debe enviar un valor escalar.

Incorrecto:

filters: {
  company: someCompanyObject
}

Correcto:

filters: {
  company: function () {
    return document.querySelector('[name="company"]').value;
  }
}

o:

filters: {
  company: { selector: '[name="company"]' }
}


---

Pruebas unitarias que faltan

Las pruebas actuales no capturan el error porque probablemente validan búsqueda, pero no validan ausencia de efectos secundarios.

Agregar pruebas para:

Caso 1: campo no preload no consulta en focus

Dado un smart select con preload=false y loadOnFilterChange=false
Cuando el usuario hace focus
Entonces no se debe llamar fetch
Y no se debe abrir la lista de opciones

Caso 2: campo dependiente se limpia al cambiar compañía

Dado un campo secuencia con valor seleccionado
Cuando cambia compañía
Entonces selectedValue, selectedLabel, search y options deben quedar vacíos
Y no debe ejecutarse fetch

Caso 3: búsqueda solo por input

Dado un campo secuencia dependiente de compañía
Cuando el usuario escribe al menos minChars caracteres
Entonces se ejecuta fetch con company como valor escalar

Caso 4: nunca enviar objetos como filtros

Dado un filtro company configurado
Cuando se construyen parámetros
Entonces company no debe ser "[object Object]"


---

Requerimiento resumido para implementación

El formulario de comprobante contable debe implementar un comportamiento de Smart Select orientado a formularios ERP. El campo compañía será el único campo con precarga y apertura automática al recibir foco. Los demás campos deberán permanecer inactivos al recibir foco y solo deberán consultar el backend cuando el usuario escriba el mínimo de caracteres requerido. Los cambios en compañía u otros filtros deberán limpiar campos dependientes, aplicar nuevos filtros contextuales y, únicamente cuando exista una regla explícita de default, asignar un valor predeterminado sin abrir listas ni precargar resultados.
