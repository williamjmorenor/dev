# PENDIENTE — Cacao Accounting

**Fecha de análisis:** 2026-05-04  
**Base:** definición de módulos en `modulos/` y estado actual del código.

Este documento registra todo lo que está pendiente de implementar para cumplir la especificación completa de los módulos del sistema.

---

## 🔴 BLOQUE 1 — Posting Contable (Core crítico)

El sistema tiene modelos de base de datos y rutas de UI pero **ningún documento genera `GLEntry` automáticamente** al ser confirmado (submit). Este es el bloque más crítico y bloquea toda la funcionalidad contable real.

### 1.1 Contabilización de Factura de Venta (`SalesInvoice`)
- [ ] Al hacer submit, generar `GLEntry` por cada libro activo (`Book`):
  - Débito: Cuentas por cobrar (AR) — `PartyAccount` del cliente.
  - Crédito: Ingreso de ventas — cuenta de ingreso del ítem.
  - Líneas de impuesto: según `TaxTemplate` aplicada.
  - Costo de ventas (COGS) si el ítem es inventariable.
- [ ] Respetar `posting_date` y período abierto.
- [ ] Registrar `voucher_type` y `voucher_id` en cada `GLEntry`.
- [ ] Calcular `outstanding_amount` inicial = `total_amount`.
- [ ] Soportar multimoneda: guardar moneda base y moneda original con `exchange_rate`.

### 1.2 Contabilización de Factura de Compra (`PurchaseInvoice`)
- [ ] Al hacer submit, generar `GLEntry` por cada libro activo:
  - Débito: gasto, inventario o impuesto acreditable según tipo de ítem.
  - Crédito: Cuentas por pagar (AP) — `PartyAccount` del proveedor.
  - Si hay recepción previa: descarga cuenta GI/IR.
- [ ] Calcular `outstanding_amount` inicial.
- [ ] Soportar multimoneda.

### 1.3 Contabilización de Pago (`PaymentEntry`)
- [ ] Al hacer submit, generar `GLEntry`:
  - Cobro: Débito banco/caja, Crédito AR.
  - Pago: Débito AP, Crédito banco/caja.
  - Transferencia interna: Débito cuenta destino, Crédito cuenta origen.
- [ ] Procesar `PaymentReference` y reducir `outstanding_amount` en documentos aplicados.
- [ ] Calcular `allocation_date` para cada referencia.

### 1.4 Contabilización de Nota de Entrega / Recepción de Mercancía (Inventario)
- [ ] Al hacer submit de `DeliveryNote`: generar `StockLedgerEntry` (salida) + `GLEntry` de COGS.
- [ ] Al hacer submit de `PurchaseReceipt`: generar `StockLedgerEntry` (entrada) + `GLEntry` GI/IR.
- [ ] Actualizar `StockBin` (saldo actual) tras cada movimiento.
- [ ] Registrar `StockValuationLayer` con costo según método (FIFO / Moving Average).

### 1.5 Contabilización de Entrada de Almacén (`StockEntry`)
- [ ] Al hacer submit: generar `StockLedgerEntry` según propósito (receipt, issue, transfer, adjustment).
- [ ] Actualizar `StockBin`.
- [ ] Generar `GLEntry` con cuenta de inventario vs contrapartida según propósito.
- [ ] Registrar `StockValuationLayer`.

### 1.6 Comprobante Contable Manual (Journal Entry)
- [ ] Implementar servicio de posting completo en `contabilidad/gl/`.
- [ ] Validar balance (`SUM(debit) == SUM(credit)`) por libro.
- [ ] Generar `GLEntry` por cada línea y por cada libro activo.
- [ ] Soportar tipos: estándar, apertura, nota de crédito, nota de débito, contra asiento, ajuste, reversión.
- [ ] Conectar rutas existentes (`/gl/new`, `/gl/list`, `/journal/new`, `/journal/<id>`) con el servicio real.

---

## 🟠 BLOQUE 2 — Cuentas por Cobrar / Cuentas por Pagar (AR/AP)

### 2.1 Saldo pendiente (`outstanding_amount`)
- [ ] Implementar cálculo dinámico de `outstanding_amount` para `SalesInvoice` y `PurchaseInvoice`.
- [ ] Fórmula: `outstanding_amount = total_amount - SUM(allocated_amount de PaymentReference)`.
- [ ] El campo persistido es cache; el cálculo dinámico es la fuente de verdad.
- [ ] Consistencia temporal: filtrar por `posting_date` y `allocation_date`.

