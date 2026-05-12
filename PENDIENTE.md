# PENDIENTE — Cacao Accounting

Este documento registra todo lo que está pendiente de implementar para cumplir la especificación completa de los módulos del sistema.

---

## Posting Contable (Core crítico)
- [ ] Recalcular referencias y outstanding desde GL/allocations como fuente dinámica.
- [ ] Implementar FIFO y Moving Average reales para consumo de capas.
- [ ] Soportar tipos: estándar, apertura, nota de crédito, nota de débito, contra asiento, ajuste, reversión.
- [ ] Completar edición de borradores y lista operacional; `/gl/new` y `/gl/list` quedan como legacy hasta retiro.
- [ ] Resolver formalmente el comportamiento de `document_no` cuando un borrador cambia de serie antes de contabilizar.
- [ ] Implementar selector de documentos abiertos dependiente de compañía / tipo de tercero / tercero / tipo documental.

---

## Cuentas por Cobrar / Cuentas por Pagar (AR/AP)

### Aplicación de pagos a facturas
- [ ] Permitir desde el formulario de pago seleccionar una o varias facturas pendientes del mismo tercero.
- [ ] Registrar `PaymentReference` con `allocated_amount` y `allocation_date`.
- [ ] Actualizar `outstanding_amount` en las facturas aplicadas.
- [ ] Soportar pago parcial (un pago → una factura parcial).
- [ ] Soportar pago multiple (un pago → múltiples facturas).
- [ ] Soportar aplicación cruzada (múltiples pagos → una factura).

### Anticipos (totales y parciales)
- [ ] Registrar anticipo de cliente como pasivo (cuenta de anticipo de cliente).
- [ ] Registrar anticipo a proveedor como activo (cuenta de anticipo a proveedor).
- [ ] Aplicar anticipo contra factura mediante `PaymentReference` con `allocation_date`.
- [ ] Soportar aplicación parcial: el remanente queda como saldo a favor.
- [ ] Aplicar un anticipo a múltiples facturas del mismo tercero.

### Aging AR/AP
- [ ] Mejorar UX/exportación y permitir buckets configurables por compañía.

---

## Documentos de Corrección

### Nota de Crédito de Venta (Sales Credit Note)
- [ ] Verificar y reforzar la creación de nota de crédito de venta con `is_return=True` y `reversal_of` a factura origen.
- [ ] Generar GL inverso al de la factura original.
- [ ] Reducir `outstanding_amount` de la factura referenciada.
- [ ] Validar que la lista de notas de crédito muestre correctamente el origen y el estado del documento.

### Nota de Débito de Venta (Sales Debit Note)
- [ ] Verificar la creación de nota de débito de venta y su asociación a la factura origen.
- [ ] Generar GL adicional al de la factura original.
- [ ] Incrementar `outstanding_amount` de la factura referenciada.

### Devolución de Venta (Sales Return)
- [ ] Implementar retorno de mercancía: `DeliveryNote` con `is_return=True`.
- [ ] Revertir `StockLedgerEntry` y `StockValuationLayer`.
- [ ] Generar `SalesInvoice` de crédito asociada.

### Nota de Crédito de Compra (Purchase Credit Note)
- [ ] Ruta de creación desde factura de proveedor.
- [ ] `PurchaseInvoice` con `is_return=True` o vía nota de crédito de proveedor.
- [ ] Revertir impacto GL y ajustar `outstanding_amount` AP.

### Nota de Débito de Compra (Purchase Debit Note)
- [ ] Ruta de creación desde factura de proveedor.
- [ ] Incrementar `outstanding_amount` AP.

### Devolución de Compra (Purchase Return)
- [ ] `PurchaseReceipt` con `is_return=True`.
- [ ] Revertir `StockLedgerEntry`.
- [ ] Generar nota de crédito de proveedor asociada.

### Reversión de Comprobante Contable
- [ ] Trazabilidad bidireccional visible entre asiento original y reverso.

---

## Proveedor y Cliente (formularios completos)

