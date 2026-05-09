# ESTADO ACTUAL DEL PROYECTO

**Fecha de análisis:** 2026-05-07
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
| Conciliación de Compras | `cacao_accounting/compras/purchase_reconciliation_service.py` | Motor de matching 2-way/3-way, eventos económicos, tolerancias configurables por compañía y panel operativo |
| Conciliación bancaria | `cacao_accounting/bancos/reconciliation_service.py` | Servicio de matching parcial contra pagos y GL |
| Reportes contables y operativos | `cacao_accounting/reportes/` | Framework financiero base (Detalle Movimiento, Balanza, Estado de Resultado, Balance General) + reportes operativos |
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
- CRUD de cuentas por defecto por compañía en `/settings/default-accounts`, con validación de compañía, tipo de cuenta compatible y selección asistida Smart Select filtrada por compañía/tipo.
- Asistente de configuración inicial con selección de catálogo predefinido o catálogo en blanco; al elegir catálogo en blanco se deshabilita el selector de archivo, y los catálogos predefinidos muestran alias de usuario (`Predeterminado - ES`, `Default - EN`) manteniendo el filename como valor técnico.
- Pendiente: configuración funcional avanzada de compañía, workflows y auditoría operativa.

### `api` — API REST y Selección Asistida
- Items de documentos operativos (PO, SO, Receipt, Invoice, etc.).
- Endpoints de flujo documental (tree, summary, pending-lines, create-target, close-line/document).
- Endpoint autenticado `/api/search-select` para campos Smart Select, con registry explícito de doctypes (`company`, `account`, `book`, `cost_center`, `unit`, `project`, `party`, `customer`, `supplier`, `item`, `warehouse`, `bank_account`, `naming_series`), filtros permitidos y límites de resultados.
- Endpoint autenticado `/api/form-preferences/<form_key>/<view_key>` para persistir configuración de columnas por usuario en backend.

### `contabilidad` — Módulo Contable Central
Rutas implementadas:
- **Entidades (compañías):** CRUD completo (lista, ver, crear, editar, eliminar, activar/inactivar, predeterminar).
- **Unidades de negocio:** lista, ver, crear, eliminar.
- **Libros contables:** CRUD operativo con moneda por libro, estado activo/inactivo y libro primario.
- **Catálogo de cuentas:** lista y detalle de cuenta por entidad.
- **Centros de costo:** lista y detalle.
- **Proyectos:** lista.
- **Proyectos:** lista, crear, editar y eliminar con endpoint operativo `contabilidad.proyectos` restituido para navegación del módulo.
- **Tipo de cambio:** lista.
- **Períodos contables:** lista.
- **Monedas:** lista.
- **Comprobante Contable (Journal Entry):** nuevo formulario backend-first en `/journal/new`, guarda borrador en `ComprobanteContable` + `ComprobanteContableDetalle`, permite ver `/journal/<id>` y contabilizar con `/journal/<id>/submit`. El formulario permite seleccionar por checkboxes uno o varios libros activos de la compañía; si todos quedan marcados, el posting afecta todos los libros activos. La moneda del comprobante usa SmartSelect (`doctype=currency`).
- **Edición de borradores de Comprobante Contable:** `/journal/edit/<id>` rehidrata cabecera, libros y líneas del borrador para modificarlo antes de contabilizar.
- **Validaciones del comprobante manual:** exige balance, líneas de un solo lado, centro de costo para cuentas de gasto y moneda única por comprobante. El modal avanzado ya no expone moneda de línea ni cuenta bancaria; mantiene captura de anticipo y dimensiones contables.
- **Estados operativos del comprobante manual:** soporte de `draft` -> `rejected` sin impacto en ledger y `submitted` -> `cancelled` con reversa contable append-only.
- **Vista de detalle del comprobante manual:** rediseñada en patrón visual nativo Cacao (`ca-card`/`ca-table`), mostrando alias de usuario (`User.user`) y doble modo de detalle de línea (panel + modal).
- **Política UX de legibilidad (Journal Entry):** en UI se prioriza formato `codigo - descripcion` para cuenta contable, centro de costos, libros y moneda; los códigos puros se reservan al payload técnico.
- **Duplicación de comprobantes manuales:** disponible para estados `draft`, `rejected` y `submitted`, creando siempre un nuevo comprobante en estado `draft` mediante acción dedicada en vista de detalle.
- **Edición post-duplicación/reversión:** `Duplicar` y `Revertir` abren directamente el formulario de edición del nuevo borrador para permitir ajuste de fecha de contabilización y serie en el periodo destino.
- **Revertir comprobante manual:** variante de duplicación que invierte débitos y créditos de cada línea y genera borrador editable para registrar la reversión contable con nueva fecha/serie.
- **Numeración diferida en duplicar/revertir:** los borradores creados por estas acciones nacen sin `document_no`; el identificador se asigna al primer guardado de edición (o como fallback al submit) usando la fecha/serie activa del borrador.
- **Contabilizar con caja/banco en Journal Entry:** el asiento manual ahora puede postear cuentas `cash` y `bank`; los errores de contabilización también se muestran con flash global en la UI.
- **Series (legacy `Serie`):** lista y crear.
- **NamingSeries:** lista, nueva, toggle-default, toggle-active.
- **Contadores externos (`ExternalCounter`):** lista, nuevo, ajuste con auditoría, log de auditoría.
- **Sub-blueprint GL:** lista (`/gl/list`) y nuevo (`/gl/new`) conservados como implementación legacy desacoplada.
- **Servicio de posting operativo:** `contabilidad/posting.py` genera `GLEntry` desde facturas, pagos y movimientos de inventario.
- **Catálogos contables predefinidos:** `contabilidad/ctas/catalogos/base_es.csv` incluye `account_type` en inglés y las cuentas requeridas por el motor; `base_es.json` mapea las cuentas predeterminadas para inicializar compañías completas. También se creó `contabilidad/ctas/catalogos/base_en.csv` con nombres de cuentas en inglés y su JSON compañero `base_en.json`.