### 2.2 Aplicación de pagos a facturas
- [ ] Permitir desde el formulario de pago seleccionar una o varias facturas pendientes del mismo tercero.
- [ ] Registrar `PaymentReference` con `allocated_amount` y `allocation_date`.
- [ ] Actualizar `outstanding_amount` en las facturas aplicadas.
- [ ] Soportar pago parcial (un pago → una factura parcial).
- [ ] Soportar pago multiple (un pago → múltiples facturas).
- [ ] Soportar aplicación cruzada (múltiples pagos → una factura).

### 2.3 Anticipos (totales y parciales)
- [ ] Registrar anticipo de cliente como pasivo (cuenta de anticipo de cliente).
- [ ] Registrar anticipo a proveedor como activo (cuenta de anticipo a proveedor).
- [ ] Aplicar anticipo contra factura mediante `PaymentReference` con `allocation_date`.
- [ ] Soportar aplicación parcial: el remanente queda como saldo a favor.
- [ ] Aplicar un anticipo a múltiples facturas del mismo tercero.
- [ ] Configuración de cuentas contables de anticipos por compañía en `CompanyDefaultAccount`.

### 2.4 Aging AR/AP
- [ ] Implementar cálculo de aging por buckets (0-30, 31-60, 61-90, +90 días) basado en `posting_date`.
- [ ] Reproducible históricamente: calcular aging para cualquier fecha pasada.
- [ ] Vista de aging por cliente (AR) y por proveedor (AP).

---

## 🟠 BLOQUE 3 — Documentos de Corrección

### 3.1 Nota de Crédito de Venta (Sales Credit Note)
- [ ] Crear ruta, formulario y template `ventas_factura_venta_nota_credito_nueva`.
- [ ] Campos: `is_return=True`, `reversal_of` → ID de factura origen.
- [ ] Generar GL inverso al de la factura original.
- [ ] Reducir `outstanding_amount` de la factura referenciada.
- [ ] Incluir lista de notas de crédito (actualmente **no existe** la ruta de lista de nota de crédito de ventas).

### 3.2 Nota de Débito de Venta (Sales Debit Note)
- [ ] Crear ruta, formulario y template de nota de débito de venta.
- [ ] Generar GL adicional al de la factura original.
- [ ] Incrementar `outstanding_amount` de la factura referenciada.

### 3.3 Devolución de Venta (Sales Return)
- [ ] Implementar retorno de mercancía: `DeliveryNote` con `is_return=True`.
- [ ] Revertir `StockLedgerEntry` y `StockValuationLayer`.
- [ ] Generar `SalesInvoice` de crédito asociada.

### 3.4 Nota de Crédito de Compra (Purchase Credit Note)
- [ ] Ruta de creación desde factura de proveedor.
- [ ] `PurchaseInvoice` con `is_return=True` o vía nota de crédito de proveedor.
- [ ] Revertir impacto GL y ajustar `outstanding_amount` AP.

### 3.5 Nota de Débito de Compra (Purchase Debit Note)
- [ ] Ruta de creación desde factura de proveedor.
- [ ] Incrementar `outstanding_amount` AP.

### 3.6 Devolución de Compra (Purchase Return)
- [ ] `PurchaseReceipt` con `is_return=True`.
- [ ] Revertir `StockLedgerEntry`.
- [ ] Generar nota de crédito de proveedor asociada.

### 3.7 Reversión de Comprobante Contable
- [ ] Servicio de reversión que genera asiento espejo.
- [ ] Poblar `reversal_of` y `is_reversal` en el asiento generado.
- [ ] Trazabilidad bidireccional entre asiento original y reverso.

---

## 🟠 BLOQUE 4 — Proveedor y Cliente (formularios completos)

### 4.1 Formulario de Proveedor
- [ ] Corregir y completar `proveedor_nuevo.html` (documentado en FIXME como "totalmente infuncional").
- [ ] Campos requeridos: razón social, identificación fiscal, moneda, condiciones de pago, cuentas AP.
- [ ] Gestión de direcciones (`Address`) y contactos (`Contact`) vinculados (`PartyAddress`, `PartyContact`).
- [ ] Activación en compañía (`CompanyParty`).

### 4.2 Formulario de Cliente
- [ ] Completar `cliente_nuevo.html` con campos equivalentes al proveedor.
- [ ] Gestión de direcciones y contactos.
- [ ] Activación en compañía.