### Formulario de Proveedor
- [ ] Validar y mejorar `proveedor_nuevo.html` tras la documentación de FIXME; el flujo actual es operativo pero requiere controles adicionales.
- [ ] Campos requeridos: razón social, identificación fiscal, moneda, condiciones de pago, cuentas AP.
- [ ] Gestión de direcciones (`Address`) y contactos (`Contact`) vinculados (`PartyAddress`, `PartyContact`).
- [ ] Activación en compañía (`CompanyParty`).

### Formulario de Cliente
- [ ] Completar `cliente_nuevo.html` con campos equivalentes al proveedor.
- [ ] Gestión de direcciones y contactos.
- [ ] Activación en compañía.

### Grupos de Clientes y Proveedores
- [ ] Implementar modelo `PartyGroup` para agrupar terceros.
- [ ] CRUD de grupos en la interfaz.

---

## Inventario (Servicios de Valoración)

### StockLedgerEntry automático
- [ ] Ampliar pruebas de reversión para validar `is_return`, stock negativo y ajustes de bin.

### StockValuationLayer (costo por capa)
- [ ] Implementar método FIFO: crear capa con `qty` y `incoming_rate` en cada entrada; consumir capas más antiguas en salidas.
- [ ] Implementar método Moving Average: recalcular costo promedio en cada entrada; usar promedio vigente en salidas.
- [ ] Método de valuación inmutable una vez hay transacciones en el ítem.

### Stock Reconciliation
- [ ] Tipos: ajuste de cantidad, ajuste de valuación.

---

## Conciliación de Compras

- [ ] Definir cuenta de ajuste y flujo contable para diferencias de precio conciliación de compras.

---

## Catálogo base y cuentas predeterminadas
- [ ] Crear migración formal para instalaciones existentes cuando el proyecto adopte un flujo de migraciones.

## Smart Select Framework

- [ ] Migrar progresivamente selects de catálogos grandes/contextuales en compras, ventas, bancos, inventario y GL.
- [ ] Añadir cobertura específica por cada formulario migrado para confirmar filtros de compañía, permisos y valores guardados.

## Smoke Test de Rutas
- [ ] Extender la cobertura a rutas dinámicas con parámetros mínimos por módulo.
- [ ] Definir whitelist explícita para endpoints API cuyo 400/404 sin query params es comportamiento esperado y no error de routing.

---

## Impuestos y Cargos

### Cargos Adicionales (Flete, Seguro, Aduana)
- [ ] Si capitalizable: prorratear costo entre ítems según regla (por cantidad, por valor, por peso/volumen).
- [ ] Actualizar `StockValuationLayer` para ítems inventariables capitalizables.

---

## Precios

### Sugerencia de Precio en Documentos
- [ ] El precio sugerido es editable en el documento.
- [ ] Tolerancia de precio por rol y tipo de documento.
- [ ] Documentos con precios fuera de tolerancia requieren aprobación por workflow.

---

## Multi-Ledger
- [ ] Implementar `LedgerMappingRule`: diferencias de cuenta/monto entre libros.
- [ ] UI para gestión de reglas de mapeo entre libros.
- [ ] Reporte de Mayor General por libro.

---

## Dimensiones Analíticas
- [ ] UI de `DimensionType` (lista, nuevo, activar/inactivar).
- [ ] UI de `DimensionValue` (lista y CRUD por tipo).
- [ ] Captura de dimensiones en formularios de documentos operativos.
- [ ] Generación de `GLEntryDimension` al contabilizar.
- [ ] Reporte de saldos por dimensión (cost_center, unit, project, dimensiones personalizadas).

---

## Revalorización Cambiaria
- [ ] UI para ejecutar `ExchangeRevaluation` por compañía y fecha.
- [ ] Seleccionar cuentas en moneda extranjera a revalorizar.
- [ ] Calcular diferencia entre tipo de cambio original y actual.
- [ ] Generar `GLEntry` de pérdida/ganancia cambiaria.
- [ ] Registrar `ExchangeRevaluationItem` con detalle por cuenta.
- [ ] Reporte de diferencias cambiarias históricas.

