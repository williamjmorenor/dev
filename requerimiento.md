Requerimiento Técnico: Framework de Trazabilidad de Documentos
1. Objetivo

Implementar un framework transversal que permita visualizar, consultar, filtrar y navegar entre documentos relacionados dentro del sistema, siguiendo un modelo similar al concepto de Flujo de Documentos de SAP Business ByDesign y Document Link de ERPNext.

El objetivo principal es que el usuario pueda entender rápidamente la cadena documental completa de una operación, por ejemplo:

Solicitud de compra → Orden de compra → Entrega entrante → Factura de proveedor → Pago a proveedor

El framework debe permitir responder preguntas como:

¿Qué documentos originaron este registro?
¿Qué documentos fueron creados a partir de este registro?
¿Qué documentos relacionados siguen activos?
¿Qué documentos están pendientes, completados, cancelados o parcialmente procesados?
¿Qué pagos, facturas, recepciones o solicitudes están asociados a una operación específica?
2. Concepto General

Cada documento operativo del sistema podrá tener relaciones con otros documentos.

Estas relaciones deberán permitir:

Ver documentos origen.
Ver documentos destino.
Ver documentos relacionados directa o indirectamente.
Consultar documentos asociados por tipo.
Navegar hacia la lista filtrada del documento relacionado.
Consultar el estado actual de cada documento relacionado.
Mantener trazabilidad incluso si un documento es cancelado, anulado o cerrado.

El framework no debe limitarse a compras. Debe ser reutilizable para ventas, inventario, contabilidad, pagos, proyectos, tickets, órdenes de trabajo u otros módulos.

3. Componentes Principales
3.1 Registro de Relaciones entre Documentos

Se deberá crear una estructura centralizada para registrar relaciones documentales.

Entidad sugerida: document_links

Campos mínimos:

Campo	Descripción
id	Identificador interno
source_doctype	Tipo de documento origen
source_id	ID del documento origen
target_doctype	Tipo de documento destino
target_id	ID del documento destino
relation_type	Tipo de relación
company_id	Compañía asociada, cuando aplique
status	Estado de la relación
source_line_id	Línea origen, si aplica
target_line_id	Línea destino, si aplica
linked_quantity	Cantidad relacionada, si aplica
linked_amount	Monto relacionado, si aplica
created_by	Usuario que creó la relación
created_at	Fecha de creación
cancelled_at	Fecha de cancelación de relación, si aplica
metadata	JSON para datos adicionales
3.2 Tipos de Relación

El sistema debe soportar distintos tipos de relación:

Tipo	Descripción
created_from	Documento creado desde otro
created_to	Documento generado como continuación
references	Referencia manual o informativa
settles	Documento que liquida otro, ejemplo: pago contra factura
fulfills	Documento que cumple parcial o totalmente otro
adjusts	Documento que ajusta otro
reverses	Documento que reversa/anula otro
consolidates	Documento creado a partir de varios documentos
splits	Documento origen dividido en varios documentos destino

Ejemplo:

Una orden de compra creada desde varias solicitudes de compra tendría varias relaciones consolidates.

Una factura de proveedor creada desde una recepción tendría relación created_from.

Un pago a proveedor tendría relación settles contra una factura, y trazabilidad indirecta hacia la orden y solicitud de compra.

4. Visualización en el Documento
4.1 Panel Colapsable de Documentos Relacionados

Cada documento operativo deberá mostrar un panel colapsable llamado, por ejemplo:

Documentos relacionados
o
Flujo de documentos

El diseño recomendado es similar a ERPNext:

Menú colapsable dentro de la vista del documento.
Agrupación por tipo de documento.
Contador visible por cada tipo.
Botón o enlace para abrir la lista filtrada.
Indicador visual de estado mediante badge.
Opción para crear documentos relacionados cuando aplique.

Ejemplo:

Documentos relacionados

Compras
- Solicitudes de compra (2)
- Órdenes de compra (1)
- Entregas entrantes (1)
- Facturas de proveedor (1)
- Pagos a proveedor (1)

Contabilidad
- Asientos contables (3)

Inventario
- Movimientos de inventario (2)
4.2 Contadores

Cada tipo de documento relacionado debe mostrar un contador.

El contador debe representar documentos activos asociados al documento actual.

Ejemplo:

Factura de proveedor (3)
Pagos a proveedor (2)
Recepciones pendientes (1)

Los documentos cancelados o anulados no deben ocultarse necesariamente, pero deben diferenciarse visualmente.

Se recomienda permitir dos conteos:

Activos: documentos vigentes, abiertos, aprobados, parcialmente completados o contabilizados.
Históricos: documentos cancelados, anulados o reversados.

Ejemplo:

