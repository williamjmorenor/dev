Requerimiento técnico: Framework unificado de campos seleccionables inteligentes
1. Objetivo

Implementar un framework reutilizable de frontend y backend para campos HTML de selección asistida, tipo autocomplete/search-select, que permita buscar registros dinámicamente mediante API, aplicar filtros contextuales y ofrecer una experiencia consistente en escritorio y dispositivos móviles.

El framework debe sustituir el uso de <select> tradicionales en catálogos grandes o contextuales.

2. Problema a resolver

Los campos <select> básicos generan mala experiencia cuando existen muchos registros, por ejemplo:

Catálogo de cuentas con cientos de cuentas.
Lista amplia de clientes, proveedores o empleados.
Centros de costo, unidades, proyectos o documentos operativos.
Mal comportamiento en Android, donde el selector nativo obliga a navegar manualmente muchas opciones.

El usuario no debe ver todas las opciones inicialmente. El campo debe consultar opciones solamente cuando el usuario escriba suficientes caracteres.

3. Alcance funcional

El framework debe permitir:

Buscar registros por código, nombre, descripción o campos configurados.
Consultar opciones mediante una API unificada.
Definir el tipo de documento/catálogo desde el HTML.
Aplicar filtros estáticos y dinámicos.
Actualizar filtros cuando cambien otros campos del formulario.
Validar que el valor seleccionado sea válido.
Usarse en múltiples formularios sin duplicar lógica JavaScript.
Mantener una experiencia consistente en desktop y móvil.
4. Concepto propuesto

Cada campo seleccionable inteligente será un componente Alpine.js reutilizable.

Ejemplo conceptual:

<div
    x-data="smartSelect({
        doctype: 'account',
        minChars: 2,
        valueField: 'id',
        labelField: 'display_name',
        filters: {
            company: () => document.querySelector('[name=company_id]').value,
            account_type: 'bank',
            is_active: true
        }
    })"
>
    <input
        type="text"
        x-model="search"
        @input.debounce.300ms="fetchOptions"
        placeholder="Buscar cuenta..."
    >

    <input type="hidden" name="account_id" x-model="selectedValue">

    <template x-if="options.length">
        <ul>
            <template x-for="option in options" :key="option.id">
                <li @click="selectOption(option)" x-text="option.display_name"></li>
            </template>
        </ul>
    </template>
</div>
5. Atributos HTML recomendados

Para simplificar el uso en formularios, el sistema podrá usar atributos declarativos:

<div
    x-smart-select
    x-doctype="account"
    x-filter-company="#company_id"
    x-filter-account-type="bank"
    x-filter-active="true"
    x-min-chars="2"
    x-target-name="bank_account_id"
></div>

Atributos propuestos:

Atributo	Descripción
x-doctype	Tipo de catálogo o documento a consultar. Ejemplo: account, customer, supplier, employee, journal.
x-min-chars	Cantidad mínima de caracteres antes de consultar la API.
x-filter-company	Filtro por compañía. Puede ser valor fijo o referencia a otro campo.
x-filter-account-type	Filtro por tipo de cuenta contable.
x-filter-party-type	Filtro por tipo de tercero: cliente, proveedor, empleado.
x-filter-status	Filtro por estado del registro.
x-target-name	Nombre del campo oculto que almacenará el ID seleccionado.
x-label-field	Campo que se mostrará al usuario.
x-value-field	Campo que se enviará al backend al guardar el formulario.
6. API backend unificada

Endpoint sugerido:

GET /api/search-select

Parámetros:

/api/search-select?doctype=account&q=bank&company_id=COMP001&account_type=bank

Respuesta esperada:

{
  "doctype": "account",
  "query": "bank",
  "results": [
    {
      "id": "ACC001",
      "code": "1101",
      "name": "Banco BAC",
      "display_name": "1101 - Banco BAC"
    }
  ],
  "has_more": false
}
7. Registro backend de doctypes

El backend no debe permitir consultar cualquier tabla libremente. Debe existir un registro explícito de doctypes permitidos.

Ejemplo conceptual:

SEARCH_SELECT_REGISTRY = {
    "account": {
        "model": Account,
        "search_fields": ["code", "name"],
        "label": lambda row: f"{row.code} - {row.name}",
        "allowed_filters": ["company_id", "account_type", "is_active"],
        "default_filters": {"is_active": True},
        "limit": 20
    },
    "customer": {
        "model": Customer,
        "search_fields": ["code", "name", "tax_id"],
        "label": lambda row: f"{row.code} - {row.name}",
        "allowed_filters": ["company_id", "is_active"],
        "default_filters": {"is_active": True},
        "limit": 20
    }
}
8. Reglas de búsqueda

La búsqueda debe:

Iniciar solo cuando el usuario escriba al menos minChars.
Buscar por código y descripción.
Soportar coincidencia parcial.
Priorizar coincidencias que comienzan con el texto digitado.
Limitar resultados, por ejemplo 20 registros.
No devolver registros inactivos salvo que el doctype lo permita.
Respetar permisos del usuario.
Respetar compañía activa, si aplica.
9. Filtros dinámicos

El framework debe permitir que un campo dependa de otros campos del formulario.

Ejemplo:

El usuario selecciona compañía.
Luego el campo cuenta contable solo muestra cuentas de esa compañía.
Si el usuario cambia la compañía, el valor previamente seleccionado debe invalidarse si ya no corresponde.

Casos esperados:

Campo	Depende de	Resultado
Cuenta bancaria	Compañía	Solo cuentas bancarias de la compañía seleccionada
Cuenta por cobrar	Compañía + tipo de tercero cliente	Solo cuentas AR válidas
Proveedor	Compañía	Solo proveedores activos de esa compañía
Cliente	Compañía	Solo clientes activos de esa compañía
Líneas de documento	Documento origen	Solo líneas pendientes/no completadas
10. Validaciones
Frontend
No permitir valor libre si el campo requiere selección válida.
Mostrar estado visual cuando el valor seleccionado ya no es válido.
Limpiar selección si cambia un filtro padre.
Mostrar mensaje cuando no existan resultados.
Mostrar indicador de carga durante la búsqueda.
Backend
Validar que el doctype exista en el registry.
Validar que los filtros enviados estén permitidos.
Validar permisos del usuario.
Validar compañía, sucursal o entidad activa.
No confiar únicamente en filtros enviados por frontend.
Aplicar límites de resultados.
Evitar exposición de datos sensibles.
11. Librería frontend

Debe existir una única librería JavaScript, por ejemplo:

<script src="/static/js/smart-select.js"></script>

Esta librería debe:

Registrar el componente Alpine.js.
Manejar debounce.
Manejar loading state.
Manejar errores.
Manejar selección.
Manejar limpieza del campo.
Resolver filtros dinámicos.
Ser cacheable por navegador.
No duplicarse por formulario.
12. Criterios de aceptación

El requerimiento se considera cumplido cuando:

Un campo de cuenta contable puede buscar por código o nombre.
El campo no carga opciones antes de que el usuario escriba.
La API devuelve resultados filtrados por compañía y tipo de cuenta.
Cambiar la compañía limpia o invalida selecciones dependientes.
El componente funciona en móvil y escritorio.
El mismo componente puede usarse para cuentas, clientes, proveedores, empleados y documentos.
El backend impide consultar doctypes o filtros no registrados.
El formulario guarda el ID real del registro, no solo el texto mostrado.
La experiencia es superior al <select> tradicional para catálogos grandes.
13. Nombre sugerido del feature

Smart Select Framework