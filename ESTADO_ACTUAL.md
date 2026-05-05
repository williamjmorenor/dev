# ESTADO ACTUAL DEL PROYECTO

**Fecha de análisis:** 2026-05-05  
**Rama analizada:** `copilot/analyze-modules-and-create-docs`

---

## ¿Qué implementa el proyecto?

**Cacao Accounting** es un sistema contable de código abierto orientado a pequeñas y medianas empresas. Implementa los flujos de negocio centrales de contabilidad:

- **R2R (Record to Report):** captura de transacciones → mayor general → reportes.
- **S2P (Source to Pay):** solicitud de compra → orden → recepción → factura de proveedor → pago.
- **O2C (Order to Cash):** cotización → orden de venta → entrega → factura de cliente → cobro.
- **Inventario:** movimientos físicos (entradas, salidas, transferencias), valoración (FIFO / Promedio Móvil), lotes y series.

El sistema está diseñado con soporte nativo para:
- **Multi-compañía:** toda transacción tiene campo `company`.
- **Multi-ledger:** libros paralelos (Fiscal, NIIF, etc.).
- **Multimoneda real:** documentos en cualquier moneda, GL guarda moneda base y original.
- **Múltiples períodos contables** con apertura/cierre.
- **Series e identificadores** desacoplados y auditables.
- **Flujo documental trazable** (upstream/downstream entre documentos).

---

## ¿Dónde lo implementa?

| Capa | Ubicación | Descripción |
|---|---|---|
| Paquete principal | `cacao_accounting/` | Raíz de la aplicación Flask |
| Esquema de base de datos | `cacao_accounting/database/__init__.py` | Todos los modelos SQLAlchemy (2041 líneas, ~90 tablas) |
| Módulo Contabilidad | `cacao_accounting/contabilidad/` | Blueprint `contabilidad` |
| Submódulo GL | `cacao_accounting/contabilidad/gl/` | Blueprint `gl` (Comprobante Contable) |
| Módulo Compras | `cacao_accounting/compras/` | Blueprint `compras` |
| Módulo Ventas | `cacao_accounting/ventas/` | Blueprint `ventas` |
| Módulo Bancos | `cacao_accounting/bancos/` | Blueprint `bancos` |
| Módulo Inventario | `cacao_accounting/inventario/` | Blueprint `inventario` |
| Módulo Administración | `cacao_accounting/admin/` | Blueprint `admin` |
| Módulo Autenticación | `cacao_accounting/auth/` | Blueprint `auth` |
| API REST | `cacao_accounting/api/` | Blueprint `api` |
| Flujo documental | `cacao_accounting/document_flow/` | Trazabilidad entre documentos |
| Identificadores | `cacao_accounting/document_identifiers.py` | Series y numeración automática |
| Posting contable | `cacao_accounting/contabilidad/posting.py` | Servicio de contabilización GL, AR/AP, bancos e inventario |
| Conciliación GR/IR | `cacao_accounting/compras/gr_ir_service.py` | Servicio de matching por líneas entre recepciones y facturas |
| Conciliación bancaria | `cacao_accounting/bancos/reconciliation_service.py` | Servicio de matching parcial contra pagos y GL |
| Reportes operativos | `cacao_accounting/reportes/` | Subledger, aging, Kardex y reconciliaciones |
| Datos demo | `cacao_accounting/datos/` | Datos de carga inicial y desarrollo |
| Pruebas | `tests/` | Suite de pruebas con pytest |

---

## ¿Qué hace cada módulo?

### `auth` — Autenticación y Seguridad
- Login/logout de usuarios.
- Control de sesión con Flask-Login.
- Sistema RBAC: roles (`Roles`), permisos por módulo (`RolesAccess`), asignación a usuarios (`RolesUser`).
- Decoradores `@login_required`, `@modulo_activo`, `@verifica_acceso` para proteger rutas.
- Modelos en DB: `User`, `Roles`, `RolesAccess`, `RolesUser`, `Modules`.

### `admin` — Administración General
- Dashboard de administración.
- Lista y activación/desactivación de módulos del sistema.
- Administración básica de usuarios, roles, asignación de roles y permisos por módulo.
- Pendiente: configuración funcional de compañía, cuentas por defecto, workflows y auditoría operativa.

