# Criterios de aceptación — Implementación de Comprobante Contable

## Objetivo

Definir los criterios funcionales, contables, técnicos y de experiencia de usuario que debe cumplir la implementación del módulo de Comprobante Contable del sistema Cacao Accounting.

---

# 1. Arquitectura General del Comprobante

## CA-001 — Estructura maestro/detalle

### Criterio de aceptación

El comprobante contable debe estar compuesto por:

1. Un registro maestro (header).
2. Uno o múltiples registros de líneas contables (detail).

### Validaciones

* El registro maestro debe almacenar:

  * ID único interno.
  * Referencia visible para usuario.
  * Compañía.
  * Fecha de contabilización.
  * Serie/secuencia.
  * Moneda del comprobante.
  * Concepto global.
  * Indicador `is_closing`.
  * Estado del comprobante.

* Las líneas deben almacenar:

  * Cuenta contable.
  * Débito.
  * Crédito.
  * Centro de costo.
  * Unidad de negocio.
  * Proyecto.
  * Tipo de tercero.
  * Tercero.
  * Documento referenciado.
  * Comentario de línea.
  * Indicador de anticipo.

---

# 2. Año Fiscal y Periodos Contables

## CA-002 — Inferencia automática de periodo contable

### Criterio de aceptación

El sistema debe inferir automáticamente el periodo contable y año fiscal utilizando únicamente la fecha de contabilización.

### Validaciones

* El usuario NO debe seleccionar manualmente:

  * Periodo contable.
  * Año fiscal.

* La fecha contable debe determinar automáticamente:

  * Año fiscal.
  * Periodo contable.

---

## CA-003 — Bloqueo por año fiscal cerrado

### Criterio de aceptación

El sistema debe impedir registrar comprobantes en años fiscales cerrados.

### Validaciones

* Si el año fiscal está cerrado:

  * Debe bloquearse cualquier posteo.
  * Debe mostrarse mensaje de error funcional.

* La bandera `is_closing` NO debe ignorar el cierre fiscal.

---

## CA-004 — Restricción por periodo contable cerrado

### Criterio de aceptación

Los periodos contables cerrados deben bloquear transacciones normales.

### Validaciones

* Si el periodo está cerrado:

  * Solo se permiten comprobantes con `is_closing = true`.

* Si `is_closing = false`:

  * El sistema debe impedir guardar y contabilizar.

---

# 3. Smart Select y Experiencia de Usuario

## CA-005 — Precarga inteligente de compañía

### Criterio de aceptación

El selector de compañía debe precargar registros automáticamente al abrir el formulario.

### Validaciones

* Debe existir búsqueda incremental.
* Debe existir filtrado por escritura.
* El usuario debe poder:

  * Seleccionar desde lista.
  * Escribir para buscar.

---

## CA-006 — Campo oculto de compañía

### Criterio de aceptación

Al seleccionar una compañía, el sistema debe actualizar automáticamente un campo oculto interno.

### Validaciones

* El campo oculto debe ser la fuente oficial de verdad para:

  * Filtrado de secuencias.
  * Filtrado de terceros.
  * Filtrado de documentos.
  * Filtrado de libros.
  * Filtrado de proyectos.
  * Filtrado de centros de costo.

* Los filtros NO deben depender del texto visible del selector.

---

## CA-007 — Smart Select dependiente

### Criterio de aceptación

Todos los Smart Select dependientes deben reaccionar automáticamente a los cambios de contexto.

### Validaciones

* Cambio de compañía:

  * Actualiza secuencias.
  * Actualiza libros.
  * Actualiza terceros.
  * Actualiza documentos.

* Cambio de tipo de tercero:

  * Actualiza selector de terceros.

* Cambio de tercero:

  * Actualiza documentos disponibles.

---

# 4. Series y Secuencias

## CA-008 — Secuencia predeterminada

### Criterio de aceptación

Al seleccionar una compañía, el sistema debe cargar automáticamente la secuencia predeterminada.

### Validaciones

* La secuencia debe obtenerse desde PADM.

* Debe existir una secuencia predeterminada por:

  * Compañía.
  * Tipo de documento.

* El usuario debe poder cambiar manualmente la secuencia.

---

## CA-009 — Búsqueda de secuencias

### Criterio de aceptación

El selector de secuencia debe soportar búsqueda incremental.

### Validaciones

* Debe permitir escribir para filtrar.
* Debe permitir seleccionar secuencias activas.
* Debe impedir seleccionar secuencias inactivas.

---