El posting contable actual:
- Aprueba y contabiliza documentos operativos con `submit_document`.
- Cancela documentos con reversos append-only mediante `cancel_document`.
- Es idempotente: rechaza documentos ya contabilizados para evitar duplicar `GLEntry`.
- Genera entradas por cada `Book` activo de la compañía y valida balance por libro; en comprobante manual admite subset explícito de libros activos.
- Usa `PartyAccount`, `ItemAccount` y `CompanyDefaultAccount` para resolver cuentas.
- Valida `Accounts.account_type` de forma estricta antes de persistir `GLEntry`: cuentas sin tipo explícito permiten afectación libre; cuentas tipadas se restringen al módulo/origen autorizado.
- Mantiene trazabilidad con `voucher_type`, `voucher_id`, `document_no`, `naming_series_id`, tercero y período.
- Conserva en GL metadatos operativos de línea usados por conciliación/manual journal (`bank_account_id`, `is_advance`) cuando el comprobante manual los captura.

Pendiente en contabilidad:
- No hay reportes financieros construidos sobre `GLEntry`.
- Dimensiones adicionales y reglas diferenciales entre libros aún no están conectadas al posting.
- La edición del borrador ya existe y asigna identificador al primer guardado cuando el comprobante no estaba numerado; aún falta política formal para renumerar cuando ya existe `document_no` y luego se cambia serie/fecha.
- Impuestos/cargos ya tienen configuración admin, cálculo de plantilla y posting GL básico en facturas de compra/venta.
- `CompanyDefaultAccount` cubre efectivo, bancos, AR, AP, ingresos, gastos, inventario, COGS, ajustes de inventario, cuenta puente de compras, anticipos, diferencias bancarias, impuestos, redondeo, diferencias cambiarias, diferidos, descuentos de pago, resultado del período y resultados acumulados.

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
- **Recepción de Mercancía (`PurchaseReceipt`):** lista, nueva, ver, submit, cancel. El submit ahora genera `StockLedgerEntry` y GL hacia cuenta puente / conciliación de compras, y el cancelado usa reversos append-only de stock y GL.
- **Factura de Proveedor (`PurchaseInvoice`):** lista, nueva, ver, submit, cancel.
- **Nota de Débito / Nota de Crédito / Devolución:** listas existentes; creación no implementada.
- **Cuenta puente / conciliación de compras por líneas:** servicio y vista `/buying/purchase-reconciliation` para saldos pendientes por ítem/bodega/UOM; las facturas contra recepción usan líneas de recepción y las facturas 2-way contra OC usan líneas de orden sin mezclar referencias. El matching se evalúa por agregados de producto/UOM y las disputas no consumen cantidades disponibles.
- **Panel de conciliación de compras:** vista `/buying/purchase-reconciliation/panel` agrupada por orden de compra, con contadores de recepciones/facturas y badges de estado.
- **Impuestos/cargos:** `PurchaseInvoice` puede usar `TaxTemplate`; el posting genera GL de impuestos/cargos aditivos o deductivos.
- **Flujo documental:** integrado con `document_flow` y `document_identifiers` para relaciones y numeración.
- **Posting:** al aprobar factura de compra se genera GL por libro activo:
  - AP por proveedor (`party_type="supplier"`).
  - Gasto directo o cuenta puente / conciliación de compras cuando la factura viene de recepción.
  - Auto-conciliación configurable al aprobar facturas con recepción (3-way) o con orden de compra sin recepción (2-way).
  - La cuenta puente es configurable: si `bridge_account_required=False`, el flujo operativo de recepción mantiene stock ledger y eventos sin bloquear por falta de cuenta puente.
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
- **Posting GL de inventario:** material receipt genera Inventario vs cuenta puente / conciliación de compras; material issue genera gasto/costo vs Inventario; transferencias generan stock ledger sin GL.
- **Recepción/Entrega directa:** el submit de `PurchaseReceipt` y `DeliveryNote` ahora genera `StockLedgerEntry` y GL de forma directa (cuenta puente / conciliación de compras y COGS respectivamente), y el cancelado guarda reversos append-only en stock y GL.
- **Servicios de inventario:** conversión UOM por ítem, validación obligatoria de lote/serial, actualización de seriales y reconstrucción de `StockBin` desde `StockLedgerEntry`.