### 4.3 Grupos de Clientes y Proveedores
- [ ] Implementar modelo `PartyGroup` para agrupar terceros.
- [ ] CRUD de grupos en la interfaz.

---

## 🟡 BLOQUE 5 — Inventario (Servicios de Valoración)

### 5.1 StockLedgerEntry automático
- [ ] Generar `StockLedgerEntry` al submit de: `StockEntry`, `PurchaseReceipt`, `DeliveryNote`.
- [ ] Campos obligatorios: `item_code`, `warehouse`, `posting_date`, `actual_qty`, `qty_after_transaction`, `incoming_rate`, `valuation_rate`, `voucher_type`, `voucher_id`.
- [ ] Política de reversión: crear nuevo SLE inverso (nunca eliminar).

### 5.2 StockBin (cache de saldo actual)
- [ ] Actualizar `StockBin` en cada `StockLedgerEntry` generado.
- [ ] Campo: `actual_qty`, `valuation_rate`, `last_updated`.
- [ ] Servicio de recalculo de `StockBin` desde `StockLedgerEntry`.

### 5.3 StockValuationLayer (costo por capa)
- [ ] Implementar método FIFO: crear capa con `qty` y `incoming_rate` en cada entrada; consumir capas más antiguas en salidas.
- [ ] Implementar método Moving Average: recalcular costo promedio en cada entrada; usar promedio vigente en salidas.
- [ ] Método de valuación inmutable una vez hay transacciones en el ítem.

### 5.4 Lotes (Batch)
- [ ] Requerir selección de lote en recepciones/salidas cuando `item.has_batch = True`.
- [ ] Validar existencia del lote en el almacén antes de salida.
- [ ] Reporte de lotes por estado y vencimiento.

### 5.5 Números de Serie (SerialNumber)
- [ ] Requerir selección de serial en recepciones/salidas cuando `item.has_serial_no = True`.
- [ ] Actualizar `serial_status` y `warehouse` en cada movimiento.
- [ ] Reporte de seriales por estado y ubicación.

### 5.6 Stock Reconciliation
- [ ] CRUD completo de conciliación física de inventario.
- [ ] Tipos: ajuste de cantidad, ajuste de valuación.
- [ ] Generar `StockLedgerEntry` de ajuste positivo/negativo con motivo obligatorio.

### 5.7 Conversiones de UOM
- [ ] Aplicar `ItemUOMConversion` al ingresar cantidad en unidad alternativa.
- [ ] `StockLedgerEntry` siempre en unidad base.

---

## 🟡 BLOQUE 6 — GI/IR (Goods Receipt / Invoice Receipt)

- [ ] Definir cuenta GI/IR por compañía en `CompanyDefaultAccount`.
- [ ] Al submit de `PurchaseReceipt`: acreditar GI/IR (no AP).
- [ ] Al submit de `PurchaseInvoice` con recepción previa: debitar GI/IR, acreditar AP.
- [ ] Implementar UI y servicio de `GRIRReconciliation`.
- [ ] Reporte de GI/IR pendiente de reconciliar por proveedor/ítem/documento.

---

## 🟡 BLOQUE 7 — Impuestos y Cargos

### 7.1 UI de Gestión de Impuestos
- [ ] CRUD de `Tax` (definición de impuesto: nombre, tasa, cuenta contable, tipo).
- [ ] CRUD de `TaxTemplate` (plantilla: nombre, tipo buying/selling).
- [ ] CRUD de `TaxTemplateItem` (líneas: impuesto, tasa, tipo cálculo, comportamiento).

### 7.2 Aplicación en Documentos
- [ ] Al crear factura, aplicar `TaxTemplate` seleccionada y calcular monto de cada línea de impuesto.
- [ ] Soportar cálculo fijo (monto absoluto) y porcentual.
- [ ] Soportar comportamiento aditivo (suma al total) y deductivo (resta del total).
- [ ] Base de cálculo configurable: neto de línea, neto documento, base previa.

### 7.3 Cargos Adicionales (Flete, Seguro, Aduana)
- [ ] Campo `capitalizable` en líneas de cargo de compra.
- [ ] Si capitalizable: prorratear costo entre ítems según regla (por cantidad, por valor, por peso/volumen).
- [ ] Si no capitalizable: registrar como gasto directo en cuenta contable definida.
- [ ] Actualizar `StockValuationLayer` para ítems inventariables capitalizables.

---

## 🟡 BLOQUE 8 — Precios