### `contabilidad` — Módulo Contable Central
Rutas implementadas:
- **Entidades (compañías):** CRUD completo (lista, ver, crear, editar, eliminar, activar/inactivar, predeterminar).
- **Unidades de negocio:** lista, ver, crear, eliminar.
- **Libros contables:** lista, ver, crear, eliminar.
- **Catálogo de cuentas:** lista y detalle de cuenta por entidad.
- **Centros de costo:** lista y detalle.
- **Proyectos:** lista.
- **Tipo de cambio:** lista.
- **Períodos contables:** lista.
- **Monedas:** lista.
- **Comprobante Contable (Journal Entry):** rutas de nuevo, ver y editar (backend desconectado del GL).
- **Series (legacy `Serie`):** lista y crear.
- **NamingSeries:** lista, nueva, toggle-default, toggle-active.
- **Contadores externos (`ExternalCounter`):** lista, nuevo, ajuste con auditoría, log de auditoría.
- **Sub-blueprint GL:** lista (`/gl/list`) y nuevo (`/gl/new`), sin posting real al GL.
- **Servicio de posting operativo:** `contabilidad/posting.py` genera `GLEntry` desde facturas, pagos y movimientos de inventario.

El posting contable actual:
- Aprueba y contabiliza documentos operativos con `submit_document`.
- Cancela documentos con reversos append-only mediante `cancel_document`.
- Es idempotente: rechaza documentos ya contabilizados para evitar duplicar `GLEntry`.
- Genera entradas por cada `Book` activo de la compañía y valida balance por libro.
- Usa `PartyAccount`, `ItemAccount` y `CompanyDefaultAccount` para resolver cuentas.
- Mantiene trazabilidad con `voucher_type`, `voucher_id`, `document_no`, `naming_series_id`, tercero y período.

Pendiente en contabilidad:
- El comprobante contable manual (`ComprobanteContable` / UI de GL) sigue sin generar `GLEntry`.
- No hay reportes financieros construidos sobre `GLEntry`.
- Dimensiones adicionales y reglas diferenciales entre libros aún no están conectadas al posting.
- Impuestos/cargos ya tienen configuración admin, cálculo de plantilla y posting GL básico en facturas de compra/venta.

Modelos en DB disponibles (implementados pero sin UI completa):  
`GLEntry`, `ComprobanteContable`, `ComprobanteContableDetalle`, `GLEntryDimension`, `DimensionType`, `DimensionValue`, `LedgerMappingRule`, `ExchangeRevaluation`, `ExchangeRevaluationItem`, `PeriodCloseRun`, `PeriodCloseCheck`, `ItemAccount`, `PartyAccount`, `CompanyDefaultAccount`, `Tax`, `TaxTemplate`, `TaxTemplateItem`, `AccountBalanceSnapshot`.

### `compras` — Compras (Source to Pay)
Rutas implementadas con CRUD + submit/cancel:
- **Proveedor:** lista, nuevo, ver.
- **Solicitud de Compra (`PurchaseRequest`):** lista, nuevo, ver.
- **Solicitud de Cotización (`PurchaseQuotation`):** lista, nuevo, ver.
- **Cotización de Proveedor (`SupplierQuotation`):** lista, nueva, ver.
- **Comparativo de Ofertas:** lista y vista por RFQ.
- **Orden de Compra (`PurchaseOrder`):** lista, nuevo, ver, submit, cancel.
- **Recepción de Mercancía (`PurchaseReceipt`):** lista, nueva, ver, submit, cancel. El submit ahora genera `StockLedgerEntry` y GL hacia GR/IR, y el cancelado usa reversos append-only de stock y GL.
- **Factura de Proveedor (`PurchaseInvoice`):** lista, nueva, ver, submit, cancel.
- **Nota de Débito / Nota de Crédito / Devolución:** listas existentes; creación no implementada.
- **GR/IR por líneas:** servicio y vista `/buying/gr-ir` para saldos pendientes por ítem/bodega/UOM; las facturas contra recepción crean detalle en `GRIRReconciliationItem`.
- **Impuestos/cargos:** `PurchaseInvoice` puede usar `TaxTemplate`; el posting genera GL de impuestos/cargos aditivos o deductivos.
- **Flujo documental:** integrado con `document_flow` y `document_identifiers` para relaciones y numeración.
- **Posting:** al aprobar factura de compra se genera GL por libro activo:
  - AP por proveedor (`party_type="supplier"`).
  - Gasto directo o GR/IR cuando la factura viene de recepción.
  - Impuestos/cargos desde plantilla.
  - Reverso contable al cancelar.