Facturas de proveedor (2 activas / 1 anulada)
5. Navegación hacia Listas Filtradas

Al hacer clic sobre un tipo de documento relacionado, el usuario debe ser llevado a la lista del documento seleccionado, filtrada automáticamente por relación con el documento actual.

Ejemplo:

Desde una Solicitud de Compra 13003, al hacer clic en Órdenes de Compra, el sistema debe abrir:

Lista de Órdenes de Compra
Filtro: relacionadas con Solicitud de Compra 13003

Esto implica que todas las vistas de lista de documentos operativos deben soportar filtros por relación documental.

6. Filtros por Relación Documental

Las listas de documentos deberán permitir filtrar por:

Tipo de documento relacionado.
ID del documento relacionado.
Dirección de la relación: origen, destino o ambos.
Tipo de relación.
Estado de la relación.
Compañía.
Estado del documento relacionado.
Fecha de creación de la relación.
Usuario que creó la relación.

Ejemplo de filtros:

Órdenes de compra relacionadas con Solicitud de Compra 13003
Facturas relacionadas con Orden de Compra OC-00021
Pagos relacionados con Factura FP-00045
Documentos creados desde Pedido de Cliente SO-00010
Documentos que liquidan Factura FV-00099
7. Filtros Avanzados en Listas de Documentos

Cada lista de documentos operativos debe incluir filtros estándar y filtros personalizados.

7.1 Filtros estándar

Cada tipo de documento debe mostrar filtros comunes según su naturaleza.

Ejemplo para facturas:

Estado.
Fecha.
Proveedor.
Compañía.
Moneda.
Monto.
Creado por.
Aprobado por.
Fecha de aprobación.
Estado de contabilización.
Estado de pago.
7.2 Filtros personalizados

El usuario debe poder agregar filtros sobre campos del encabezado del documento.

Ejemplo:

approved_by = "usuario_01"
approved_at BETWEEN "2026-05-01 08:00" AND "2026-05-01 12:00"
status != "Cancelled"
company = "Empresa A"
supplier = "Proveedor X"

Esto debe permitir búsquedas avanzadas como:

Ver todas las facturas aprobadas por un usuario específico entre ciertas horas.

8. Modelo de Estados y Badges

El framework debe integrarse con un sistema común de estados visuales.

8.1 Colores sugeridos
Color	Uso
Gris	Cancelado, anulado, archivado
Verde	Correcto, completado, contabilizado, aprobado
Azul	En proceso, abierto, parcialmente completado
Rojo	Requiere atención, atrasado, rechazado, error
8.2 Estados sugeridos

Estados informativos:

Abierto.
Vigente.
Parcialmente completo.
Completado.
Aprobado.
Contabilizado.
Pagado.
Parcialmente pagado.
Atrasado.
Requiere atención.
Cancelado.
Anulado.
Reversado.
Cerrado.

El badge debe ser visible tanto en:

Vista individual del documento.
Panel de documentos relacionados.
Vista de lista.
Resultados filtrados.
9. Trazabilidad Directa e Indirecta

El sistema debe distinguir entre:

9.1 Relación directa

Documentos relacionados explícitamente entre sí.

Ejemplo:

Orden de compra → Factura de proveedor
9.2 Relación indirecta

Documentos relacionados a través de una cadena documental.

Ejemplo:

Solicitud de compra → Orden de compra → Factura de proveedor → Pago

Desde la solicitud de compra, el usuario debe poder llegar al pago aunque no exista una relación directa entre ambos, porque la relación puede resolverse mediante la cadena documental.

10. Reglas de Integridad

El framework debe garantizar consistencia documental.

Reglas mínimas:

No se debe duplicar la misma relación entre dos documentos con el mismo tipo de relación.
Un documento cancelado debe conservar su trazabilidad histórica.
La anulación de un documento debe liberar saldos pendientes cuando aplique.
Los documentos relacionados deben recalcular sus saldos pendientes.
Las relaciones por línea deben permitir controlar cantidades y montos parciales.
No se debe permitir relacionar más cantidad o monto del disponible.
Las relaciones deben ser auditables.
Las relaciones críticas no deben eliminarse físicamente; deben marcarse como canceladas o inactivas.
11. Relaciones por Línea

El framework debe soportar trazabilidad a nivel de línea, no solo de encabezado.

Ejemplo:

Una orden de compra puede tomar líneas de varias solicitudes de compra.

Solicitud de Compra SC-001 Línea 1 → Orden de Compra OC-010 Línea 1
Solicitud de Compra SC-002 Línea 3 → Orden de Compra OC-010 Línea 2

Esto permitirá:

Calcular cantidades pendientes.
Evitar procesar dos veces la misma línea.
Mostrar solo líneas disponibles para documentos posteriores.
Manejar consolidaciones.
Manejar entregas parciales.
Manejar facturación parcial.
Manejar pagos parciales.
12. Creación de Documentos Relacionados

Desde un documento, el usuario debe poder crear documentos subsecuentes.

Ejemplo:

Desde una solicitud de compra:

Crear Orden de Compra

Desde una orden de compra:

Crear Entrega Entrante
Crear Factura de Proveedor

Desde una factura:

Crear Pago
Crear Nota de Crédito

Al crear un documento relacionado, el sistema debe:

Crear automáticamente el vínculo documental.
Heredar datos relevantes.
Permitir seleccionar líneas disponibles.
Evitar usar líneas ya completadas.
Registrar cantidades o montos vinculados.
Actualizar contadores y estados.
13. Consulta de Líneas Disponibles

El sistema debe permitir seleccionar líneas pendientes desde documentos previos.

Ejemplo:

Crear una orden de compra desde varias solicitudes de compra.

El sistema debe mostrar únicamente líneas:

Aprobadas.
No canceladas.
No cerradas.
Con cantidad o monto pendiente.
De la misma compañía, cuando aplique.
Compatibles con el documento destino.
14. Auditoría

Toda relación documental debe ser auditable.

Se debe registrar:

Usuario que creó la relación.
Fecha y hora.
Documento origen.
Documento destino.
Tipo de relación.
Cantidad o monto vinculado.
Cambios posteriores.
Cancelaciones o reversas.
Usuario que anuló o modificó.
Razón de anulación, si aplica.
15. Permisos

El usuario solo debe ver documentos relacionados si tiene permiso para ver ese tipo de documento.

Reglas:

Si no tiene permiso sobre el documento relacionado, no debe poder abrirlo.
El contador puede ocultarse o mostrarse de forma limitada según configuración.
La navegación a listas filtradas debe respetar permisos.
La creación de documentos relacionados debe respetar permisos de creación.
Los filtros avanzados deben respetar campos permitidos para el rol.
16. Requerimientos Técnicos de API

El framework debe exponer servicios reutilizables.

Servicios sugeridos:

GET /api/document-links/{doctype}/{id}

Devuelve documentos relacionados al documento actual.

GET /api/document-links/{doctype}/{id}/summary

Devuelve resumen agrupado por tipo de documento.

GET /api/documents/{doctype}?related_doctype=PurchaseRequest&related_id=13003

Lista documentos filtrados por relación.

POST /api/document-links

Crea una relación documental.

POST /api/document-links/bulk

Crea múltiples relaciones, útil para documentos consolidados.

DELETE /api/document-links/{id}

No debe eliminar físicamente; debe marcar como cancelado o inactivo.

17. Requerimientos de UI

La interfaz debe incluir:

Panel colapsable de documentos relacionados.
Agrupación por módulo o tipo documental.
Contadores por tipo.
Badges de estado.
Acceso rápido a listas filtradas.
Botón para crear documento relacionado, cuando aplique.
Vista de árbol o línea de tiempo opcional para flujos complejos.
Filtros estándar por documento.
Constructor de filtros avanzados por campos del encabezado.
Guardado de filtros favoritos.
Opción de limpiar filtros.
Opción de combinar filtros estándar, avanzados y relacionales.
18. Criterios de Aceptación

El desarrollo se considerará aceptado cuando:

Un documento pueda mostrar documentos relacionados agrupados por tipo.
Cada tipo relacionado muestre un contador correcto.
El usuario pueda hacer clic en un tipo relacionado y abrir la lista filtrada.
Las listas permitan filtrar por relación documental.
Las listas permitan filtros avanzados por campos del encabezado.
El sistema respete permisos de visualización y creación.
Las relaciones se conserven aunque un documento sea cancelado.
La cancelación o reversa actualice saldos pendientes.
El sistema soporte relaciones a nivel de línea.
No se puedan consumir dos veces las mismas cantidades o montos.
Los documentos consolidados puedan relacionarse con múltiples documentos origen.
Los estados y badges sean visibles y consistentes.
Toda relación quede registrada en auditoría.
19. Resultado Esperado

El sistema deberá contar con un framework robusto de trazabilidad documental que permita al usuario entender de un vistazo el historial, estado y continuidad operativa de cualquier documento.

La experiencia recomendada debe seguir el enfoque de ERPNext:

Panel colapsable.
Agrupación por tipo.
Contadores.
Acceso rápido a listas filtradas.
Filtros avanzados flexibles.

Pero con mayor rigor técnico para soportar:

relaciones por línea,
saldos pendientes,
cancelaciones,
consolidaciones,
documentos parciales,
auditoría,
permisos,
estados visuales,
y trazabilidad directa e indirecta.