---

## Cierre de Período
- [ ] UI de ejecución de `PeriodCloseRun` para un período contable.
- [ ] Implementar checks (`PeriodCloseCheck`):
  - [ ] GL balanceado en el período.
  - [ ] AR/AP conciliado.
  - [ ] GI/IR conciliado.
  - [ ] Revaluaciones aplicadas.
  - [ ] Inventario consistente.
- [ ] Marcar `AccountingPeriod.is_closed = True` al completar cierre.
- [ ] Validar en todos los endpoints de posting que el período esté abierto.
- [ ] Control de reapertura autorizada con bitácora.

---

## Reportes Financieros

### Contabilidad
- [ ] Saldos por dimensión (cost_center, unit, project).
- [ ] Revalorización cambiaria histórica.
- [ ] Anticipos de clientes/proveedores (aplicado, pendiente, remanente).
- [ ] Jerarquías expandibles y subtotales visuales implementadas para Balanza de Comprobación, Balance General y Estado de Resultado; pendiente completar drill-down universal en todos los reportes y casos de navegación.
- [ ] Exportación avanzada consistente (agrupaciones, formato monetario y totales configurables en todos los reportes).

### Compras
- [ ] Órdenes de compra pendientes (por proveedor, ítem, estado).

### Ventas
- [ ] Órdenes de venta pendientes (por cliente, ítem, estado).
- [ ] Entregas pendientes de facturar.

### Inventario
- [ ] Ítems bajo mínimo de existencia.

---

## Administración y Setup

### Wizard de Configuración Inicial
- [ ] Flujo guiado para crear compañía → catálogo de cuentas → libro contable → año fiscal → período → usuario admin → series → cuentas por defecto.
- [ ] Creación automática de series por defecto al crear una compañía.
- [ ] Validación de que los pasos mínimos están completados antes de permitir transacciones.

### Administración de Usuarios y Roles
- [ ] CRUD de usuarios en `admin/`.
- [ ] CRUD de roles y asignación de permisos por módulo.
- [ ] Asignación de roles a usuarios.
- [ ] Pantalla de usuarios activos con sus roles.

### Gestión de Contactos y Direcciones
- [ ] CRUD de `Contact` y `Address` como entidades independientes.
- [ ] Vinculación a terceros via `PartyContact` y `PartyAddress`.

### Módulo de Colaboración (Cloud Mode)
- [ ] UI de `Comment` por documento.
- [ ] `CommentMention` con notificación.
- [ ] `Assignment` de tareas a usuarios.
- [ ] `Workflow` de aprobación: definición de estados y transiciones.
- [ ] `WorkflowInstance` activa por documento pendiente.
- [ ] Historial de acciones de workflow (`WorkflowActionLog`).

### Gestión de Archivos
- [ ] Subida de archivos (`File`) con vinculación a documentos vía `FileAttachment`.
- [ ] Vista de adjuntos por documento.

### Auditoría
- [ ] Registro automático de `AuditLog` (before/after JSON) en cambios de documentos sensibles.
- [ ] Pantalla de consulta de auditoría por documento y por usuario.

---

## Mejoras de UI Transversales

### Formularios y Listas
- [ ] Agregar botón "Nuevo [Documento]" en todas las listas (documentado en FIXME para varios módulos).
- [ ] Agregar campo `company` visible en todos los formularios de alta.
- [ ] Agregar campo `currency` en todos los documentos transaccionales.
- [ ] Agregar selector de `naming_series` dinámico (filtra por compañía seleccionada sin recargar página).
- [ ] Agregar campo `posting_date` obligatorio en todos los documentos.
- [ ] Botón "Actualizar Elementos" reutilizable para poblar líneas desde documentos fuente.