# 5. Libros Contables y Multi-Ledger

## CA-010 — Carga automática de libros activos

### Criterio de aceptación

Al seleccionar compañía, deben cargarse automáticamente los libros contables activos.

### Validaciones

* Los libros deben mostrarse preseleccionados.
* El usuario puede desmarcar libros específicos.
* Si todos permanecen seleccionados:

  * El comprobante afecta todos los libros.

---

## CA-011 — Generación automática de líneas por ledger

### Criterio de aceptación

El sistema debe generar automáticamente líneas contables independientes por cada libro seleccionado.

### Validaciones

* El usuario NO debe crear líneas separadas manualmente.
* El motor contable debe:

  * Crear una línea por ledger.
  * Realizar conversiones monetarias automáticamente.

### Ejemplo esperado

Si existen:

* Ledger local en Córdoba.
* Ledger financiero en USD.

Entonces:

* Debe generarse una línea en moneda local.
* Debe generarse otra línea convertida en USD.

---

# 6. Moneda del Comprobante

## CA-012 — Moneda única por comprobante

### Criterio de aceptación

El comprobante debe manejar una única moneda transaccional.

### Validaciones

* Todas las líneas deben heredar la moneda del comprobante.
* Las líneas NO pueden definir moneda propia.
* Debe bloquearse mezcla de monedas.

---

## CA-013 — Conversión automática de monedas

### Criterio de aceptación

El sistema debe convertir automáticamente montos para ledgers con moneda distinta.

### Validaciones

* La conversión debe ejecutarse automáticamente.
* Debe utilizar configuración monetaria definida en PADM.
* Debe registrar equivalentes correctamente por ledger.

---

# 7. Validaciones Contables

## CA-014 — Balance contable obligatorio

### Criterio de aceptación

El comprobante solo puede contabilizarse si está balanceado.

### Validaciones

* Total débitos = Total créditos.
* Si existe diferencia:

  * Debe bloquear contabilización.
  * Debe resaltarse visualmente la diferencia.

---

## CA-015 — Validación de cuentas de gasto

### Criterio de aceptación

Las cuentas de gasto deben requerir centro de costo.

### Validaciones

* Si cuenta es tipo gasto:

  * Centro de costo obligatorio.

* Si no se define:

  * Debe bloquear guardado.

---

## CA-016 — Validación de débitos/créditos

### Criterio de aceptación

Cada línea debe contener únicamente débito o crédito.

### Validaciones

* No puede existir:

  * Débito y crédito simultáneamente.
  * Débito y crédito vacíos.

---

# 8. Terceros y Subledgers

## CA-017 — Soporte de terceros

### Criterio de aceptación

El comprobante debe soportar afectación de terceros.

### Validaciones

* Tipos soportados:

  * Cliente.
  * Proveedor.
  * Empleado.

* El selector de tercero debe depender del tipo seleccionado.

---

## CA-018 — Integración con AR/AP Ledger

### Criterio de aceptación

Las líneas contables deben poder afectar subledgers de cuentas por cobrar y cuentas por pagar.

### Validaciones

* Los movimientos deben reflejarse en:

  * Estado de cuenta de clientes.
  * Estado de cuenta de proveedores.

* El saldo debe calcularse por:

  * Transacciones abiertas.
  * Independientemente del origen.

---

## CA-019 — Restricción sobre inventarios

### Criterio de aceptación

El comprobante contable NO debe afectar inventario.

### Validaciones

* Debe bloquear:

  * Movimientos de stock.
  * Ajustes de existencias.
  * Afectación de Kardex.

* Inventario solo puede modificarse desde módulos logísticos.

---

# 9. Documentos Referenciados

## CA-020 — Selección de documentos abiertos

### Criterio de aceptación

El comprobante debe permitir seleccionar documentos abiertos de terceros.

### Validaciones

* El selector debe depender de:

  * Compañía.
  * Tipo de tercero.
  * Tercero.
  * Tipo de documento.

* Solo deben mostrarse documentos:

  * Activos.
  * Con saldo pendiente.

### Documentos soportados

* Facturas.
* Notas de débito.
* Notas de crédito.
* Devoluciones.
* Otros documentos configurados.

---

## CA-021 — Soporte de cancelaciones contables

### Criterio de aceptación

El comprobante debe permitir cancelar parcial o totalmente saldos de AR/AP.

### Validaciones

* Debe permitir:

  * Castigos.
  * Ajustes.
  * Reclasificaciones.
  * Cancelaciones contables.