### 8.1 UI de Listas de Precios
- [ ] CRUD de `PriceList` (nombre, tipo buying/selling, moneda, activa).
- [ ] CRUD de `ItemPrice` (ítem, precio, moneda, fecha inicio/fin de vigencia).

### 8.2 Sugerencia de Precio en Documentos
- [ ] Al agregar ítem a documento de compra/venta, sugerir precio desde `ItemPrice` activo.
- [ ] El precio sugerido es editable en el documento.
- [ ] Tolerancia de precio por rol y tipo de documento.
- [ ] Documentos con precios fuera de tolerancia requieren aprobación por workflow.

---

## 🟡 BLOQUE 9 — Multi-Ledger

- [ ] Implementar lógica de posting multi-libro: al contabilizar cualquier documento, generar `GLEntry` por cada `Book` activo de la compañía.
- [ ] Implementar `LedgerMappingRule`: diferencias de cuenta/monto entre libros.
- [ ] UI para gestión de reglas de mapeo entre libros.
- [ ] Reporte de Mayor General por libro.

---

## 🟡 BLOQUE 10 — Dimensiones Analíticas

- [ ] UI de `DimensionType` (lista, nuevo, activar/inactivar).
- [ ] UI de `DimensionValue` (lista y CRUD por tipo).
- [ ] Captura de dimensiones en formularios de documentos operativos.
- [ ] Generación de `GLEntryDimension` al contabilizar.
- [ ] Reporte de saldos por dimensión (cost_center, unit, project, dimensiones personalizadas).

---

## 🟡 BLOQUE 11 — Revalorización Cambiaria

- [ ] UI para ejecutar `ExchangeRevaluation` por compañía y fecha.
- [ ] Seleccionar cuentas en moneda extranjera a revalorizar.
- [ ] Calcular diferencia entre tipo de cambio original y actual.
- [ ] Generar `GLEntry` de pérdida/ganancia cambiaria.
- [ ] Registrar `ExchangeRevaluationItem` con detalle por cuenta.
- [ ] Reporte de diferencias cambiarias históricas.

---

## 🟡 BLOQUE 12 — Cierre de Período

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

## 🟡 BLOQUE 13 — Reconciliación Bancaria

- [ ] UI de importación/registro manual de `BankTransaction` (extracto bancario).
- [ ] Herramienta de reconciliación: vincular `BankTransaction` con `PaymentEntry`.
- [ ] Ajustes de diferencia vía Journal Entry.
- [ ] Reporte de transacciones no reconciliadas.
- [ ] Separar "Transferencia Interna" como documento independiente (documentado en FIXME).

---

## 🟢 BLOQUE 14 — Reportes Financieros

### Contabilidad
- [ ] Balance General (por compañía, libro, fecha, moneda).
- [ ] Estado de Resultados (por compañía, libro y período).
- [ ] Mayor General (por cuenta y tercero).
- [ ] Libro Diario (asientos cronológicos).
- [ ] Balanza de Comprobación (saldos por cuenta).
- [ ] Aging AR/AP (saldos por antigüedad).
- [ ] Saldos por dimensión (cost_center, unit, project).
- [ ] Revalorización cambiaria histórica.
- [ ] Anticipos de clientes/proveedores (aplicado, pendiente, remanente).

### Compras
- [ ] Órdenes de compra pendientes (por proveedor, ítem, estado).
- [ ] Recepciones vs Facturas (estado GI/IR por orden).
- [ ] Cuentas por pagar (saldo pendiente por proveedor).
- [ ] Aging AP (vencimientos por bucket).
- [ ] Compras por proveedor (monto total por período).
- [ ] Compras por ítem (consumo y precio promedio).

### Ventas
- [ ] Órdenes de venta pendientes (por cliente, ítem, estado).
- [ ] Entregas pendientes de facturar.
- [ ] Cuentas por cobrar (saldo pendiente por cliente).
- [ ] Aging AR (vencimientos por bucket 30/60/90/+90 días).
- [ ] Ventas por cliente (monto total por período).
- [ ] Ventas por ítem (unidades y valor).
- [ ] Margen bruto (ingreso − COGS por ítem/cliente/período).

### Inventario
- [ ] Stock Balance (existencia actual por ítem+almacén).
- [ ] Stock Ledger (historial de movimientos por ítem).
- [ ] Valoración de inventario (costo total por almacén).
- [ ] Movimientos por período (entradas y salidas por fecha).
- [ ] Ítems bajo mínimo de existencia.
- [ ] Reporte de lotes (estado y vencimiento).
- [ ] Reporte de seriales (estado y ubicación).