Modelos en DB disponibles pero sin funcionalidad completa:
`StockBalanceSnapshot`. `Batch` y `SerialNumber` ya tienen validación operativa básica; `StockLedgerEntry`, `StockBin` y `StockValuationLayer` ya están conectados para `StockEntry`, `PurchaseReceipt` y `DeliveryNote`, pero falta gestión visual completa de lotes/seriales y recalculo histórico avanzado.

### `reportes` — Reportes contables y operativos
- Blueprint global con rutas HTML:
  - `/reports/account-movement`
  - `/reports/trial-balance`
  - `/reports/income-statement`
  - `/reports/balance-sheet`
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
- Estado actual:
  - Reportes financieros base derivados del GL con filtros por compañía/libro/período, paginación server-side y exportación CSV/XLSX para Detalle de Movimiento.
  - Layout ERP de reportes (panel lateral de filtros + panel derecho de resultados con sticky headers y scroll independiente).
  - Reportes operativos MVP existentes se mantienen activos.
  - Pendiente: profundizar jerarquías/drill-down universal, exportación avanzada para todos los reportes y endurecimiento de seguridad por compañía/libro a nivel de permisos.

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

---

## ¿Qué módulos son los más relevantes?

| Prioridad | Módulo / Archivo | Razón |
|---|---|---|
| 🔴 Crítico | `cacao_accounting/database/__init__.py` | Esquema completo; toda la lógica parte de aquí. |
| 🔴 Crítico | `cacao_accounting/contabilidad/posting.py` | Servicio de posting operativo para GL, AR/AP, bancos y stock. |
| 🔴 Crítico | `cacao_accounting/compras/__init__.py` | Módulo más completo operacionalmente (47 KB, flujo S2P). |
| 🔴 Crítico | `cacao_accounting/ventas/__init__.py` | Flujo O2C; crítico para ingresos. |
| 🟠 Importante | `cacao_accounting/contabilidad/__init__.py` | Corazón contable; falta conectar el Journal Entry manual y reportes. |
| 🟠 Importante | `tests/test_routes_map.py` | Smoke test de `url_map` para detectar rutas estáticas rotas y errores de renderizado temprano. |
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
| `cacao_accounting/contabilidad/gl/__init__.py` | Implementación legacy desacoplada; no debe ser el punto de evolución del nuevo comprobante contable. |
| `cacao_accounting/contabilidad/templates/contabilidad/journal_nuevo.html` | Primer formulario transaccional modelo; requiere validación UX continua con usuarios contables antes de replicar el patrón. |
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
| `cacao_accounting/database/__init__.py` | Modelos `PeriodCloseRun`, `ExchangeRevaluation`, `PurchaseReconciliation`, `Comment`, `Assignment`, `Workflow*`, `File` no tienen UI ni servicio conectado. |
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

---

## Actualización 2026-05-09 — Smart Select (frontend)

- `smart-select.js` ahora separa preload general vs preload en foco:
  - `preload` sigue permitiendo carga por inicialización/cambio de filtros.
  - nuevo `preloadOnFocus` controla si el foco puede disparar carga y apertura del menú.
- Normalización de filtros fortalecida para evitar query params con objetos (`[object Object]`):
  - prioriza `value`, `id` o `code` cuando el filtro es objeto.
- Formulario de comprobante (`journal_nuevo.html`):
  - solo el campo **Compañía** mantiene apertura/carga por foco (`preloadOnFocus: true`).
- Cobertura JS agregada en `cacao_accounting/static/test/smart-select.test.js` con escenarios del bug.

## Actualización 2026-05-09 — Validación de comprobante contable

- Validación integral ejecutada contra build + lint + pytest del workflow CI local:
  - `python -m build`
  - `python -m flake8 cacao_accounting/`
  - `python -m ruff check cacao_accounting/`
  - `python -m mypy cacao_accounting/`
  - `CACAO_TEST=True LOGURU_LEVEL=WARNING SECRET_KEY=ASD123kljaAddS python -m pytest -v -s --exitfirst --slow=True`
- Resultado: **342 pruebas en verde** en el clone local.
- Ajustes realizados durante la validación:
  - el formulario de Journal Entry ya no permite tratar la moneda como atributo libre por línea; las líneas heredan la moneda del comprobante;
  - el modal avanzado fue simplificado para captura contable (sin moneda de línea ni cuenta bancaria) y mantiene anticipo/dimensiones;
  - el bootstrap de datos demo vuelve a preservar web/correo/teléfonos/fax para las vistas smoke de CI;
  - `smart-select.js` conserva las opciones pre-cargadas al auto-seleccionar una opción default y sus pruebas JS ya funcionan desde rutas reales del repositorio.