### `ventas` — Ventas (Order to Cash)
Rutas implementadas con CRUD + submit/cancel:
- **Cliente:** lista, nuevo, ver.
- **Pedido de Venta (`SalesRequest`):** lista, nuevo, ver.
- **Cotización (`SalesQuotation`):** lista, nueva, ver.
- **Orden de Venta (`SalesOrder`):** lista, nueva, ver, submit, cancel.
- **Nota de Entrega (`DeliveryNote`):** lista, nueva, ver, submit, cancel.
- **Factura de Venta (`SalesInvoice`):** lista, nueva, ver, submit, cancel.
- **Nota de Débito:** lista existente; creación disponible en `/sales-invoice/new?document_type=sales_debit_note`.
- **Devolución:** lista existente; creación disponible mediante `is_return=True` en la factura de venta.
- **Nota de Crédito:** ruta de lista alias `/sales-invoice/credit-note/list` y creación disponible en `/sales-invoice/new?document_type=sales_credit_note`; pendiente validar flujo de reversión y `outstanding_amount`.
- **Posting:** al aprobar factura de venta se genera GL por libro activo:
  - AR por cliente (`party_type="customer"`).
  - Ingreso por líneas.
  - Impuestos/cargos desde plantilla.
  - Reverso contable al cancelar.

### `bancos` — Tesorería y Pagos
Rutas implementadas:
- **Banco:** lista, nuevo, ver.
- **Cuenta Bancaria:** lista, nueva, ver.
- **Pago (`PaymentEntry`):** lista, nuevo, ver, submit y cancel para cobros/pagos de terceros.
- **Transferencia interna (`PaymentEntry` con `payment_type=internal_transfer`):** listado dedicado separado de pagos/cobros.
- **Posting de pagos:** genera banco/caja contra AR/AP o banco origen/destino; puede usar cuenta explícita o `BankAccount.gl_account_id`.
- **PaymentReference:** se registra al crear pagos desde facturas y el saldo vivo ahora se calcula dinámicamente a partir de las referencias de pago; soporta cálculo temporal por `allocation_date` para consistencia histórica.
- **Transacciones Bancarias:** lista general, lista de notas de débito bancario y lista de notas de crédito bancario.
- **Nota de Débito/Crédito Bancario:** creación manual implementada sobre `BankTransaction` (retiro/deposito).
- **Reconciliación bancaria completa:** modelos extendidos, servicio de sugerencias y matching parcial contra `PaymentEntry` o `GLEntry`; vista mínima en `/cash_management/bank-reconciliation`.
- **Importación de extractos:** UI CSV con preview, mapeo de columnas y detección de duplicados.
- **Reglas de matching:** modelo y UI mínima para reglas por compañía/cuenta, texto de referencia, prioridad y tolerancias.

### `inventario` — Inventario y Almacén
Rutas implementadas:
- **Artículo (`Item`):** lista, nuevo, ver.
- **Unidad de Medida (`UOM`):** lista, nueva, ver.
- **Bodega (`Warehouse`):** lista, nueva, ver.
- **Entrada de Almacén (`StockEntry`):** lista, nueva, ver, submit, cancel. Soporta material_receipt, material_issue, material_transfer, stock_adjustment, stock_reconciliation, adjustment_positive y adjustment_negative.
- **Filtros por tipo:** rutas diferenciadas para recibo de material, emisión y transferencia.
- **Stock Ledger:** al aprobar `StockEntry` se genera `StockLedgerEntry`, se actualiza `StockBin` y se crea `StockValuationLayer`.
- **Posting GL de inventario:** material receipt genera Inventario vs GR/IR; material issue genera gasto/costo vs Inventario; transferencias generan stock ledger sin GL.
- **Recepción/Entrega directa:** el submit de `PurchaseReceipt` y `DeliveryNote` ahora genera `StockLedgerEntry` y GL de forma directa (GR/IR y COGS respectivamente), y el cancelado guarda reversos append-only en stock y GL.
- **Servicios de inventario:** conversión UOM por ítem, validación obligatoria de lote/serial, actualización de seriales y reconstrucción de `StockBin` desde `StockLedgerEntry`.