---

## 🟢 BLOQUE 15 — Administración y Setup

### 15.1 Wizard de Configuración Inicial
- [ ] Flujo guiado para crear compañía → catálogo de cuentas → libro contable → año fiscal → período → usuario admin → series → cuentas por defecto.
- [ ] Creación automática de series por defecto al crear una compañía.
- [ ] Validación de que los pasos mínimos están completados antes de permitir transacciones.

### 15.2 Administración de Usuarios y Roles
- [ ] CRUD de usuarios en `admin/`.
- [ ] CRUD de roles y asignación de permisos por módulo.
- [ ] Asignación de roles a usuarios.
- [ ] Pantalla de usuarios activos con sus roles.

### 15.3 Cuentas por Defecto de Compañía
- [ ] UI para configurar `CompanyDefaultAccount` (AR, AP, bancos, descuentos, impuestos, GI/IR, anticipos).

### 15.4 Gestión de Contactos y Direcciones
- [ ] CRUD de `Contact` y `Address` como entidades independientes.
- [ ] Vinculación a terceros via `PartyContact` y `PartyAddress`.

### 15.5 Módulo de Colaboración (Cloud Mode)
- [ ] UI de `Comment` por documento.
- [ ] `CommentMention` con notificación.
- [ ] `Assignment` de tareas a usuarios.
- [ ] `Workflow` de aprobación: definición de estados y transiciones.
- [ ] `WorkflowInstance` activa por documento pendiente.
- [ ] Historial de acciones de workflow (`WorkflowActionLog`).

### 15.6 Gestión de Archivos
- [ ] Subida de archivos (`File`) con vinculación a documentos vía `FileAttachment`.
- [ ] Vista de adjuntos por documento.

### 15.7 Auditoría
- [ ] Registro automático de `AuditLog` (before/after JSON) en cambios de documentos sensibles.
- [ ] Pantalla de consulta de auditoría por documento y por usuario.

---

## 🟢 BLOQUE 16 — Mejoras de UI Transversales

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

## 🔵 BLOQUE 17 — Series e Identificadores (Mejoras)

- [ ] Endpoint dinámico para refrescar lista de series al cambiar compañía (sin recargar formulario completo).
- [ ] Migrar administración legacy (`Serie`) a CRUD completo de `NamingSeries` + `Sequence` + `SeriesSequenceMap`.
- [ ] Soporte de múltiples secuencias por serie con condiciones JSON.
- [ ] Bootstrap automático de series al crear compañía (JE, SI, PI, PE, SE).
- [ ] Aplicar lógica de identificadores en flujo contable manual (asientos desde UI de GL).
- [ ] UI para `SeriesExternalCounterMap` (asociar serie a contador externo).
- [ ] UI para `ExternalNumberUsage` (consultar números externos ya utilizados).

---

## Prioridad de Implementación Recomendada

| Orden | Bloque | Impacto |
|---|---|---|
| 1 | Bloque 1 — Posting Contable | Desbloquea toda la funcionalidad financiera real |
| 2 | Bloque 2 — AR/AP y Pagos | Completa el ciclo de cobros y pagos |
| 3 | Bloque 3 — Documentos de Corrección | Completa el flujo no lineal (correcciones) |
| 4 | Bloque 4 — Formularios Proveedor/Cliente | Corrige problemas críticos documentados en FIXME |
| 5 | Bloque 5 — Inventario Valoración | Completa control físico y financiero del stock |
| 6 | Bloque 6 — GI/IR | Completa separación entre recepción y facturación |
| 7 | Bloque 7 — Impuestos y Cargos | Necesario para facturación completa |
| 8 | Bloque 8 — Precios | Complementa ciclo de compra/venta |
| 9 | Bloque 9 — Multi-Ledger | Habilita contabilidad paralela |
| 10 | Bloque 10 — Dimensiones | Habilita reportes analíticos |
| 11 | Bloque 11 — Revalorización | Cierre contable multimoneda |
| 12 | Bloque 12 — Cierre de Período | Completa el ciclo R2R |
| 13 | Bloque 13 — Reconciliación Bancaria | Completa módulo de bancos |
| 14 | Bloque 14 — Reportes | Habilita toma de decisiones |
| 15 | Bloque 15 — Setup/Admin | Completa la configuración inicial |
| 16 | Bloque 16 — Mejoras UI | Mejora la experiencia de usuario |
| 17 | Bloque 17 — Series (mejoras) | Consolida el subsistema de identificadores |
