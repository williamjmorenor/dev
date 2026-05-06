Requerimiento Técnico
Framework de Conciliación de Compras (Alternativa Moderna a GR/IR)
1. Objetivo

Diseñar e implementar un framework desacoplado de conciliación de compras que:

Modele correctamente el flujo real del negocio
Separe completamente:
Operación (documentos)
Conciliación (matching)
Contabilidad (registro financiero)
Permita alta configurabilidad sin introducir rigidez estructural
2. Principios de Diseño
2.1 Process-first (obligatorio)

El sistema debe modelar primero los eventos del negocio antes de generar cualquier impacto contable.

2.2 Event-driven architecture

Cada documento genera eventos económicos inmutables.

2.3 Desacoplamiento fuerte

Separación estricta entre:

Capa	Responsabilidad
Operacional	Documentos (OC, Recepción, Factura)
Conciliación	Matching y control
Contable	Generación de asientos
2.4 Auditabilidad total

Todos los eventos deben ser:

Inmutables
Trazables
Reproducibles
3. Modelo de Entidades
3.1 Documentos Operativos (core)
Orden de Compra (OC)
id
proveedor_id
moneda
líneas (producto, cantidad, precio)
estado
Recepción de Bienes
id
oc_id
líneas (producto, cantidad recibida)
fecha
Factura de Proveedor
id
proveedor_id
referencia externa
líneas (producto, cantidad, precio facturado)
impuestos

⚠️ Restricción:

Estas entidades NO deben contener lógica de conciliación ni contabilidad.

3.2 Entidad de Conciliación (core del diseño)
Conciliación
id
oc_id
estado
tipo_matching (2-way | 3-way)
tolerancia_precio
tolerancia_cantidad
fecha_creación
Relaciones
conciliacion_receipts
conciliacion_invoices
Métricas calculadas
cantidad_ordenada
cantidad_recibida
cantidad_facturada
monto_ordenado
monto_facturado
diferencias
4. Estados de Conciliación

El sistema debe soportar únicamente los siguientes estados:

Pendiente Recepción
Pendiente Factura
Parcial
Conciliado
En Disputa
Reglas
Estado derivado automáticamente (no editable manualmente)
Basado en comparación de cantidades y montos
5. Motor de Matching
5.1 Configuración

Debe ser totalmente configurable por compañía:

tipo_matching:
2-way (OC vs Factura)
3-way (OC vs Recepción vs Factura)
tolerancia_precio:
porcentaje (%)
monto absoluto
tolerancia_cantidad:
porcentaje (%)
cantidad absoluta
5.2 Lógica de Evaluación

El motor debe:

Agrupar líneas por producto
Comparar:
OC vs Recepción
OC vs Factura
Recepción vs Factura (en 3-way)
Calcular desviaciones:
Δ cantidad
Δ precio
Δ monto
Evaluar contra tolerancias
5.3 Resultado del Matching
MATCH_OK
MATCH_PARTIAL
MATCH_FAILED
6. Eventos Económicos (clave del diseño)

Cada acción genera un evento:

Tipos de eventos
GOODS_RECEIVED
INVOICE_RECEIVED
MATCH_COMPLETED
MATCH_FAILED
Estructura
id
tipo_evento
referencia_documento
payload (JSON)
timestamp
estado_procesamiento

⚠️ Restricción:

Los eventos son inmutables.

7. Motor Contable (desacoplado)
7.1 Principio

La contabilidad NO se genera en el momento del documento.

Se genera en función de eventos.

7.2 Reglas configurables

Ejemplos:

Evento	Acción
GOODS_RECEIVED	Débito inventario / Crédito cuenta puente
INVOICE_RECEIVED	Débito cuenta puente / Crédito cuentas por pagar
MATCH_FAILED	No generar asiento
7.3 Cuenta Puente (GR/IR)
Implementación opcional
Configurable por compañía
No debe estar hardcodeada al flujo
8. Flujo Operativo
Escenario estándar (3-way matching)
Crear OC
Registrar Recepción → genera evento
Registrar Factura → genera evento
Ejecutar Matching automático
Actualizar estado de conciliación
Motor contable evalúa eventos y genera asientos
9. Reglas de Negocio Críticas
9.1 No duplicidad
Una línea no puede ser conciliada más allá de su cantidad disponible
9.2 Reversión
Anulación de recepción:
Genera evento inverso
Libera cantidades
Anulación de factura:
Reabre conciliación
10. UI/UX (alineado a tu visión ERPNext-like)
Panel de Conciliación
Vista colapsable por documento
Contadores:
Recepciones: N
Facturas: N
Indicadores visuales (badges):
Estado	Color
Conciliado	Verde
Parcial	Azul
Pendiente	Gris
Disputa	Rojo
11. Diferenciación Estratégica
ERP tradicionales
Sistema	Enfoque
SAP ERP	Contabilidad-first
Oracle ERP Cloud	Contabilidad configurable
Microsoft Dynamics 365	Documento-first con límites
Tu enfoque

Process-first + Event-driven + Contabilidad desacoplada

12. Beneficios Esperados
Técnicos
Bajo acoplamiento
Alta extensibilidad
Testing más simple
Funcionales
Mayor claridad para usuario
Mejor trazabilidad
Flexibilidad en reglas
Contables
Igual nivel de auditoría que GR/IR tradicional
Mayor control en timing de reconocimiento
13. Riesgos y Consideraciones
Requiere disciplina en modelado de eventos
Necesita motor contable robusto
Debe evitar duplicación de lógica entre capas
14. Criterios de Aceptación
Se puede ejecutar matching sin generar asientos contables
Se puede cambiar tolerancias sin alterar datos históricos
Se pueden reconstruir estados desde eventos
El sistema soporta 2-way y 3-way sin cambios estructurales
La cuenta puente es configurable, no obligatoria