Modelos en DB disponibles pero sin funcionalidad completa:  
`StockBalanceSnapshot`. `Batch` y `SerialNumber` ya tienen validación operativa básica; `StockLedgerEntry`, `StockBin` y `StockValuationLayer` ya están conectados para `StockEntry`, `PurchaseReceipt` y `DeliveryNote`, pero falta gestión visual completa de lotes/seriales y recalculo histórico avanzado.

### `reportes` — Reportes operativos
- Blueprint global con rutas HTML:
  - `/reports/subledger`
  - `/reports/aging`
  - `/reports/kardex`
  - `/reports/reconciliations`
  - `/reports/purchases-by-supplier`
  - `/reports/purchases-by-item`
  - `/reports/sales-by-customer`
  - `/reports/sales-by-item`
  - `/reports/gross-margin`
  - `/reports/stock-balance`
  - `/reports/inventory-valuation`
  - `/reports/batches`
  - `/reports/serials`
- Servicios derivados desde GL/documentos, `PaymentReference`, `StockLedgerEntry` y reconciliaciones.
- Estado actual: reportes operativos MVP con filtros básicos y totales; pendiente pulir UX, exportación y reportes financieros formales.

### `document_flow` — Flujo Documental
- Registro de relaciones entre documentos (`DocumentRelation`).
- Estado de líneas de flujo (`DocumentLineFlowState`).
- API para consultar árbol de documentos, resumen de upstream/downstream y lista filtrada.
- Actualización de cachés de flujo al submit de documentos.
- Servicios: `create_document_relation`, `refresh_source_caches_for_target`, `revert_relations_for_target`.

### `document_identifiers` — Series e Identificadores
- Resolución de `NamingSeries` por tipo documental y compañía.
- Generación de identificadores con tokens: `*YYYY*`, `*YY*`, `*MM*`, `*MMM*`, `*DD*`, `*COMP*`.
- Bootstrap automático de serie + secuencia cuando no existe configuración.
- Validación de período contable cerrado por `posting_date`.
- Soporte de contadores externos (`ExternalCounter`) con auditoría.
- Log de identificadores generados (`GeneratedIdentifierLog`).

### `api` — API REST
- Items de documentos operativos (PO, SO, Receipt, Invoice, etc.).
- Endpoints de flujo documental (tree, summary, pending-lines, create-target, close-line/document).

---

## ¿Qué módulos son los más relevantes?

| Prioridad | Módulo / Archivo | Razón |
|---|---|---|
| 🔴 Crítico | `cacao_accounting/database/__init__.py` | Esquema completo; toda la lógica parte de aquí. |
| 🔴 Crítico | `cacao_accounting/contabilidad/posting.py` | Servicio de posting operativo para GL, AR/AP, bancos y stock. |
| 🔴 Crítico | `cacao_accounting/compras/__init__.py` | Módulo más completo operacionalmente (47 KB, flujo S2P). |
| 🔴 Crítico | `cacao_accounting/ventas/__init__.py` | Flujo O2C; crítico para ingresos. |
| 🟠 Importante | `cacao_accounting/contabilidad/__init__.py` | Corazón contable; falta conectar el Journal Entry manual y reportes. |
| 🟠 Importante | `cacao_accounting/document_identifiers.py` | Identificación transversal de documentos. |
| 🟠 Importante | `cacao_accounting/document_flow/` | Trazabilidad documental upstream/downstream. |
| 🟡 Relevante | `cacao_accounting/bancos/__init__.py` | Pagos y tesorería; lógica de reconciliación incompleta. |
| 🟡 Relevante | `cacao_accounting/inventario/__init__.py` | Control físico de stock; valuación básica conectada para StockEntry. |
| 🟢 Soporte | `cacao_accounting/auth/` | Seguridad y acceso; base estable. |
| 🟢 Soporte | `cacao_accounting/api/__init__.py` | Endpoints REST para operaciones de formularios. |