### Flujo Documental desde UI
- [ ] Botón "Crear desde..." en la vista de detalle de cada documento:
  - Orden de Compra → Recepción / Factura / Anticipo.
  - Recepción → Factura de Compra.
  - Factura de Compra → Pago / Nota de Crédito / Nota de Débito.
  - Orden de Venta → Nota de Entrega / Factura.
  - Nota de Entrega → Factura de Venta.
  - Factura de Venta → Pago / Nota de Crédito / Nota de Débito.
- [ ] Modal de selección de líneas pendientes con qty_ordered, qty_delivered, qty_billed, qty_pending.
- [ ] Control de no duplicar líneas ya consumidas.

### Correcciones Pendientes (FIXME.md)
- [ ] `/cash_management/payment/new`: separar Transferencia Interna como transacción independiente.
- [ ] `/cash_management/payment/new`: completar lógica de asociación a factura según `aging.md`.
- [ ] `/cash_management/cash`: mapear todos los registros definidos en `registros_overview.md`.
- [ ] `/accounting/`: mapear todos los tipos de documentos (no solo comprobantes).
- [ ] `/accounting/gl/new`: conectar completamente con el backend.
- [ ] `/cash_management/bank/list`: agregar botón "Nuevo Banco" y enlace a detalle.
- [ ] `/buying/supplier/list`: agregar botón "Nuevo Proveedor".
- [ ] `/buying/supplier/new`: reparar completamente el formulario.
- [ ] `/buying/purchase-order/list`: agregar botón "Nueva Orden de Compra".
- [ ] `/buying/purchase-order/new`: corregir errores de HTML e incompletud.
- [ ] `/buying/purchase-receipt/list`: compartir vista entre almacén y compras.
- [ ] `/buying/purchase-receipt/new`: corregir errores de HTML.
- [ ] `/buying/purchase-invoice/list`: agregar botón "Nueva Factura".
- [ ] `/buying/purchase-invoice/new`: corregir errores de HTML.

---

## Series e Identificadores (Mejoras)

- [ ] Endpoint dinámico para refrescar lista de series al cambiar compañía (sin recargar formulario completo).
- [ ] Migrar administración legacy (`Serie`) a CRUD completo de `NamingSeries` + `Sequence` + `SeriesSequenceMap`.
- [ ] Soporte de múltiples secuencias por serie con condiciones JSON.
- [ ] Bootstrap automático de series al crear compañía (JE, SI, PI, PE, SE).
- [ ] Aplicar lógica de identificadores en flujo contable manual (asientos desde UI de GL).
- [ ] UI para `SeriesExternalCounterMap` (asociar serie a contador externo).
- [ ] UI para `ExternalNumberUsage` (consultar números externos ya utilizados).

---

## Pendiente (iteración 2026-05-10 — reportes financieros)

- [ ] Implementar persistencia real de vistas guardadas (filtros/columnas/orden/agrupaciones por usuario).
- [ ] Implementar selector funcional de columnas (actualmente botón placeholder en UI).
- [ ] Implementar agrupación dinámica y jerarquías expandibles reales para Balanza, Estado de Resultado y Balance General.
- [ ] Completar drill-down universal (cuenta → movimiento → comprobante) con validación de permisos.
- [ ] Mejorar exportación avanzada de Excel (hoja de filtros, formato monetario por columna, auto ancho, metadata de usuario/fecha).
- [ ] Reforzar seguridad de reportes por compañía/libro en filtros, exportación y drill-down.

## Pendiente tras iteración 2026-05-10 (reportes financieros)

- [ ] Endurecer autorización por compañía/libro con matriz explícita usuario↔compañía/libro (modelo dedicado; hoy se reforzó acceso de módulo y validación de compañía/ledger).
- [ ] Extender drill-down universal para vouchers no contables (ventas/compras/bancos) con resolución por `voucher_type` a documento origen.
- [ ] Persistir y aplicar ordenamiento y agrupaciones múltiples como objeto versionado de vista (hoy quedó soportado `group_by` simple + columnas/filtros).
- [ ] Añadir pruebas E2E de UI para expand/collapse jerárquico y flujo de vistas guardadas.