* Los saldos abiertos deben actualizarse automáticamente.

---

# 10. Modal Expandido de Línea

## CA-022 — Modal de detalle de línea

### Criterio de aceptación

Cada línea debe poder expandirse a un modal avanzado.

### Validaciones

* El modal debe permitir editar:

  * Proyecto.
  * Unidad.
  * Referencias.
  * Tipo de documento.
  * Documento relacionado.
  * Comentario.
  * Cuenta bancaria.
  * Anticipo.

---

## CA-023 — Persistencia completa de dimensiones

### Criterio de aceptación

Las dimensiones configuradas desde el modal deben persistirse correctamente.

### Validaciones

* Al cerrar y reabrir:

  * Deben mantenerse los datos.

* Al guardar:

  * Deben persistirse todas las dimensiones.

---

# 11. Comentarios y Referencias

## CA-024 — Comentario global y comentario por línea

### Criterio de aceptación

El comprobante debe soportar comentarios globales y específicos por línea.

### Validaciones

* Debe existir:

  * Concepto general.
  * Comentario individual por línea.

* Ambos deben persistirse independientemente.

---

# 12. Anticipos

## CA-025 — Marcado de anticipos

### Criterio de aceptación

Las líneas deben poder marcarse como anticipo.

### Validaciones

* Debe existir indicador `is_advance`.
* Debe persistirse en ledger.
* Debe ser visible posteriormente en conciliaciones.

---

# 13. Experiencia de Usuario

## CA-026 — Vista simplificada y avanzada

### Criterio de aceptación

La tabla principal debe mostrar únicamente dimensiones frecuentes.

### Validaciones

* Vista principal:

  * Cuenta.
  * Centro de costo.
  * Tipo tercero.
  * Tercero.
  * Débito.
  * Crédito.

* Vista avanzada:

  * Modal expandido.

---

## CA-027 — Indicadores visuales

### Criterio de aceptación

El sistema debe mostrar indicadores visuales de balance.

### Validaciones

* Debe mostrar:

  * Total débitos.
  * Total créditos.
  * Diferencia.

* Diferencias deben resaltarse visualmente.

---

# 14. Persistencia y Auditoría

## CA-028 — Trazabilidad completa

### Criterio de aceptación

Toda transacción debe ser completamente auditable.

### Validaciones

* Registrar:

  * Usuario creador.
  * Fecha creación.
  * Usuario modificación.
  * Fecha modificación.
  * Ledger afectado.
  * Moneda.
  * Tasa de cambio.

---

## CA-029 — Integridad transaccional

### Criterio de aceptación

La contabilización debe ejecutarse de manera atómica.

### Validaciones

* Si falla una línea:

  * Debe revertirse toda la transacción.

* No pueden existir:

  * Ledgers parciales.
  * Posteos incompletos.

---

# 15. Estados del Comprobante

## CA-030 — Estados operativos

### Criterio de aceptación

El comprobante debe soportar estados operativos visibles.

### Estados mínimos

* Borrador.
* Contabilizado.
* Cancelado.
* Reversado.
* Cierre.

### Validaciones

* Los estados deben mostrarse visualmente mediante badges.
* Deben existir restricciones según estado.

---

# 16. Restricciones Funcionales

## CA-031 — Restricción de edición

### Criterio de aceptación

Los comprobantes contabilizados no deben editarse libremente.

### Validaciones

* Debe bloquearse edición directa.
* La corrección debe realizarse mediante:

  * Reversión.
  * Ajuste.
  * Cancelación.

---

# 17. Rendimiento

## CA-032 — Rendimiento aceptable

### Criterio de aceptación

El formulario debe responder fluidamente.

### Validaciones

* Smart Select:

  * Debe responder en tiempo razonable.

* Apertura de modal:

  * No debe congelar interfaz.

* Cambios de compañía:

  * Deben refrescar dependencias automáticamente.

---

# 18. Criterio Final de Aprobación

## CA-033 — Validación integral

### El módulo será considerado aceptado únicamente si

* Cumple integridad contable.
* Soporta multi-ledger.
* Soporta multimoneda.
* Soporta subledgers AR/AP.
* Soporta cierres fiscales.
* Soporta cierres contables.
* Mantiene trazabilidad completa.
* Mantiene atomicidad transaccional.
* Mantiene experiencia de usuario fluida.
* Mantiene consistencia de Smart Select dependientes.
* Impide inconsistencias contables.
* Impide mezcla de monedas.
* Impide posteo en periodos inválidos.