---

## ¿Qué archivos requieren atención?

### 🔴 Atención urgente

| Archivo | Problema |
|---|---|
| `cacao_accounting/contabilidad/gl/__init__.py` | Solo renderiza vistas; completamente desconectado del backend. El formulario de comprobante contable no genera GL entries. |
| `cacao_accounting/contabilidad/__init__.py` | Rutas de Journal Entry (nuevo/ver/editar) existen pero no están conectadas al servicio de posting. |
| `cacao_accounting/compras/templates/compras/proveedor_nuevo.html` | Formulario de nuevo proveedor operativo en el código; requiere verificación de datos y mejoras de UX tras la documentación FIXME. |
| `cacao_accounting/compras/templates/compras/factura_compra_nuevo.html` | Documentado con "incompleto y con errores de HTML" en FIXME.md. |
| `cacao_accounting/compras/templates/compras/recepcion_nuevo.html` | Documentado como "incompleto y con errores de HTML" en FIXME.md. |

### 🟠 Atención prioritaria

| Archivo | Problema |
|---|---|
| `cacao_accounting/ventas/__init__.py` | No existe ruta de creación de nota de crédito de cliente (el gap más relevante del módulo). |
| `cacao_accounting/bancos/__init__.py` | Conciliación, importación CSV y reglas de matching MVP implementadas; falta UX avanzada y automatización de diferencias. |
| `cacao_accounting/inventario/__init__.py` | StockEntry ya genera ledger/bin/valuation; existen UOM/lote/serial/rebuild/reportes MVP; faltan gestión visual avanzada y valoración histórica profunda. |
| `cacao_accounting/admin/__init__.py` | Ya gestiona usuarios/roles/permisos; falta setup funcional de compañía y cuentas por defecto. |
| `FIXME.md` | Bitácora de errores conocidos con ~18 items sin resolver; debe procesarse sistemáticamente. |

### 🟡 Atención en siguiente iteración

| Archivo | Problema |
|---|---|
| `cacao_accounting/database/__init__.py` | Modelos `PeriodCloseRun`, `ExchangeRevaluation`, `GRIRReconciliation`, `Comment`, `Assignment`, `Workflow*`, `File` no tienen UI ni servicio conectado. |
| `cacao_accounting/contabilidad/auxiliares.py` | Funciones auxiliares que pueden requerir actualización al implementar posting real. |
| `cacao_accounting/datos/dev/data.py` | Datos demo pueden no reflejar el estado más reciente del esquema. |

---

## Resumen de estado por módulo

| Módulo | Modelos DB | Rutas CRUD | Posting/Servicios | Reportes |
|---|---|---|---|---|
| Auth | ✅ Completo | ✅ Login/Logout | ✅ RBAC activo | ❌ Sin reportes |
| Admin | ✅ Completo | 🟡 Usuarios/roles/módulos | 🟡 Servicios básicos | ❌ Sin reportes |
| Contabilidad | ✅ Completo | 🟡 Parcial | 🟡 Posting operativo; JE manual pendiente | ❌ Sin reportes |
| Compras | ✅ Completo | 🟡 Parcial | ✅ Factura de compra genera GL + impuestos/cargos | 🟡 MVP |
| Ventas | ✅ Completo | 🟡 Parcial | ✅ Factura de venta genera GL + impuestos/cargos | 🟡 MVP |
| Bancos | ✅ Completo | 🟡 Parcial | ✅ Pagos, notas, conciliación e importación MVP | 🟡 MVP |
| Inventario | ✅ Completo | 🟡 Parcial | ✅ SLE/Bin/Valuation/GL + UOM/lote/serial MVP | 🟡 MVP |
| API | N/A | 🟡 Parcial | ✅ Flow endpoints | N/A |
| Document Flow | ✅ Completo | ✅ API completa | ✅ Relaciones activas | ❌ Sin reportes |
| Identificadores | ✅ Completo | ✅ NamingSeries UI | ✅ Generación activa | 🟡 Solo log |
