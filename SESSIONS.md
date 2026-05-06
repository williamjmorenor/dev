# SESSIONS

## 2026-05-04 (diagnóstico del proyecto)

### Peticion del usuario
Analizar la definición de módulos del sistema (directorio `modulos/`) y generar dos documentos:
- `ESTADO_ACTUAL.md`: qué implementa el proyecto, dónde, qué hace cada módulo, los más relevantes y qué archivos requieren atención.
- `PENDIENTE.md`: todo lo pendiente para completar los módulos indicados.

### Plan implementado
1. Leer todos los archivos de definición de módulos en `modulos/` (contabilidad, compras, ventas, inventario, relaciones, setup) y archivos de contexto.
2. Inspeccionar el código fuente: modelos en `database/__init__.py`, rutas en cada módulo, templates, API, document_flow.
3. Revisar `FIXME.md` y `SESSIONS.md` anteriores para contexto de problemas conocidos.
4. Crear `ESTADO_ACTUAL.md` contestando: qué implementa, dónde, qué hace cada módulo, los más relevantes y archivos que requieren atención.
5. Crear `PENDIENTE.md` con todos los pendientes organizados en 17 bloques por prioridad.

### Resumen tecnico de cambios
- Creado `ESTADO_ACTUAL.md` (~250 líneas): diagnóstico completo del estado actual del proyecto.
  - Inventario de lo que implementa el proyecto (multi-compañía, multi-ledger, multimoneda, S2P, O2C, R2R).
  - Tabla por módulo: modelos DB, rutas CRUD, posting/servicios, reportes.
  - Archivos que requieren atención urgente y prioritaria.
- Creado `PENDIENTE.md` (~400 líneas): roadmap de pendientes dividido en 17 bloques.
  - Bloque 1: Posting Contable (core crítico — ningún documento genera GLEntry al submit).
  - Bloque 2: AR/AP, saldos outstanding, pagos y anticipos.
  - Bloque 3: Documentos de corrección (notas crédito/débito, devoluciones, reversión).
  - Bloques 4-17: formularios, inventario, GI/IR, impuestos, precios, multi-ledger, dimensiones, cierre, reportes, setup/admin.

### Hallazgos clave
- El modelo de base de datos es completo (~90 tablas en 2041 líneas).
- Ningún documento operativo genera `GLEntry` al ser confirmado (submit). Este es el gap más crítico.
- El módulo de ventas tiene ruta de lista y creación de nota de crédito de cliente; queda pendiente validar el flujo de reversión y el cálculo de `outstanding_amount`.
- El formulario de proveedor nuevo es operativo en el código, aunque documentado en FIXME y sujeto a mejoras de UX.
- `StockEntry` no genera `StockLedgerEntry` ni actualiza `StockBin` al hacer submit.
- La reconciliación bancaria, cierre de período y revalorización cambiaria tienen modelos pero sin UI ni servicio.

### Verificacion ejecutada
- Inspección completa de: modelos DB, rutas de todos los módulos, templates, API endpoints.
- Revisión de FIXME.md, SESSIONS.md previos, y todos los archivos de definición de módulos.

### Notas para siguiente iteracion
1. Priorizar implementación de posting contable (Bloque 1 de PENDIENTE.md).
2. Corregir formularios documentados como no funcionales en FIXME.md.
3. Implementar nota de crédito de venta (gap crítico en módulo ventas).

## 2026-05-05 (inicio de implementación)

### Peticion del usuario
Iniciar la implementación de los registros pendientes para Bancos, Compras, Ventas e Inventario, alineando la documentación con el estado real del código.

### Plan implementado
1. Verificar en el código la existencia de rutas de ventas para nota de crédito y nota de débito, y actualizar la documentación para reflejar su estado real.
2. Ajustar el backlog de pendientes para conservar solo las brechas reales: reconciliación bancaria, posteo directo de PurchaseReceipt/DeliveryNote, GL inverso en notas de crédito/débito y validaciones de `outstanding_amount`.
3. Registrar el punto de inicio de esta iteración en la bitácora de sesión.

### Resumen tecnico de cambios
- Actualizado `ESTADO_ACTUAL.md` para reflejar que la lista y creación de notas de crédito/débito de venta ya existen como rutas operativas.
- Ajustado `PENDIENTE.md` para no reportar como faltante la ruta de nota de crédito de ventas y el formulario de proveedor se marca como operativo básico sujeto a mejoras.
- Añadido registro de sesión en `SESSIONS.md` para documentar el inicio de implementación.

### Verificacion ejecutada
- Revisión de código en `cacao_accounting/ventas/__init__.py` para rutas `sales-credit-note` y `sales-debit-note`.
- Revisión de código en `cacao_accounting/compras/__init__.py` para el formulario de proveedor.
- Revisión de estado en documentación y backlog.

### Notas para siguiente iteracion
1. Completar la UI de reconciliación bancaria y la lógica de `outstanding_amount` dinámica.
2. Validar pruebas de regressión del flujo de notas de crédito/débito.
3. Confirmar pruebas de reversión contable y de stock para `PurchaseReceipt` y `DeliveryNote`.

## 2026-05-05 (cancelación de recepciones y entregas)

### Peticion del usuario
Agregar cancelación contable y de stock append-only a las recepciones de compra y notas de entrega, y actualizar la documentación de estado.

### Plan implementado
1. Extender `cancel_document` para que también revierta `StockLedgerEntry` de `PurchaseReceipt` y `DeliveryNote`.
2. Usar `cancel_document` en las rutas de cancelación de `PurchaseReceipt` y `DeliveryNote`.
3. Mantener la trazabilidad de `GL` y `StockBin` con reversos append-only.

### Resumen tecnico de cambios
- `cacao_accounting/contabilidad/posting.py` ahora cancela movimientos de stock asociados a `PurchaseReceipt`, `DeliveryNote` y `StockEntry`.
- `cacao_accounting/compras/__init__.py` usa `cancel_document` al cancelar `PurchaseReceipt`.
- `cacao_accounting/ventas/__init__.py` usa `cancel_document` al cancelar `DeliveryNote`.
- El backlog se actualizó para reflejar que la reversión append-only está implementada y requiere pruebas adicionales.

### Verificacion ejecutada
- Compilación de los archivos afectados.
- Revisión de rutas de cancelación y del motor de posting.

### Notas para siguiente iteracion
1. Implementar pruebas de regresión para cancelaciones contables de notas de entrega y recepciones.
2. Avanzar en la UI de reconciliación bancaria.
3. Verificar el impacto de cancelaciones en `document_flow` y `outstanding_amount`.

## 2026-05-05 (posteo directo de recepciones y entregas)

### Peticion del usuario
Implementar el posting contable directo para recepciones de compra y notas de entrega, manteniendo la documentación de estado actualizada.

### Plan implementado
1. Añadir soporte en `cacao_accounting/contabilidad/posting.py` para procesar `PurchaseReceipt` y `DeliveryNote` como documentos operativos contables.
2. Generar `StockLedgerEntry`, `StockBin` y `StockValuationLayer` al aprobar recepciones y entregas.
3. Generar GL de GR/IR en `PurchaseReceipt` y GL de COGS en `DeliveryNote`.
4. Actualizar los submit handlers de `cacao_accounting/compras/__init__.py` y `cacao_accounting/ventas/__init__.py` para usar `submit_document`.

### Resumen tecnico de cambios
- `cacao_accounting/contabilidad/posting.py` ahora soporta `PurchaseReceipt` y `DeliveryNote` en `post_document_to_gl`.
- `PurchaseReceipt` crea movimientos de inventario con impacto en `StockLedgerEntry`, `StockBin` y `StockValuationLayer`, y registra GL hacia GR/IR.
- `DeliveryNote` crea movimientos de inventario de salida y registra GL de costo de ventas contra inventario.
- Los submit handlers ahora ejecutan `submit_document` y gestionan errores de posting.

### Verificacion ejecutada
- Compilación de `cacao_accounting/contabilidad/posting.py`, `cacao_accounting/compras/__init__.py` y `cacao_accounting/ventas/__init__.py`.
- Confirmación de que los nuevos tipos de documento son reconocidos por el motor de posting.

### Notas para siguiente iteracion
1. Ajustar la reversión de `PurchaseReceipt` y `DeliveryNote` para que generen SLE reversos append-only.
2. Implementar los reportes de stock y la validación FIFO / Moving Average.
3. Avanzar en la UI de reconciliación bancaria.

## 2026-05-05 (finalización Fase 3/4)

### Peticion del usuario
Finalizar la etapa Fase 3/4 con notas de crédito/débito, devoluciones, GR/IR y validaciones formales de período/cierre.

### Plan implementado
1. Añadir validación de período cerrado en el motor de cancelación para evitar reversos en períodos cerrados.
2. Registrar conciliación GR/IR al contabilizar facturas de compra asociadas a recepciones de compra.
3. Eliminar registros de conciliación GR/IR cuando se cancela la factura de compra correspondiente.
4. Añadir pruebas de notas de crédito de compra, reconciliación GR/IR y bloqueo de cancelación en período cerrado.

### Resumen tecnico de cambios
- Actualizada `cacao_accounting/contabilidad/posting.py` con:
  - conversión de errores de período cerrado a `PostingError` en el flujo de contabilización,
  - reconciliación GR/IR registrada en `GRIRReconciliation` para facturas de compra con recepción asociada,
  - limpieza de conciliaciones GR/IR en la cancelación de factura de compra.
- Añadida cobertura de pruebas en `tests/test_07posting_engine.py` para:
  - cálculo y registro de GR/IR,
  - notas de crédito de compra balanceadas,
  - bloqueo de cancelación en períodos cerrados.

### Verificacion ejecutada
- `pytest tests/test_07posting_engine.py -q` -> 17 passed.
- `python -m py_compile cacao_accounting/contabilidad/posting.py tests/test_07posting_engine.py` -> sin errores de sintaxis.

## 2026-05-05 (ledger core y notas bancarias)

### Peticion del usuario
Completar la implementación de ledger core con posting de comprobante contable manual, consumo FIFO/MA de capas de inventario y GL para notas bancarias.

### Plan implementado
1. Añadir soporte de `BankTransaction` en `cacao_accounting/contabilidad/posting.py` y procesar notas bancarias en GL.
2. Implementar consumo de capas de valuación de inventario FIFO/Moving Average en `cacao_accounting/contabilidad/posting.py`.
3. Ajustar `DeliveryNote` para usar costo real de inventario como base de COGS.
4. Consolidar el cálculo de `outstanding_amount` temporal en `cacao_accounting/document_flow/service.py`.
5. Agregar conciliación bancaria MVP en `cacao_accounting/bancos/__init__.py` con estado `is_reconciled` y registro de conciliaciones.

### Resumen tecnico de cambios
- `cacao_accounting/contabilidad/posting.py`: soporte completo de `BankTransaction` en `post_document_to_gl`; consumo de capas de valuación negado para salidas; fallback de costo cuando no hay capas registradas; `DeliveryNote` usa costo real para GL de COGS.
- `cacao_accounting/document_flow/service.py`: `compute_outstanding_amount` ahora usa fecha actual por defecto para consultas temporales.
- `cacao_accounting/bancos/__init__.py`: notas bancarias ahora generan GL al crearse y existe endpoint para marcar transacciones como conciliadas.

### Verificacion ejecutada
- `ruff check cacao_accounting/contabilidad/posting.py cacao_accounting/bancos/__init__.py cacao_accounting/document_flow/service.py`
- `pytest -q tests/test_07posting_engine.py -q`

### Notas para siguiente iteracion
1. Añadir pruebas unitarias para reconciliación bancaria y notas bancarias en `tests/`.
2. Extender Fase 3 con notas de crédito/débito de compras y ventas.
3. Completar validación de período contable para operaciones de pago y cierre.

## 2026-05-05 (posteo de comprobantes contables manuales)

### Peticion del usuario
Agregar soporte de contabilización para comprobantes contables manuales (`ComprobanteContable`) y dejar listo el motor de posting para entradas de diario.

### Plan implementado
1. Extender `cacao_accounting/contabilidad/posting.py` para reconocer `ComprobanteContable` en `post_document_to_gl`.
2. Implementar la traducción de líneas del comprobante (`ComprobanteContableDetalle`) a `GLEntry` balanceadas.
3. Soportar `entity`/`date` como alias de `company`/`posting_date` para documentos de diario manual.
4. Añadir prueba de regresión en `tests/test_07posting_engine.py` para asegurar que un comprobante manual produce entradas GL balanceadas.

### Resumen tecnico de cambios
- `post_comprobante_contable` ahora prepara entradas de débito/crédito desde `ComprobanteContableDetalle`.
- El motor de posting valida que el comprobante está balanceado y que cada línea tiene cuenta y monto válidos.
- Se resolvió la cuenta contable por código usando `Accounts(entity, code)` y se trasladó la metadata de dimensiones y tercero a `GLEntry`.

### Verificacion ejecutada
- `pytest -q tests/test_07posting_engine.py -q`
- `ruff check cacao_accounting/contabilidad/posting.py tests/test_07posting_engine.py`

### Notas para siguiente iteracion
1. Conectar la UI de comprobantes contables al servicio de posting manual.
2. Añadir manejo de referencias cruzadas y validaciones de periodos fiscales en formularios de GL.
3. Verificar la implicación de `ComprobanteContable` en la lógica de reversos y conciliación contable.

## 2026-05-05 (outstanding dinámico y pruebas de inventario)

### Peticion del usuario
Calcular el saldo vivo de AR/AP desde las referencias de pago y agregar cobertura de pruebas para las cancelaciones de inventario.

### Plan implementado
1. Agregar `compute_outstanding_amount` en `cacao_accounting/document_flow/service.py`.
2. Usar el cálculo dinámico en el módulo de bancos y en el estado de documento `document_flow.status`.
3. Añadir pruebas que validan la reversión de `PurchaseReceipt` y el cálculo dinámico de `outstanding_amount`.

### Resumen tecnico de cambios
- `cacao_accounting/document_flow/service.py` ahora calcula el saldo vivo de facturas con `PaymentReference` en lugar de depender únicamente del cache.
- `cacao_accounting/bancos/__init__.py` usa el saldo dinámico en los formularios de pago.
- `cacao_accounting/document_flow/status.py` usa el saldo dinámico para el estado de pagos de facturas.
- Se agregaron pruebas de cancelación para `PurchaseReceipt` y de cálculo de saldo vivo.

### Verificacion ejecutada
- Revisión de código y pruebas unitarias específicas de posting y AR/AP.

### Notas para siguiente iteracion
1. Confirmar la consistencia temporal de `outstanding_amount` con filtros por `posting_date` y `allocation_date`.
2. Avanzar en la UI de reconciliación bancaria.
3. Extender pruebas para `DeliveryNote` y notas de crédito de venta.

## 2026-05-04

### Peticion del usuario
Priorizar la correccion del subsistema de series e identificadores y comenzar la implementacion.

### Plan implementado
1. Crear una capa transversal para resolver identificadores documentales por tipo documental y compania.
2. Integrar validacion de periodo contable cerrado usando `posting_date`.
3. Conectar la asignacion de `document_no` en las rutas de creacion de documentos de compras, ventas, bancos e inventario.
4. Exponer en formularios y templates el selector de serie (`naming_series`) para permitir seleccion manual con preseleccion automatica por compania.
5. Garantizar operatividad inicial sin configuracion previa mediante bootstrap automatico de serie + secuencia por compania/tipo documental.
6. Validar la implementacion con pruebas de vistas/acciones y pruebas de esquema/helpers.

### Resumen tecnico de cambios
- Nuevo modulo: `cacao_accounting/document_identifiers.py`
  - Validacion de `posting_date`.
  - Validacion de periodos cerrados (`AccountingPeriod.is_closed`).
  - Seleccion de serie por compania + tipo documental.
  - Creacion automatica de serie y secuencia por defecto cuando no existe configuracion.
  - Asignacion de `document_no` + `naming_series_id`.
- Actualizacion helper de series:
  - `resolve_naming_series_prefix` ahora soporta token `*COMP*`.
  - `generate_identifier` ahora propaga `company` para resolver ese token.
- Integracion en rutas de alta:
  - Compras: orden, recepcion, factura.
  - Ventas: orden, entrega, factura.
  - Bancos: pago.
  - Inventario: entrada de almacen.
- Formularios actualizados con campo `naming_series`:
  - compras/forms.py, ventas/forms.py, bancos/forms.py, inventario/forms.py
- Templates de alta actualizados para mostrar selector de serie:
  - compras/*_nuevo.html
  - ventas/*_nuevo.html
  - bancos/pago_nuevo.html
  - inventario/entrada_nuevo.html

### Verificacion ejecutada
- `pytest -q tests/test_01vistas.py tests/test_03webactions.py` -> 8 passed
- `pytest -q tests/test_04database_schema.py -k "series or naming or sequence or identifier"` -> 36 passed

### Notas para siguiente iteracion
1. Implementar endpoint dinamico para refrescar series cuando cambia compania sin recargar pantalla.
2. Migrar administracion legacy de series (`Serie`) hacia CRUD completo de `NamingSeries` + `Sequence` + `SeriesSequenceMap`.
3. Aplicar la misma logica al flujo contable/manual que aun no genera documentos reales desde UI.

## 2026-05-04 (continuacion)

### Peticion del usuario
Alinear el flujo del modulo de compras con: Solicitud de Compra → Solicitud de Cotización → Cotización de Proveedor → Comparativo de Ofertas → Orden de Compra → Recepciones de Mercancía → Factura de Proveedor.

### Plan implementado
1. Registrar nuevos documentos base en el esquema de compras: `PurchaseRequest`, `PurchaseRequestItem`, `SupplierQuotation`, `SupplierQuotationItem`.
2. Extender el sistema de identificadores para reconocer `purchase_request` y `supplier_quotation`.
3. Agregar formularios, rutas y plantillas para el nuevo flujo de compras.
4. Preparar el menú de compras para exponer el orden de flujo propuesto y conectar RFQ con cotización de proveedor y comparativo de ofertas.

### Resumen tecnico de cambios
- En `cacao_accounting/database/__init__.py`:
  - Nuevos modelos para solicitud de compra y cotización de proveedor.
- En `cacao_accounting/document_identifiers.py`:
  - Nuevos prefijos de documento para `purchase_request` y `supplier_quotation`.
- En `cacao_accounting/compras/forms.py`:
  - Nuevos formularios `FormularioSolicitudCompra` y `FormularioCotizacionProveedor`.
- En `cacao_accounting/compras/__init__.py`:
  - Rutas nuevas para `purchase-request`, `supplier-quotation` y comparativo de ofertas.
  - Detalle de RFQ con enlaces a cotización de proveedor y comparativo.
- En `cacao_accounting/compras/templates/compras/`:
  - Nuevas plantillas para solicitud de compra, cotización de proveedor y comparativo de ofertas.

### Verificacion ejecutada
- Compilacion de Python de los archivos modificados.
- `pytest tests/test_03webactions.py -q --slow=True` -> 12 passed.

### Notas para siguiente iteracion
1. Revisar cobertura completa de UI y flujos de documento para compras.
2. Agregar soporte de transiciones directas de RFQ / comparativo a orden de compra.
3. Validar la creación de notas de crédito, débito y devoluciones desde factura de proveedor.

## 2026-05-04 (inventario)

### Peticion del usuario
Completar los registros del modulo de inventario siguiendo al flujo de compras.

### Plan implementado
1. Agregar rutas de creacion de entrada de almacén especificas por propósito: recepcion, salida y transferencia.
2. Permitir prellenar líneas desde una recepción de compra usando el API existente de líneas del documento origen.
3. Exponer botones "Nuevo" con propósito en los listados de inventario.
4. Conectar la recepción de compra aprobada con la creación de una entrada de almacén.

### Resumen tecnico de cambios
- En `cacao_accounting/inventario/__init__.py`:
  - Rutas nuevas para `/stock-entry/material-receipt/new`, `/stock-entry/material-issue/new` y `/stock-entry/material-transfer/new`.
  - Inferencia de propósito por ruta y título dinámico para el formulario de inventario.
  - Contexto de `source_api_url` para cargar líneas desde `purchase_receipt` o `delivery_note`.
  - Soporte de `new_url` en los listados para iniciar el registro con propósito.
- En `cacao_accounting/inventario/templates/inventario/entrada_nuevo.html`:
  - Migracion del macro de líneas para aceptar `source_api_url` y `source_label`.
- En `cacao_accounting/inventario/templates/inventario/entrada_lista.html`:
  - Botón "Nuevo" adaptativo según el tipo de listado.
- En `cacao_accounting/compras/templates/compras/recepcion.html`:
  - Enlace directo desde recepción de compra aprobada a la creación de una entrada de almacén.

### Verificacion ejecutada
- `pytest -q tests/test_03webactions.py --maxfail=1` -> 13 passed.

## 2026-05-04 (ventas)

### Peticion del usuario
Completar los registros del módulo de ventas replicando el flujo de compras: Pedido → Solicitud de Cotización → Cotización de Cliente → Orden de Venta → Nota de Entrega de Mercancía → Factura de Venta.

### Plan implementado
1. Agregar nuevo documento `SalesRequest` para pedidos de venta.
2. Extender `SalesQuotation` para poder derivar cotizaciones de un pedido de venta.
3. Permitir crear `SalesOrder` a partir de una cotización de venta.
4. Añadir soporte de notas de débito de venta y mantener las notas de crédito existentes.
5. Crear rutas, formularios y plantillas para los documentos faltantes en el flujo de ventas.

### Resumen tecnico de cambios
- En `cacao_accounting/database/__init__.py`:
  - Añadidos `SalesRequest` y `SalesRequestItem`.
  - Se enlaza `SalesQuotation.sales_request_id` y `SalesOrder.sales_quotation_id`.
  - Se agrega `SalesInvoice.document_type` para distinguir factura, nota de crédito y nota de débito.
- En `cacao_accounting/document_identifiers.py`:
  - Soporte de serie para `sales_request`.
- En `cacao_accounting/document_flow/registry.py`:
  - Permitido el flujo `sales_request -> sales_quotation` y `sales_quotation -> sales_order`.
- En `cacao_accounting/ventas/__init__.py`:
  - Nuevas rutas para `sales-request`.
  - Creación de cotizaciones desde pedidos y órdenes desde cotizaciones.
  - Lista de notas de débito de venta.
  - API de items para `sales-request` y `sales-quotation`.
- En `cacao_accounting/ventas/forms.py`:
  - Nuevo `FormularioPedidoVenta`.
- En `cacao_accounting/ventas/templates/ventas/`:
  - Nuevas plantillas para pedidos de venta.
  - Ajustes en las plantillas de cotización, orden y factura para soportar orígenes de documento.

### Verificacion ejecutada
- `pytest -q tests/test_03webactions.py -q` -> 16 passed.

### Notas para siguiente iteracion
1. Agregar una vista de lista dedicada para devoluciones de venta con impacto en inventario.
2. Extender la lógica de kardex para reflejar devoluciones de ventas y notas de crédito.
3. Revisar el flujo completo de cliente para incluir descuentos, anticipos y cobranza.

## 2026-05-04 (bancos y contabilidad)

### Peticion del usuario
Completar los registros pendientes de los módulos de bancos y contabilidad, asegurando que los documentos de pago y los comprobantes contables tengan flujo y CRUD consistentes.

### Plan implementado
1. Revisar y completar las rutas de bancos para banco, cuenta bancaria, pago y transacción bancaria.
2. Verificar la integración de `PaymentEntry` con facturas de compra y venta, incluyendo la generación de referencias de pago y el saldo vivo (`outstanding_amount`).
3. Extender el módulo de contabilidad con CRUD básico de entidades, unidades, libros y series.
4. Corregir los flujos de registro en contabilidad para creación de unidades y libros, y sincronizar redirecciones con el prefijo de ruta `/accounting`.
5. Asegurar que las plantillas y formularios de contabilidad respeten el acceso RBAC y el módulo activo.
6. Documentar los endpoints actuales para permitir futuras transiciones hacia comprobantes contables con líneas y asientos GL reales.

### Resumen tecnico de cambios
- En `cacao_accounting/bancos/__init__.py`:
  - Se consolidaron listas y formularios para `Bank`, `BankAccount`, `PaymentEntry` y `BankTransaction`.
  - Se agregó soporte para seleccionar serie de documento de pago según compañía.
  - Se implementó el cálculo de saldo vivo y la asignación de referencias de pago al crear un pago.
- En `cacao_accounting/contabilidad/__init__.py`:
  - Se mantiene el CRUD de entidades, unidades, libros y series.
  - Se corrigieron los flujos de creación de unidad y libro para usar los modelos correctos (`Unit`, `Book`).
  - Se agregó eliminación funcional para unidades y libros con redirección hacia el listado correcto.
  - Se refuerzan las rutas con `modulo_activo` y `verifica_acceso`.
- En `cacao_accounting/contabilidad/gl/__init__.py`:
  - Se integraron vistas básicas de listado y creación de comprobantes contables.

### Verificacion ejecutada
- Revisión manual de rutas y plantillas de bancos y contabilidad.
- Confirmación de que `bancos/` y `contabilidad/` se cargan sin errores en el módulo actual.

### Notas para siguiente iteracion
1. Implementar el registro completo de comprobantes contables con asientos GL cargables y validaciones de suma débito/crédito.
2. Conectar los pagos de bancos con llamados automáticos a la contabilización en `GL`.
3. Agregar pruebas funcionales para pagos a facturas, listado de transacciones bancarias y creación de comprobantes contables.

## 2026-05-04 (cierre de sesión)

### Peticion del usuario
Finalizar los alcances propuestos en la bitácora del día, estabilizando series, identificadores y cobertura transaccional en Bancos, Contabilidad, Compras, Inventario y Ventas. La única restricción de edición fue no modificar `cacao_accounting/contabilidad/gl/templates/gl_new.html`.

### Plan implementado
1. Cargar el contexto completo definido en `AGENTS.md`, incluyendo instrucciones `.github/instructions/*.md`, `modulos/contexto/*.md`, `SESSIONS.md` y `FIXME.md`.
2. Corregir la regresión Compra → Inventario que impedía ver la acción de "Entrada de Almacén" desde una recepción aprobada.
3. Agregar cobertura backend de cierre para identificadores documentales, validación de periodo cerrado, validación de serie incompatible y validación de serie de otra compañía.
4. Agregar cobertura de pagos parciales contra facturas de compra y venta, incluyendo `PaymentReference`, `allocation_date` y actualización de `outstanding_amount`.
5. Ejecutar y dejar pasando la batería completa de calidad solicitada.

### Resumen tecnico de cambios
- En `cacao_accounting/datos/dev/data.py`:
  - La recepción demo `REC-DEMO-0000001` queda aprobada (`docstatus=1`) para reflejar el flujo Compra → Inventario ya implementado en la plantilla de detalle.
- En `tests/test_06transaction_closure.py`:
  - Nueva suite de cierre para comprobar generación real de `document_no` y `naming_series_id` en documentos de Compras, Ventas, Bancos e Inventario.
  - Pruebas de rechazo por periodo contable cerrado, serie de tipo documental incorrecto y serie de otra compañía.
  - Pruebas de pagos parciales para facturas AP/AR y bloqueo de referencias entre compañías.
- En `cacao_accounting/document_identifiers.py`, `cacao_accounting/bancos/__init__.py` e `cacao_accounting/inventario/__init__.py`:
  - Ajustes de tipado para cumplir `mypy` sin cambiar comportamiento funcional.
- En pruebas auxiliares:
  - Limpieza de estilo para cumplir `ruff`/`flake8`.
  - Formateo general con `black`.

### Verificacion ejecutada
- `python -m compileall cacao_accounting tests` -> passed
- `black --check cacao_accounting tests` -> passed
- `ruff check cacao_accounting tests` -> passed
- `flake8 cacao_accounting tests` -> passed
- `mypy cacao_accounting` -> passed
- `pytest -q` -> 223 passed
- `pytest -q tests/test_03webactions.py --slow=True` -> 16 passed

### Pendientes documentados
1. No se modificó `cacao_accounting/contabilidad/gl/templates/gl_new.html` por instrucción explícita del usuario.

## 2026-05-05 (ledger financiero maestro y subledgers)

### Peticion del usuario
Implementar el plan para completar el ledger financiero maestro y los subledgers de AP, AR, Inventario y Bancos a partir del motor de posting creado en el ultimo commit.

### Plan implementado
1. Refactorizar `cacao_accounting/contabilidad/posting.py` como servicio transaccional con `submit_document`, `cancel_document` y `post_document_to_gl`.
2. Hacer el posting idempotente para evitar duplicacion de `GLEntry` por `company + voucher_type + voucher_id`.
3. Generar entradas GL por todos los libros (`Book`) de la compania, con validacion de balance por libro.
4. Corregir trazabilidad de AR/AP para que facturas y pagos registren `party_type` y `party_id` del cliente/proveedor.
5. Agregar resolucion jerarquica de cuentas usando cuentas explicitas, `PartyAccount`, `ItemAccount` y `CompanyDefaultAccount`.
6. Implementar posting de inventario para `StockEntry`: `StockLedgerEntry`, `StockBin`, `StockValuationLayer` y GL para receipts/issues.
7. Conectar submit/cancel de facturas de compra, facturas de venta, entradas de inventario y pagos al servicio contable con rollback ante errores.
8. Agregar rutas de aprobar/cancelar pagos y acciones visibles en el detalle de pago.
9. Ampliar pruebas del motor contable para multi-ledger, idempotencia, reversos, bancos e inventario.

### Resumen tecnico de cambios
- En `cacao_accounting/contabilidad/posting.py`:
  - Nuevo `LedgerContext` para construir entradas por libro.
  - `submit_document` aprueba y contabiliza en una sola unidad de trabajo.
  - `cancel_document` genera reversos append-only y marca entradas originales como canceladas.
  - `post_document_to_gl` rechaza documentos ya contabilizados.
  - Facturas de venta generan AR por cliente e ingresos por linea.
  - Facturas de compra generan AP por proveedor y gasto o GR/IR segun origen de recepcion.
  - Pagos generan banco contra AR/AP; tambien soportan fallback a `BankAccount.gl_account_id`.
  - Entradas de stock generan ledger de inventario, snapshot en bin, capa de valuacion y GL para receipt/issue; transferencias generan stock ledger sin GL.
- En rutas:
  - `ventas`, `compras`, `inventario` y `bancos` usan `submit_document`/`cancel_document`.
  - Los errores de posting hacen rollback y se muestran con mensajes marcados para traduccion.
- En `tests/test_07posting_engine.py`:
  - La suite pasa de 3 a 9 pruebas cubriendo los escenarios clave del ledger.
- En `tests/z_forms_data.py`:
  - Se corrigio una parentesis extra que impedia ejecutar la suite completa de pytest.

### Verificacion ejecutada
- `pytest -q tests/test_07posting_engine.py` -> 9 passed
- `pytest -q tests/test_06transaction_closure.py tests/test_07posting_engine.py` -> 14 passed
- `pytest -q` -> 275 passed, 4 warnings
- `python -m py_compile` sobre archivos modificados -> passed
- `black --check` sobre archivos modificados -> passed
- `ruff check` sobre archivos modificados -> passed
- `flake8` sobre archivos modificados -> passed
- `mypy cacao_accounting` -> falla por 12 errores preexistentes en `auth/forms.py`, `modulos/__init__.py`, `auth/permisos.py`, `document_flow/tracing.py`, `admin/__init__.py` y `api/__init__.py`; no quedan errores reportados en `contabilidad/posting.py`.

### Notas para siguiente iteracion
1. Completar engine de impuestos para separar `tax_total` en cuentas fiscales especificas.
2. Agregar UI/reportes para trial balance, party ledger, bank ledger y kardex basados en GL/Stock Ledger.
3. Resolver la deuda de mypy preexistente para recuperar la compuerta completa de tipos.

## 2026-05-05 (calidad global)

### Peticion del usuario
Corregir los errores pendientes de formato, lint y tipos para confirmar que todos los controles de calidad pasan antes de continuar.

### Plan implementado
1. Corregir imports faltantes, imports no usados y definiciones duplicadas en autenticacion y formularios.
2. Ajustar anotaciones y conversiones de resultados SQLAlchemy para cumplir `mypy`.
3. Normalizar formato con `black` en los modulos afectados.
4. Corregir lineas largas en el registro de flujos documentales.
5. Verificar la suite completa de calidad solicitada.

### Resumen tecnico de cambios
- En `cacao_accounting/auth/__init__.py` se importo `url_for`.
- En `cacao_accounting/auth/forms.py` se eliminaron imports y clases duplicadas.
- En `cacao_accounting/auth/permisos.py` se declararon atributos dinamicos de permisos para tipado estatico.
- En `cacao_accounting/contabilidad/forms.py` se elimino un import no usado.
- En `cacao_accounting/modulos/__init__.py` se separo la lista detectada de plugins del valor opcional final.
- En `cacao_accounting/admin/__init__.py`, `document_flow/tracing.py` y `api/__init__.py` se convirtieron resultados `Sequence` a `list` donde la firma lo requiere.
- En `cacao_accounting/admin/__init__.py` se corrigio el uso de `proteger_passwd`.
- En `cacao_accounting/document_flow/registry.py` se aplico formato para cumplir longitud de linea.

### Verificacion ejecutada
- `black --check cacao_accounting tests` -> passed
- `ruff check cacao_accounting tests` -> passed
- `flake8 cacao_accounting tests` -> passed
- `mypy cacao_accounting` -> passed
- `pytest -q` -> 275 passed, 4 warnings

## 2026-05-05 (documentacion de estado del posting)

### Peticion del usuario
Actualizar `ESTADO_ACTUAL.md` y `PENDIENTE.md` con los ultimos cambios hechos en el servicio de posting.

### Plan implementado
1. Revisar el contenido actual de ambos documentos y localizar afirmaciones obsoletas sobre GL, Stock Ledger, pagos y multi-ledger.
2. Actualizar `ESTADO_ACTUAL.md` para reflejar `contabilidad/posting.py`, `submit_document`, `cancel_document`, multi-libro, AR/AP, pagos y `StockEntry`.
3. Actualizar `PENDIENTE.md` marcando como completado lo ya implementado y dejando pendientes reales: impuestos, COGS, documentos directos de recepcion/entrega, JE manual, FIFO/Moving Average, reportes y reglas avanzadas.
4. Mantener los pendientes de formularios, notas/devoluciones, reconciliacion y reportes sin darlos por completados.

### Resumen tecnico de cambios
- `ESTADO_ACTUAL.md` ahora incluye el servicio de posting como capa explicita del sistema.
- Los modulos de compras, ventas, bancos e inventario documentan el estado real del posting operativo.
- `PENDIENTE.md` diferencia entre posting base ya operativo y los escenarios contables que siguen incompletos.
- Se ajusto la prioridad recomendada para enfocar la siguiente etapa en posting restante y reportes, no en crear el motor desde cero.
2. El backend de comprobantes contables manuales/GL requiere una iteración dedicada para persistencia real de cabecera, líneas, validación debe/haber y contabilización en `GLEntry`.
3. La contabilización automática de pagos e inventario hacia `GLEntry` queda pendiente para una etapa posterior de motor contable.

## 2026-05-04 (auditoria series e identificadores)

### Peticion del usuario
Realizar una auditoria a la implementacion de series e identificadores en el sistema e implementar un framework robusto que soporte series globales, por compania, series internas controladas por el sistema y series externas (chequeras, numeracion fiscal, recibos preimpresos) con auditoria obligatoria de cambios.

### Plan implementado
1. Agregar el campo `is_default` al modelo `NamingSeries` para cumplir la regla de "maximo una serie predeterminada activa por entity_type + company".
2. Agregar el modelo `ExternalCounter` para representar contadores externos (chequeras, numeracion fiscal, recibos preimpresos, etc.).
3. Agregar el modelo `ExternalCounterAuditLog` para la bitacora obligatoria de ajustes del ultimo numero usado.
4. Actualizar `document_identifiers.py` con:
   - `enforce_single_default_series()` — garantiza unicidad de serie predeterminada.
   - `_pick_naming_series()` — prioriza serie con `is_default=True` por compania.
   - `_create_default_series()` — ya establece `is_default=True` al crear serie automatica.
   - `suggest_next_external_number()` — devuelve el siguiente numero externo sugerido.
   - `record_external_number_used()` — actualiza `last_used` si aplica.
   - `adjust_external_counter()` — ajusta `last_used` con auditoria obligatoria (motivo requerido).
5. Actualizar `contabilidad/forms.py` con nuevos formularios:
   - `FormularioNamingSeries`, `FormularioSecuencia`, `FormularioExternalCounter`, `FormularioAjusteContadorExterno`.
6. Agregar rutas CRUD en `contabilidad/__init__.py`:
   - `/naming-series/list`, `/naming-series/new`, `/naming-series/<id>/toggle-default`, `/naming-series/<id>/toggle-active`.
   - `/external-counter/list`, `/external-counter/new`, `/external-counter/<id>/adjust`, `/external-counter/<id>/audit-log`.
7. Crear plantillas HTML para todas las nuevas vistas.
8. Actualizar `admin.html` para incluir enlaces directos a series de numeracion y contadores externos.
9. Agregar rutas nuevas a `z_static_routes.py` para cobertura en `test_01vistas.py`.
10. Crear `tests/test_07series_audit.py` con 15 pruebas unitarias cubiertas:
    - is_default en NamingSeries.
    - enforce_single_default_series.
    - _pick_naming_series prefiere is_default.
    - ExternalCounter.next_suggested y next_suggested_formatted.
    - suggest_next_external_number y validaciones de inactivo.
    - adjust_external_counter: actualiza last_used, crea auditoria, requiere motivo no vacio.
    - record_external_number_used: incrementa solo si corresponde.
    - Multiples ajustes generan multiples entradas de auditoria.

### Resumen tecnico de cambios
- `cacao_accounting/database/__init__.py`: campo `is_default` en `NamingSeries`, nuevos modelos `ExternalCounter` y `ExternalCounterAuditLog`.
- `cacao_accounting/document_identifiers.py`: servicios de contadores externos y logica de predeterminado.
- `cacao_accounting/contabilidad/forms.py`: nuevos formularios de serie, secuencia y contador externo.
- `cacao_accounting/contabilidad/__init__.py`: rutas CRUD para NamingSeries y ExternalCounter.
- `cacao_accounting/contabilidad/templates/contabilidad/`: 5 nuevas plantillas HTML.
- `cacao_accounting/admin/templates/admin.html`: enlaces a series e identificadores.
- `tests/test_07series_audit.py`: 15 pruebas nuevas.
- `tests/z_static_routes.py`: 4 nuevas rutas de cobertura estatica.

### Verificacion ejecutada
- `python3 -m compileall cacao_accounting/` -> passed
- `python3 -m flake8 cacao_accounting/ --max-line-length=130` -> passed
- `python3 -m ruff check cacao_accounting/` -> passed
- `python3 -m black --check cacao_accounting/ tests/` -> passed
- `python3 -m mypy cacao_accounting/ --ignore-missing-imports` -> passed
- `pytest tests/test_07series_audit.py -v` -> 15 passed
- `pytest tests/ -q --slow=True` -> 236 passed (2 fallos preexistentes sin relacion con estos cambios)

### Pendientes documentados
1. Implementar enlace de ExternalCounter con documentos transaccionales (ej: al crear un pago, seleccionar el cheque del contador externo).
2. Mostrar en el formulario de pago el siguiente numero de cheque sugerido al seleccionar una chequera.
3. El backend de comprobantes contables manuales/GL requiere una iteracion dedicada.

## 2026-05-04 (correccion series e identificadores)

### Peticion del usuario
Analizar `git diff --cached` contra `requerimiento.md`, corregir gaps de la implementacion actual, evitar mutaciones accidentales por rutas GET y actualizar la bitacora de desarrollo.

### Plan implementado
1. Corregir `FormularioAjusteContadorExterno.new_last_used` para aceptar `0` usando `InputRequired()` y `NumberRange(min=0)`.
2. Convertir las rutas mutantes `/naming-series/<id>/toggle-default` y `/naming-series/<id>/toggle-active` a POST-only.
3. Reemplazar enlaces GET de acciones en la lista de series por formularios POST con CSRF.
4. Corregir la regla de predeterminadas para que una serie por compania no desmarque la predeterminada global.
5. Ajustar la seleccion de series para respetar predeterminada por compania, fallback por compania y predeterminada global.
6. Crear `Sequence` y `SeriesSequenceMap` al crear `NamingSeries` desde la UI.
7. Crear `SeriesExternalCounterMap` al crear un `ExternalCounter` asociado a una serie interna.
8. Validar que los contadores externos pertenezcan a la misma compania del documento.
9. Endurecer condiciones JSON de contadores externos para rechazar JSON valido que no sea objeto.
10. Ampliar pruebas de regresion de series, contadores externos, rutas POST-only y validacion cross-company.

### Resumen tecnico de cambios
- `cacao_accounting/contabilidad/forms.py`: validadores para aceptar cero y campos de secuencia en `FormularioNamingSeries`.

## 2026-05-05 (roles, permisos y mayor contable)

### Peticion del usuario
Documentar los cambios recientes de UX de roles y permisos y la alineación del ledger contable con reglas estrictas de integridad y motor de posting.

### Plan implementado
1. Revisar e implementar la administración de roles y permisos en el módulo admin.
2. Corregir la lógica del engine de permisos para que el acceso de administradores funcione y los templates usen campos seguros de Jinja.
3. Añadir restricciones de integridad en `GLEntry` para asegurar que cada registro tenga solo débito o crédito positivo.
4. Crear un motor de posting contable capaz de generar `GLEntry` desde documentos operativos clave.
5. Añadir pruebas de validación para la integridad del mayor y para el posting de documentos contables.

### Resumen tecnico de cambios
- `cacao_accounting/auth/permisos.py`:
  - Se restauró el acceso `.autorizado` y el fallback admin para ingresar al panel.
  - Se mejoró la consulta para obtener permisos de usuario por módulo y rol.
- `cacao_accounting/admin/__init__.py`:
  - Se agregaron rutas CRUD para `Roles` y asignación de permisos.
  - Se corrigió el import de `RolesAccess` y se normalizaron los datos de permisos para templates.
- Admin templates:
  - Se corrigieron variables Jinja y se ocultó el token CSRF cuando se renderiza el formulario.
  - Se agregaron vistas para lista de roles, edición y asignación de permisos.
- `cacao_accounting/database/__init__.py`:
  - Se agregó `CheckConstraint` en `GLEntry`:
    - `ck_gl_entry_debit_credit_integrity`
    - `ck_gl_entry_debit_non_negative`
    - `ck_gl_entry_credit_non_negative`
  - Esto refuerza la regla contable: una entrada GL debe tener solo débito o crédito positivo, no ambos.
- `cacao_accounting/contabilidad/posting.py`:
  - Nuevo motor de posting contable para documentar y poblar `GLEntry` desde:
    - `SalesInvoice`
    - `PurchaseInvoice`
    - `PaymentEntry`
    - `StockEntry`
  - Soporta trazabilidad con `voucher_type`, `voucher_id`, `document_no`, `naming_series_id` y periodos contables.
  - Valida periodos abiertos antes de contabilizar.
- `tests/test_07posting_engine.py`:
  - Se agregaron pruebas para:
    - rechazo de asientos GL no balanceados por constraint.
    - posting balanceado de `SalesInvoice`.
    - posting balanceado de `PaymentEntry`.

### Verificacion ejecutada
- `python -m py_compile cacao_accounting/contabilidad/posting.py tests/test_07posting_engine.py` -> passed
- `pytest tests/test_07posting_engine.py -q` -> 3 passed
- `pytest tests/test_04database_schema.py -q` -> 191 passed
- `pytest tests/test_06transaction_closure.py -q` -> 5 passed

### Notas para siguiente iteracion
1. Agregar pruebas adicionales de posting para `PurchaseInvoice` y `StockEntry`.
2. Integrar el engine de posting en el flujo de submit de documentos operativos.
3. Implementar validaciones de periodo contable y libro contable en la UI de cierre/contabilización.
- `cacao_accounting/contabilidad/__init__.py`: rutas mutantes POST-only; alta de series crea secuencia/mapa; alta de contador crea mapa externo.
- `cacao_accounting/contabilidad/templates/contabilidad/naming_series_lista.html`: acciones POST con CSRF y columnas de contador interno/externo.
- `cacao_accounting/contabilidad/templates/contabilidad/naming_series_nueva.html`: captura de valor inicial, incremento, padding y politica de reinicio.
- `cacao_accounting/document_identifiers.py`: seleccion de defaults corregida, validacion cross-company y condiciones JSON robustas.
- `tests/test_07series_audit.py`: cobertura ampliada a 36 pruebas.

### Verificacion ejecutada
- `python -m compileall cacao_accounting tests` -> passed
- `black --check cacao_accounting tests` -> passed
- `ruff check cacao_accounting tests` -> passed
- `flake8 cacao_accounting tests` -> passed
- `mypy cacao_accounting` -> passed
- `pytest -q tests/test_04database_schema.py tests/test_06transaction_closure.py tests/test_07series_audit.py` -> 232 passed
- `pytest -q tests/test_01vistas.py tests/test_02forms.py tests/test_03webactions.py --slow=True` -> 16 passed, 2 failed preexistentes/no relacionados:
  - `tests/test_01vistas.py::test_visit_views` espera `Nueva Moneda` en `/accounting/currency/list`, pero la vista paginada actual no lo muestra en la primera pagina.
  - `tests/test_03webactions.py::test_inventory_stock_entry_routes` espera `/buying/purchase-receipt/REC-DEMO-0000001`, pero el dataset slow actual responde 404.

### Pendientes documentados
1. Revisar la cobertura slow preexistente de moneda y recepcion demo para decidir si se corrige el dato de prueba o el assert.
2. Implementar UI dedicada para condiciones (`condition_json`) de `SeriesExternalCounterMap` si se requieren mapas externos dinamicos por banco/metodo.

## 2026-05-04 (flujo documental y estados)

### Peticion del usuario
Implementar el framework transversal de flujo documental definido en `requerimiento.md`, incluyendo trazabilidad por linea, saldos pendientes, creacion de documentos relacionados, reversión al cancelar, cierre manual y un estado unico calculado con badge informativo en listas y detalles.

### Plan implementado
1. Extender `DocumentRelation` para conservar historial de relaciones activas/revertidas sin eliminar trazabilidad.
2. Agregar `DocumentLineFlowState` como cache auditable de cantidades fuente, procesadas, cerradas y pendientes por linea + tipo destino.
3. Ampliar `document_flow` con registro de flujos de compras, ventas, inventario y pagos.
4. Agregar servicios para recalcular saldos, cerrar lineas/documentos, revertir relaciones al cancelar y crear documentos destino desde lineas fuente.
5. Crear un servicio central de estados documentales con estado unico calculado y tonos de badge.
6. Publicar APIs transversales para documentos fuente, lineas pendientes, creacion de destino, cierre de saldos, estado calculado y arbol de trazabilidad.
7. Integrar badges calculados en listas y vistas de detalle de compras, ventas, inventario y bancos/pagos.
8. Corregir dos brechas detectadas por la bateria slow: texto esperado `Nueva Moneda` en lista de monedas y campo `is_return` faltante en `FormularioFacturaVenta`.

### Resumen tecnico de cambios
- `cacao_accounting/database/__init__.py`: nuevos campos de historial en `DocumentRelation` y nuevo modelo `DocumentLineFlowState`.
- `cacao_accounting/document_flow/registry.py`: registro ampliado de documentos y flujos permitidos.
- `cacao_accounting/document_flow/service.py`: cierre manual, reversión, lineas pendientes, documentos fuente y creacion generica de documentos destino.
- `cacao_accounting/document_flow/status.py`: calculo centralizado de estados como `Pendiente Recibir`, `Recibido Parcialmente`, `Pendiente Facturar`, `Completado`, `Pagado` y `Cancelado`.
- `cacao_accounting/document_flow/tracing.py`: arbol upstream/downstream para trazabilidad documental.
- `cacao_accounting/api/__init__.py`: endpoints `/api/document-flow/*` nuevos.
- `cacao_accounting/templates/macros.html`: macros `document_status_badge`, `document_status_for` y `document_flow_trace`.
- Templates de compras, ventas, inventario y bancos: badge informativo en listas y badge + texto completo en detalles.
- `tests/test_05document_flow.py`: cobertura de saldos parciales, sobreconsumo, reversión al cancelar, cierre manual y estados/badges calculados.

### Verificacion ejecutada
- `python -m compileall cacao_accounting tests` -> passed
- `black --check cacao_accounting tests` -> passed
- `ruff check cacao_accounting tests` -> passed
- `flake8 cacao_accounting tests` -> passed
- `mypy cacao_accounting` -> passed
- `pytest -q` -> 262 passed
- `pytest -q tests/test_01vistas.py --slow=True` -> 1 passed
- `pytest -q tests/test_03webactions.py --slow=True` -> 16 passed

### Pendientes documentados
1. Evolucionar el modal `Actualizar Elementos` para seleccionar documentos fuente desde `/api/document-flow/source-documents` sin depender de una fuente preseleccionada por URL.
2. Agregar vistas dedicadas para explorar el arbol completo de trazabilidad devuelto por `/api/document-flow/tree`.

## 2026-05-04 (framework de trazabilidad - panel UI y API de resumen)

### Peticion del usuario
Implementar el framework de trazabilidad de documentos descrito en `requerimiento.md`, que incluye panel colapsable con documentos relacionados agrupados por tipo, contadores activos/historicos, badges de estado, navegacion a listas filtradas y acciones de creacion de documentos relacionados.

### Plan implementado
1. Agregar funcion `document_flow_summary()` en `tracing.py` que devuelve upstream y downstream agrupados por tipo documental, con contadores activos/historicos, label, modulo y endpoint de lista.
2. Exportar `document_flow_summary` desde `document_flow/__init__.py`.
3. Agregar endpoint REST `GET /api/document-flow/summary?document_type=&document_id=` en `api/__init__.py`.
4. Agregar vista HTML `GET /document-flow/list/<doctype>?related_doctype=&related_id=` en `api/__init__.py` que muestra documentos del tipo solicitado relacionados al documento origen.
5. Crear plantilla `cacao_accounting/templates/document_flow_related_list.html` para la vista de lista filtrada, con breadcrumb, indicador de filtro activo y boton para quitar filtro.
6. Reemplazar el macro `document_flow_trace` en `macros.html` con un panel colapsable completo usando Alpine.js que:
   - Carga el resumen via `/api/document-flow/summary` al abrir.
   - Muestra estado del documento actual con badge.
   - Lista acciones de creacion de documentos relacionados.
   - Agrupa documentos origen (upstream) y destino (downstream) por tipo con contadores activos/historicos.
   - Muestra badge de estado calculado por cada documento relacionado.
   - Proporciona enlace "Ver lista" que navega a `/document-flow/list/<doctype>` con filtro por documento actual.
   - Marca relaciones historicas (revertidas/cerradas) con tachado visual.
7. Agregar 4 pruebas unitarias en `tests/test_05document_flow.py` cubriendo: resumen con relaciones activas, conteo de historicos post-reversion, relaciones upstream desde recibo, y exposicion de create_actions.

### Resumen tecnico de cambios
- `cacao_accounting/document_flow/tracing.py`: nueva funcion `document_flow_summary()` con helpers `_group_key`, `_doctype_label`, `_doctype_list_endpoint` y `_build_groups`.
- `cacao_accounting/document_flow/__init__.py`: exportacion de `document_flow_summary`.
- `cacao_accounting/api/__init__.py`: nuevo endpoint `/api/document-flow/summary`, nueva vista HTML `/document-flow/list/<doctype>`, importaciones adicionales (`render_template`, `DOCUMENT_TYPES`, `normalize_doctype`, `get_document`).
- `cacao_accounting/templates/macros.html`: macro `document_flow_trace` completamente reescrito con Alpine.js, panel colapsable, agrupaciones, contadores, badges y navegacion.
- `cacao_accounting/templates/document_flow_related_list.html`: nueva plantilla para lista de documentos filtrada por relacion documental.
- `tests/test_05document_flow.py`: 4 nuevas pruebas para `document_flow_summary`.

### Verificacion ejecutada
- `python -m compileall cacao_accounting/ -q` -> passed
- `python -m flake8 cacao_accounting/document_flow/tracing.py cacao_accounting/document_flow/__init__.py cacao_accounting/api/__init__.py tests/test_05document_flow.py --max-line-length=130` -> passed
- `python -m ruff check cacao_accounting/document_flow/ cacao_accounting/api/__init__.py tests/test_05document_flow.py` -> passed
- `pytest tests/test_05document_flow.py -q` -> 9 passed
- `pytest tests/ -q` -> 266 passed

### Pendientes documentados
1. Actualizar el modal `Actualizar Elementos` para seleccionar multiples documentos fuente via `/api/document-flow/source-documents` dinamicamente.
2. Implementar arbol grafico de trazabilidad directa e indirecta basado en `/api/document-flow/tree` (vista de diagrama de flujo completo).
3. Constructor de filtros avanzados por campos del encabezado en listas de documentos (filtros personalizados por campo/valor/operador).
4. Soporte de filtros relacionales en los listados propios de cada modulo (compras, ventas, bancos, inventario) sin requerir la vista generica de flujo.

## 2026-05-05 (registros pendientes bancos/compras/ventas/inventario)

### Peticion del usuario
Analizar `ESTADO_ACTUAL.md` y `PENDIENTE.md`, finalizar registros pendientes en Bancos, Compras, Ventas e Inventario, separar transferencias de pagos a clientes/proveedores y actualizar la bitacora/documentacion.

### Plan implementado
1. Revisar estado de rutas de registros y confirmar cobertura de notas de débito, notas de crédito y devoluciones en compras/ventas/inventario.
2. Completar ajuste estructural en Bancos para separar transferencias internas de pagos/cobros.
3. Endurecer validaciones para impedir mezcla de referencias de compras/ventas y transferencias en la misma operación.
4. Actualizar `ESTADO_ACTUAL.md` y `PENDIENTE.md` con el nuevo estado funcional.

### Resumen tecnico de cambios
- `bancos` separa listado de pagos/cobros versus transferencias internas (`/payment/list` y `/transfer/list`).
- Se agregaron validaciones para bloquear mezclas no permitidas:
  - no se permite combinar facturas de compra y venta en un mismo pago;
  - no se permite usar transferencias internas con referencias de facturas.
- Se actualizó la documentación de estado y pendientes para reflejar la separación operativa de transferencias bancarias y la implementación vigente de registros de notas/devoluciones en compras y ventas.

### Actualizacion adicional
- Se implementaron registros operativos faltantes en Bancos para notas de débito y notas de crédito bancario (listado + creación).
- Se dejó separación explícita entre pagos/cobros (`PaymentEntry`) y notas bancarias (`BankTransaction`) para evitar mezcla de naturalezas.

## 2026-05-05 (registros pendientes compras/ventas/inventario)

### Peticion del usuario
Completar registros pendientes en Compras, Ventas e Inventarios.

### Plan implementado
1. Crear rutas explícitas de creación para notas y devoluciones de compra.
2. Agregar alias explícito para listado de nota de crédito en ventas.
3. Implementar registros de ajuste y conciliación física en inventario como propósitos de `StockEntry` con listados y accesos directos.

### Resumen tecnico de cambios
- Compras: nuevas rutas de creación para nota de débito, nota de crédito y devolución sobre factura de compra.
- Ventas: alias explícito para listado de nota de crédito de venta (`/sales-invoice/credit-note/list`).
- Inventario: nuevos listados y creación para `stock_adjustment` y `stock_reconciliation` dentro de `StockEntry`.

### Actualizacion de inventario (ajustes + conciliación)
- Se implementaron rutas y propósitos explícitos para `adjustment_positive` y `adjustment_negative` en `StockEntry` (listado/creación).
- Se completó el soporte de conciliación de inventario en posting para generar movimientos de stock y GL según el signo del ajuste.

## 2026-05-05 (cierre de auditoría de registros y ledgers)

### Peticion del usuario
Implementar el plan de cierre de issues detectados en la auditoría de calidad de los cambios staged para Bancos, Compras, Ventas e Inventarios.

### Plan implementado
1. Limpiar código generado duplicado en `posting.py` y dejar una sola definición de helpers contables centrales.
2. Bloquear salidas de inventario sin capas de valuación suficientes y eliminar el fallback de costo por rate de línea.
3. Cambiar cancelación de inventario a reversos append-only en `StockLedgerEntry` y `StockValuationLayer`, actualizando `StockBin` desde el reverso.
4. Endurecer GR/IR para exigir recepción aprobada, contabilizada y con saldo pendiente antes de reconciliar una factura.
5. Mejorar notas bancarias y conciliación MVP con carga usable de cuentas, validación de compañía y bloqueo de duplicados.
6. Ampliar pruebas de posting para cubrir reversos de stock append-only, bloqueo de stock negativo, GR/IR y notas bancarias.

### Resumen tecnico de cambios
- `cacao_accounting/contabilidad/posting.py`: stock negativo bloqueado para entregas/salidas; reversos de stock append-only; GR/IR validado; helpers duplicados eliminados.
- `cacao_accounting/bancos/__init__.py`: creación de notas bancarias valida cuenta/compañía y conciliación rechaza transacciones ya conciliadas o duplicadas.
- `cacao_accounting/bancos/templates/bancos/transaccion_nueva.html`: strings visibles nuevos marcados para traducción.
- `cacao_accounting/document_flow/service.py`: ajustes menores de typing para mypy.
- `tests/test_07posting_engine.py`: cobertura ampliada de 17 a 20 pruebas.

### Verificacion ejecutada
- `pytest -q tests/test_07posting_engine.py` -> 20 passed.
- `ruff check cacao_accounting/contabilidad/posting.py cacao_accounting/bancos/__init__.py cacao_accounting/compras/__init__.py cacao_accounting/ventas/__init__.py cacao_accounting/inventario/__init__.py cacao_accounting/document_flow/service.py cacao_accounting/document_flow/status.py tests/test_07posting_engine.py` -> passed.
- `mypy cacao_accounting/contabilidad/posting.py cacao_accounting/bancos/__init__.py cacao_accounting/document_flow/service.py cacao_accounting/document_flow/status.py` -> passed.
- `black --check cacao_accounting/contabilidad/posting.py cacao_accounting/bancos/__init__.py cacao_accounting/document_flow/service.py tests/test_07posting_engine.py` -> passed.
- `flake8 cacao_accounting/contabilidad/posting.py cacao_accounting/bancos/__init__.py tests/test_07posting_engine.py` -> passed.
- `python -m py_compile cacao_accounting/contabilidad/posting.py cacao_accounting/bancos/__init__.py cacao_accounting/compras/__init__.py cacao_accounting/ventas/__init__.py cacao_accounting/inventario/__init__.py cacao_accounting/document_flow/service.py cacao_accounting/document_flow/status.py tests/test_07posting_engine.py` -> passed.

## 2026-05-05 (conciliaciones finales y reportes operativos)

### Peticion del usuario
Implementar el plan revisado para cerrar brechas restantes: GR/IR por lineas y cantidades, conciliacion bancaria completa contra `PaymentEntry`/`GLEntry`, reportes finales y actualizacion de `ESTADO_ACTUAL.md`, `PENDIENTE.md` y `SESSIONS.md`.

### Plan implementado
1. Extender el modelo de conciliaciones para soportar conciliacion parcial, origen/destino, estado y fecha de conciliacion.
2. Crear detalle `GRIRReconciliationItem` para reconciliar facturas de compra contra recepciones por linea, cantidad, monto, item, almacen y UOM.
3. Crear servicios de GR/IR y conciliacion bancaria con validaciones de compania, duplicados, parcialidades y reversibilidad.
4. Agregar vistas HTML minimas para GR/IR, conciliacion bancaria y reportes operativos.
5. Implementar servicios de reportes para subledger AR/AP, aging, Kardex y reconciliaciones.
6. Agregar pruebas de regresion para parcialidades, duplicados, reportes y cuadratura contra las fuentes operativas.

### Resumen tecnico de cambios
- `cacao_accounting/database/__init__.py`: `ReconciliationItem` ahora guarda asignacion parcial, fuente, destino, fecha y estado; se agrego `GRIRReconciliationItem`.
- `cacao_accounting/compras/gr_ir_service.py`: nuevo servicio `reconcile_gr_ir_invoice`, `cancel_gr_ir_for_invoice` y `get_gr_ir_pending`.
- `cacao_accounting/contabilidad/posting.py`: el posting de `PurchaseInvoice` usa GR/IR por lineas; la cancelacion revierte solo conciliaciones activas de la factura.
- `cacao_accounting/bancos/reconciliation_service.py`: nuevo motor para reconciliar `BankTransaction` contra pagos o GL bancario, con 1:1, 1:N, N:1 y parcialidades.
- `cacao_accounting/bancos/__init__.py`: rutas HTML para `/bank-reconciliation`, detalle por cuenta y aplicacion de conciliacion.
- `cacao_accounting/compras/__init__.py`: ruta `/gr-ir` para consulta de pendientes GR/IR.
- `cacao_accounting/reportes/`: nuevo blueprint y servicios para `/reports/subledger`, `/reports/aging`, `/reports/kardex` y `/reports/reconciliations`.
- `tests/test_08_reconciliation_reports.py`: nueva cobertura para GR/IR parcial, conciliacion bancaria parcial/duplicada y reportes.
- `ESTADO_ACTUAL.md` y `PENDIENTE.md`: actualizados para reflejar lo implementado y dejar pendientes posteriores.

### Verificacion ejecutada
- `pytest -q tests/test_07posting_engine.py tests/test_08_reconciliation_reports.py` -> 24 passed.
- `pytest -q tests/test_08_reconciliation_reports.py` -> 4 passed.
- `pytest -q` -> 290 passed, 4 warnings de Flask-Caching/deprecacion externa.
- `ruff check` sobre archivos tocados -> passed.
- `black --check` sobre archivos tocados -> passed.
- `flake8 cacao_accounting` -> passed.
- `mypy cacao_accounting tests/test_08_reconciliation_reports.py` -> passed.
- `python -m py_compile` sobre archivos tocados -> passed.

### Pendientes posteriores
1. Definir cuenta y politica de ajuste para diferencias de precio GR/IR; por ahora se bloquean.
2. Mejorar reglas configurables de matching bancario e importacion masiva de extractos.
3. Agregar exportaciones, paginacion avanzada y buckets configurables en reportes.
4. Crear migracion formal si se deja de depender de `database.create_all()` para pruebas y entornos nuevos.

## 2026-05-05 (cierre funcional bancos/inventario/compras/ventas)

### Peticion del usuario
Implementar el plan para completar brechas de Bancos, Inventario, Compras y Ventas: impuestos/cargos y pricing desde configuracion admin, anticipos, UOM/lote/serial, reconstruccion de bins, importacion de extractos, reglas de matching y reportes operativos finales.

### Plan implementado
1. Extender modelos existentes de impuestos, plantillas, listas de precio y cuentas por defecto; agregar regla de matching bancario.
2. Crear servicios publicos para calculo de impuestos/precios, conversion UOM, validacion lote/serial, reconstruccion de `StockBin`, importacion CSV bancaria y ajustes de diferencia.
3. Conectar `TaxTemplate` al posting de facturas de compra y venta, manteniendo GL balanceado por libro.
4. Agregar UI admin exclusiva para impuestos/precios y UI bancaria para importar extractos y configurar reglas.
5. Ampliar reportes operativos de compras, ventas, margen, stock balance, valoracion, lotes y seriales.
6. Actualizar documentacion de estado, pendientes y bitacora.

### Resumen tecnico de cambios
- `cacao_accounting/tax_pricing_service.py`: nuevo servicio `calculate_taxes`, `get_item_price` y `validate_price_tolerance`.
- `cacao_accounting/inventario/service.py`: nuevo servicio `convert_item_qty`, validacion lote/serial, actualizacion de seriales y `rebuild_stock_bins`.
- `cacao_accounting/bancos/statement_service.py`: importacion CSV con preview, duplicados, reglas de matching y helper de ajuste bancario.
- `cacao_accounting/admin/__init__.py`: rutas `/settings/taxes`, `/settings/tax-templates`, `/settings/price-lists` y `/settings/item-prices`, protegidas para administrador.
- `cacao_accounting/contabilidad/posting.py`: facturas de compra/venta generan GL de impuestos/cargos; pagos sin cuenta AR/AP pueden usar cuentas de anticipo configuradas.
- `cacao_accounting/reportes/`: reportes MVP de compras/ventas por tercero/item, margen bruto, stock balance, valoracion, lotes y seriales.
- `tests/test_08_reconciliation_reports.py`: cobertura ampliada para impuestos, pricing, UOM/lote/serial/rebuild e importacion bancaria.

### Verificacion ejecutada
- `pytest -q tests/test_08_reconciliation_reports.py` -> 7 passed.
- `pytest -q tests/test_07posting_engine.py tests/test_08_reconciliation_reports.py` -> 27 passed.
- `pytest -q` -> 293 passed, 4 warnings de Flask-Caching/deprecacion externa.
- `ruff check cacao_accounting tests/test_07posting_engine.py tests/test_08_reconciliation_reports.py` -> passed.
- `flake8 cacao_accounting` -> passed.
- `mypy cacao_accounting tests/test_08_reconciliation_reports.py` -> passed.
- `python -m py_compile` sobre archivos tocados -> passed.

### Pendientes posteriores
1. Migracion formal del esquema extendido para instalaciones existentes.
2. Prorrateo real de cargos capitalizables hacia `StockValuationLayer`.
3. UI avanzada de edicion/eliminacion para impuestos, plantillas, precios y reglas bancarias.
4. Exportaciones, paginacion avanzada y filtros configurables en reportes.

## 2026-05-05 (Renaming: Framework de Conciliación de Compras — eliminación del término GR/IR)

### Peticion del usuario
1. Continuar la implementación sobre la rama `main` actualizada.
2. El término **GR/IR (Goods Receipt / Invoice Receipt)** está prohibido en el proyecto — es terminología específica de SAP.  Se debe usar únicamente el nombre genérico **"Conciliación de Compras"** / **"Purchase Reconciliation"** en todo el código, plantillas, tests y documentación.
3. Implementar el framework completo: configuración por compañía, eventos económicos inmutables, y tarjeta de administración en el menú de configuración.

### Decisiones de diseño
- **Terminología prohibida:** `GR/IR`, `GRIR`, `gr_ir`, `gr-ir` — ningún identificador o texto visible al usuario debe usar estos términos.
- **Nombre canónico:** "Conciliación de Compras" (español) / "Purchase Reconciliation" (inglés).
- **Cuenta puente:** renombrada de `gr_ir_account_id` a `bridge_account_id` en `CompanyDefaultAccount`.
- **Tipo de cuenta interna:** renombrado de `"gr_ir"` a `"bridge"` en el mapa de cuentas del motor de posting.
- **Nombre de tabla:** `gr_ir_reconciliation` → `purchase_reconciliation`; `gr_ir_reconciliation_item` → `purchase_reconciliation_item`.
- **Clase Python:** `GRIRReconciliation` → `PurchaseReconciliation`; `GRIRReconciliationItem` → `PurchaseReconciliationItem`.
- **Módulo de servicio:** `gr_ir_service.py` → `purchase_reconciliation_service.py` (el archivo antiguo queda como shim de compatibilidad con aliases).
- **Eventos económicos:** `EventType` enum con valores descriptivos: `GOODS_RECEIVED`, `INVOICE_RECEIVED`, `MATCH_COMPLETED`, `MATCH_FAILED`, `MATCH_CANCELLED` — estos nombres de evento son aceptables porque describen la semántica de negocio, no el producto SAP.
- **Items de conciliación:** el estado del item siempre es `"reconciled"` una vez creado (el ítem representa una cantidad ya conciliada); el estado parcial/total se refleja en el encabezado `PurchaseReconciliation`.
- **Configuración por compañía:** `PurchaseMatchingConfig` permite configurar `matching_type` (2-way / 3-way), tolerancias de precio y cantidad, cuenta puente requerida y auto-conciliación. Al crear una compañía se siembra en modo **más estricto** (3-way, 0% tolerancia).

### Plan implementado
1. Merge de `main` → rama de trabajo (adquirió 6103 líneas nuevas en 37 archivos).
2. Renombrado exhaustivo de todos los identificadores GR/IR en código Python, templates HTML y tests.
3. Nuevos modelos en `database/__init__.py`: `PurchaseMatchingConfig`, `PurchaseEconomicEvent`, `PurchaseReconciliation`, `PurchaseReconciliationItem`.
4. Nuevo servicio `purchase_reconciliation_service.py` con motor de matching configurable (2-way/3-way, tolerancias, eventos económicos).
5. Ruta de administración `/settings/purchase-reconciliation` con formulario de configuración por compañía.
6. Tarjeta "Conciliación de Compras" añadida a `admin.html`.
7. Hook en creación de compañía (`nueva_entidad`) para sembrar configuración estricta automáticamente.
8. Corrección de bug: `_matched_qty_for_receipt_item` filtraba solo `status="reconciled"` — ahora excluye `"cancelled"` para incluir ítems parciales.

### Resumen tecnico de cambios
- `cacao_accounting/database/__init__.py`: modelos `PurchaseMatchingConfig`, `PurchaseEconomicEvent`, `PurchaseReconciliation`, `PurchaseReconciliationItem`; columna `bridge_account_id` en `CompanyDefaultAccount`.
- `cacao_accounting/compras/purchase_reconciliation_service.py`: servicio nuevo con motor de matching configurable, enums `MatchingType`, `MatchingResult`, `ToleranceType`, `EventType`, `seed_matching_config_for_company`, `emit_economic_event`.
- `cacao_accounting/compras/gr_ir_service.py`: convertido en shim de compatibilidad con re-exports y aliases.
- `cacao_accounting/compras/__init__.py`: ruta `/purchase-reconciliation` (`compras_purchase_reconciliation`).
- `cacao_accounting/compras/templates/compras/purchase_reconciliation.html`: plantilla renombrada sin GR/IR.
- `cacao_accounting/contabilidad/posting.py`: tipo de cuenta `"bridge"`, función `_record_purchase_reconciliation`, cancel usa `cancel_purchase_reconciliation`.
- `cacao_accounting/contabilidad/__init__.py`: `nueva_entidad` llama a `seed_matching_config_for_company`.
- `cacao_accounting/reportes/services.py`: usa `get_purchase_reconciliation_pending`, `recon_type="purchase_reconciliation"`.
- `cacao_accounting/admin/__init__.py`: ruta `/settings/purchase-reconciliation`, importa `PurchaseMatchingConfig`.
- `cacao_accounting/admin/templates/admin.html`: tarjeta "Conciliación de Compras".
- `cacao_accounting/admin/templates/admin/purchase_reconciliation_config.html`: UI de configuración.
- `tests/test_04database_schema.py`: `PurchaseReconciliation`, tabla `purchase_reconciliation`.
- `tests/test_07posting_engine.py`: `PurchaseReconciliation`, `bridge_account_id`, `bridge_account`.
- `tests/test_08_reconciliation_reports.py`: `reconcile_purchase_invoice`, `get_purchase_reconciliation_pending`, `PurchaseReconciliationItem`, `PurchaseReconciliationError`.

### Verificacion ejecutada
- `black cacao_accounting/ tests/` → 5 archivos reformateados, resto sin cambios.
- `flake8 cacao_accounting/ --max-line-length=130` → sin errores.
- `ruff check cacao_accounting/` → All checks passed.
- `mypy cacao_accounting/ --ignore-missing-imports` → Success: no issues found in 64 source files.
- `pytest -q tests/` → **293 passed**, 4 warnings (Flask-Caching/deprecaciones externas).

## 2026-05-05 (corrección 2-way de Conciliación de Compras)

### Peticion del usuario
Implementar el plan consolidado del framework de Conciliación de Compras y corregir los hallazgos de revisión: el modo 2-way no debe guardar líneas de OC como líneas de recepción y el posting debe auto-conciliar facturas contra OC sin recepción cuando la compañía está configurada en 2-way.

### Decisiones de diseño
- Se mantiene el nombre funcional **Conciliación de Compras**; el cambio fuera de GR/IR fue intencional para evitar terminología específica de SAP.
- `PurchaseReconciliationItem` distingue referencias 2-way y 3-way: `purchase_order_item_id` para OC vs factura, `purchase_receipt_item_id` para recepción vs factura.
- La auto-conciliación se decide por `PurchaseMatchingConfig.auto_reconcile`; 2-way usa `purchase_order_id` sin exigir recepción y 3-way exige recepción aprobada.
- El panel de conciliación se alimenta desde el servicio, dejando la ruta como capa HTTP/render únicamente.

### Plan implementado
1. Agregar `purchase_order_item_id` nullable y hacer `purchase_receipt_item_id` nullable en `PurchaseReconciliationItem`.
2. Guardar snapshot de tolerancias usadas en `PurchaseReconciliation`.
3. Corregir `_reconcile_two_way` para usar líneas de OC y calcular cantidades ya conciliadas por `purchase_order_item_id`.
4. Mantener `_reconcile_three_way` con líneas de recepción y bloquear conciliación por encima de cantidad disponible.
5. Invocar conciliación desde `post_purchase_invoice` cuando existe recepción o una orden de compra, respetando `auto_reconcile`.
6. Mover la agrupación del panel de conciliación al servicio `get_purchase_reconciliation_panel_groups`.
7. Añadir pruebas para FK en 2-way, auto-conciliación PO-only desde posting y eventos generados.
8. Actualizar `ESTADO_ACTUAL.md` y `PENDIENTE.md` con el estado real.

### Resumen tecnico de cambios
- `cacao_accounting/database/__init__.py`: `PurchaseReconciliation` guarda snapshot de tolerancias; `PurchaseReconciliationItem` soporta `purchase_order_item_id` y referencias nullable según tipo de matching.
- `cacao_accounting/compras/purchase_reconciliation_service.py`: helpers separados para cantidades conciliadas por recepción y por OC; 2-way ya no reutiliza `purchase_receipt_item_id`; nuevo servicio para grupos del panel; eventos de cancelación tipados.
- `cacao_accounting/contabilidad/posting.py`: facturas con `purchase_order_id` también entran al flujo de auto-conciliación; el evento `INVOICE_RECEIVED` incluye OC y recepción.
- `cacao_accounting/compras/__init__.py`: la ruta del panel delega la lógica de agrupación al servicio.
- `tests/test_08_reconciliation_reports.py`: cobertura 2-way con FK activas y cobertura de auto-conciliación desde posting.

### Verificacion ejecutada
- `python -m py_compile cacao_accounting/compras/purchase_reconciliation_service.py cacao_accounting/contabilidad/posting.py cacao_accounting/database/__init__.py cacao_accounting/compras/__init__.py tests/test_08_reconciliation_reports.py` -> sin errores.
- `ruff check cacao_accounting/compras/purchase_reconciliation_service.py cacao_accounting/contabilidad/posting.py cacao_accounting/database/__init__.py cacao_accounting/compras/__init__.py tests/test_08_reconciliation_reports.py` -> passed.
- `pytest -q tests/test_08_reconciliation_reports.py -q` -> 15 passed.
- `ruff check .` -> passed.
- `mypy cacao_accounting` -> Success: no issues found in 64 source files.
- `pytest -q tests/test_08_reconciliation_reports.py tests/test_07posting_engine.py tests/test_04database_schema.py` -> 226 passed.
- `pytest -q` -> 301 passed, 4 warnings externas de Flask-Caching/deprecación.
- `flake8` sin scope del proyecto falla porque analiza `venv/`; `flake8 cacao_accounting tests --max-line-length=130` -> passed.

### Pendientes posteriores
1. Ejecutar suite completa y checks globales antes de merge final.
2. Definir política contable para diferencias de precio cuando se permita generar ajustes.
3. Crear migración formal del esquema si el proyecto adopta migraciones para instalaciones existentes.

## 2026-05-06 (cierre de brechas restantes de Conciliación de Compras)

### Peticion del usuario
Implementar el plan para completar lo pendiente de `requerimiento.md`: matching agregado real por producto/UOM, estados derivados completos, cancelación 2-way, cuenta puente opcional, pruebas faltantes y documentación final, manteniendo "Conciliación de Compras" como nombre funcional.

### Decisiones de diseño
- Las diferencias fuera de tolerancia generan una conciliación `disputed` con evento `MATCH_FAILED`, pero no crean líneas conciliadas para no consumir disponibilidad.
- La evaluación se hace por agregados `(item_code, uom)` y los detalles se crean únicamente cuando el resultado no es fallido.
- `bridge_account_required=False` permite que `PurchaseReceipt` genere stock ledger y evento operativo sin bloquear por falta de cuenta puente ni crear GL puente.
- `gr_ir_service.py` sigue solo como shim legacy; no se reintroduce GR/IR como dominio funcional.

### Plan implementado
1. Reemplazar el uso decorativo de agrupación por agregados reales de cantidad, monto y precio promedio.
2. Evaluar explícitamente diferencias de cantidad, precio y monto contra tolerancias configuradas.
3. Centralizar derivación de estados desde resultado y cobertura de cantidades.
4. Evitar creación de `PurchaseReconciliationItem` cuando el matching termina en `MATCH_FAILED`.
5. Cancelar conciliaciones de facturas 2-way y 3-way desde `cancel_document`.
6. Honrar `bridge_account_required` en `post_purchase_receipt`.
7. Agregar pruebas de agregación, disputa sin consumo, cancelación 2-way, cuenta puente opcional y panel mixto.
8. Actualizar `ESTADO_ACTUAL.md`, `PENDIENTE.md` y `SESSIONS.md`.

### Resumen tecnico de cambios
- `cacao_accounting/compras/purchase_reconciliation_service.py`: agregados internos por producto/UOM, evaluación de cantidad/precio/monto, estado derivado centralizado y disputas sin consumo de cantidades.
- `cacao_accounting/contabilidad/posting.py`: cancelación de `PurchaseInvoice` ahora cubre conciliaciones con `purchase_order_id`; `PurchaseReceipt` respeta `bridge_account_required`.
- `tests/test_08_reconciliation_reports.py`: cobertura nueva para agregación 2-way, disponibilidad tras disputa, cancelación 2-way, cuenta puente opcional y panel con 2-way/3-way.
- `ESTADO_ACTUAL.md` y `PENDIENTE.md`: actualizados con el estado real.

### Verificacion ejecutada
- `python -m py_compile cacao_accounting/compras/purchase_reconciliation_service.py cacao_accounting/contabilidad/posting.py tests/test_08_reconciliation_reports.py` -> sin errores.
- `ruff check cacao_accounting/compras/purchase_reconciliation_service.py cacao_accounting/contabilidad/posting.py tests/test_08_reconciliation_reports.py` -> passed.
- `pytest -q tests/test_08_reconciliation_reports.py -q` -> 19 passed.
- `black cacao_accounting/compras/purchase_reconciliation_service.py cacao_accounting/contabilidad/posting.py tests/test_08_reconciliation_reports.py` -> sin cambios pendientes.
- `ruff check .` -> passed.
- `flake8 cacao_accounting tests --max-line-length=130` -> passed.
- `mypy cacao_accounting` -> Success: no issues found in 64 source files.
- `pytest -q tests/test_08_reconciliation_reports.py tests/test_07posting_engine.py tests/test_04database_schema.py` -> 230 passed.
- `pytest -q` -> 305 passed, 4 warnings externas de Flask-Caching/deprecación.

## 2026-05-06 (catálogo base, cuentas predeterminadas y tipos de cuenta)

### Peticion del usuario
Implementar un catálogo base completo para las cuentas que el sistema requiere, agregar mapping JSON por catálogo predefinido, aplicar ese mapping al crear compañías desde setup, crear CRUD administrativo de cuentas por defecto y aplicar restricción estricta por `account_type`.

### Decisiones de diseño
- Los tipos de cuenta son strings en inglés sobre `Accounts.account_type`.
- Una cuenta sin `account_type` explícito permite afectación libre.
- Una cuenta con tipo especial se valida contra el origen del posting antes de persistir `GLEntry`.
- Cada catálogo ofrecido por el setup debe tener un JSON compañero con el mismo nombre base; para `base_es.csv` se creó `base_es.json` y para `base_en.csv` se creó `base_en.json`.
- La cuenta puente de compras sigue nombrada como `bridge`; no se reintroduce GR/IR como nombre funcional.

### Lista de cuentas predeterminadas requeridas
`default_cash`, `default_bank`, `default_receivable`, `default_payable`, `default_income`, `default_expense`, `default_inventory`, `default_cogs`, `inventory_adjustment_account_id`, `bridge_account_id`, `customer_advance_account_id`, `supplier_advance_account_id`, `bank_difference_account_id`, `default_sales_tax_account_id`, `default_purchase_tax_account_id`, `default_rounding_account_id`, `exchange_gain_account_id`, `exchange_loss_account_id`, `unrealized_exchange_gain_account_id`, `unrealized_exchange_loss_account_id`, `deferred_income_account_id`, `deferred_expense_account_id`, `payment_discount_account_id`, `period_profit_loss_account_id`, `retained_earnings_account_id`.

### Plan implementado
1. Extender `CompanyDefaultAccount` con todos los campos de cuenta requeridos por el motor actual.
2. Crear `contabilidad/default_accounts.py` con definiciones, validación de asignaciones, carga de mapping JSON y enforcement de uso por `account_type`.
3. Actualizar el cargador de catálogos para aceptar cabeceras en inglés y español, incluyendo `account_type` / `tipo_cuenta`.
4. Actualizar `base_es.csv`: columna `account_type`, cuentas nuevas faltantes, tipos en inglés y eliminación de códigos duplicados.
5. Crear `base_es.json` con el mapping completo para inicialización automática y `base_en.json` como mapping equivalente para el catálogo inglés.
6. Cambiar setup para ofrecer únicamente catálogos con JSON compañero y aplicar defaults al finalizar.
7. Agregar `/settings/default-accounts` con UI en dos columnas y CRUD de configuración por compañía.
8. Conectar posting a la validación estricta de tipos y a los nuevos defaults para COGS, ajustes de inventario e impuestos por defecto.
9. Agregar pruebas de catálogo bilingüe, mapping completo, setup, CRUD admin, enforcement manual y fallback de impuestos.

### Resumen tecnico de cambios
- `cacao_accounting/contabilidad/default_accounts.py`: servicio central para campos requeridos, compatibilidad de tipos, mapping JSON y validación de GL.
- `cacao_accounting/contabilidad/ctas/catalogos/base_es.csv` y `base_es.json`: catálogo base completo en español y mapping predeterminado. `cacao_accounting/contabilidad/ctas/catalogos/base_en.csv` y `base_en.json`: catálogo base completo en inglés y mapping predeterminado.
- `cacao_accounting/setup/service.py`: solo ofrece catálogos con mapping y aplica `CompanyDefaultAccount`.
- `cacao_accounting/admin/__init__.py` y `admin/default_accounts.html`: CRUD de cuentas por defecto.
- `cacao_accounting/contabilidad/posting.py`: enforcement por `account_type`, COGS/defaults de inventario e impuestos con fallback.
- `tests/test_04database_schema.py`, `tests/test_07posting_engine.py`, `tests/test_08_reconciliation_reports.py`: cobertura de esquema, enforcement y configuración.

### Verificacion ejecutada
- `python -m py_compile` sobre archivos tocados -> sin errores.
- `ruff check` sobre archivos tocados -> passed.
- `flake8` sobre archivos tocados con `--max-line-length=130` -> passed.
- `mypy cacao_accounting/contabilidad/default_accounts.py cacao_accounting/setup/service.py cacao_accounting/admin/__init__.py cacao_accounting/contabilidad/posting.py` -> passed.
- `pytest -q tests/test_08_reconciliation_reports.py tests/test_07posting_engine.py tests/test_04database_schema.py` -> 237 passed, 3 warnings externas/deprecación.
- `black .` -> 4 archivos reformateados (`default_accounts.py`, `admin/__init__.py`, `run.py`, `wsgi.py`).
- `ruff check .` -> passed.
- `flake8 cacao_accounting tests --max-line-length=130` -> passed.
- `mypy cacao_accounting` -> Success: no issues found in 65 source files.
- `pytest -q` -> 312 passed, 7 warnings externas/deprecación.

## 2026-05-06 (Smart Select Framework y cuentas por defecto)

### Peticion del usuario
Implementar un framework transversal robusto para campos select/autocomplete, sin migrar todos los formularios de una vez, usando `/settings/default-accounts` como primer formulario piloto. Tambien crear instrucciones permanentes para futuras migraciones y actualizar la bitacora/documentacion del proyecto.

### Decisiones de diseño
- El backend usa un registry explicito de doctypes permitidos y rechaza doctypes/filtros no registrados.
- El primer corte migra solo `/settings/default-accounts`; compras, ventas, bancos, inventario y GL quedan para migracion progresiva.
- El frontend usa una unica libreria Alpine.js (`smart-select.js`) y no renderiza catalogos grandes dentro del HTML.
- La validacion final sigue en servicios backend (`upsert_company_default_accounts`); Smart Select mejora UX y reduce opciones invalidas, pero no sustituye reglas de negocio.
- Se agrego versionado de URL del asset JS para evitar que el navegador conserve una version anterior del componente.

### Plan implementado
1. Crear `cacao_accounting/search_select.py` con servicio generico, registry, filtros permitidos, busqueda por campos configurados y serializacion uniforme.
2. Agregar `GET /api/search-select` autenticado para devolver opciones filtradas.
3. Crear `cacao_accounting/static/js/smart-select.js` como componente Alpine reusable con loading, errores, sin resultados, valor inicial, limpieza y filtros dinamicos.
4. Agregar estilos genericos `.ca-smart-select*` en `cacao_accounting/static/css/cacaoaccounting.css`.
5. Refactorizar `admin/default_accounts.html` para usar Smart Select por cada cuenta predeterminada, filtrando por compania y tipos compatibles.
6. Crear `.github/instructions/search-select-fields.instructions.md` para guiar futuras implementaciones.
7. Agregar pruebas de servicio, API y vista para el caso piloto.
8. Actualizar `ESTADO_ACTUAL.md` y `PENDIENTE.md`.

### Resumen tecnico de cambios
- `cacao_accounting/search_select.py`: registry inicial para `account`, `customer`, `supplier`, `item`, `warehouse`, `bank_account` y `naming_series`.
- `cacao_accounting/api/__init__.py`: endpoint `/api/search-select`.
- `cacao_accounting/static/js/smart-select.js`: componente Alpine con seleccion asistida y manejo de valores iniciales validos.
- `cacao_accounting/templates/macros.html`: carga global del componente con version de asset.
- `cacao_accounting/admin/templates/admin/default_accounts.html`: reemplazo de selects de cuentas por Smart Select filtrado.
- `tests/test_08_reconciliation_reports.py`: cobertura de busqueda, filtros, limites, errores de registry/API y renderizado sin opciones masivas.

### Verificacion ejecutada
- `python -m py_compile cacao_accounting/search_select.py cacao_accounting/api/__init__.py cacao_accounting/admin/__init__.py` -> sin errores.
- `ruff check cacao_accounting/search_select.py cacao_accounting/api/__init__.py cacao_accounting/admin/__init__.py tests/test_08_reconciliation_reports.py` -> passed.
- `pytest -q tests/test_08_reconciliation_reports.py -k 'search_select or default_accounts_view or default_account_admin'` -> 4 passed, 4 warnings externas/deprecación.
- `black cacao_accounting/search_select.py cacao_accounting/api/__init__.py cacao_accounting/admin/__init__.py tests/test_08_reconciliation_reports.py` -> sin cambios pendientes tras formateo.
- `ruff check .` -> passed.
- `flake8 cacao_accounting tests --max-line-length=130` -> passed.
- `mypy cacao_accounting` -> Success: no issues found in 66 source files.
- `pytest -q tests/test_03webactions.py::test_inventory_stock_entry_routes --slow=True -vv` -> passed.
- `CACAO_TEST=True LOGURU_LEVEL=WARNING SECRET_KEY=ASD123kljaAddS python -m pytest -v -s --exitfirst --slow=True` -> falla antes de ejecutar las pruebas nuevas: `tests/test_03webactions.py::test_inventory_stock_entry_routes` recibe 404 en `/buying/purchase-receipt/REC-DEMO-0000001`; el mismo test pasa aislado, por lo que queda como fallo de interacción/estado de la suite lenta no relacionado con Smart Select.

## 2026-05-06 (alias y estado del selector de catálogos en setup)

### Peticion del usuario
En el último paso del setup inicial, deshabilitar el selector de catálogos de cuentas cuando el usuario seleccione catálogo en blanco. Además, mantener el nombre de archivo como valor técnico del selector, pero mostrar alias al usuario: `Predeterminado - ES` para `base_es.csv` y `Default - EN` para `base_en.csv`.

### Plan implementado
1. Agregar un mapping explícito de alias en el servicio que enumera catálogos disponibles.
2. Mantener el filename como value del `SelectField` para no romper la carga de catálogos ni `finalize_setup`.
3. Usar Alpine.js en el paso 3 del setup para deshabilitar `catalogo_origen` cuando `catalogo == "en_cero"`.
4. Actualizar la prueba que valida los catálogos ofrecidos y sincronizar documentación de estado/backlog.

### Resumen tecnico de cambios
- `cacao_accounting/setup/service.py`: nuevo `CATALOG_FILE_ALIASES` y `catalog_display_name`; `available_catalog_files()` devuelve `(filename, alias)`.
- `cacao_accounting/setup/templates/setup.html`: el fieldset de catálogo usa estado Alpine y deshabilita el select de catálogo existente al elegir catálogo en cero.
- `tests/test_08_reconciliation_reports.py`: expectativa actualizada para alias visibles.
- `ESTADO_ACTUAL.md` y `PENDIENTE.md`: documentan el comportamiento del setup.

### Verificacion ejecutada
- `black cacao_accounting/setup/service.py tests/test_08_reconciliation_reports.py` -> sin cambios pendientes.
- `python -m py_compile cacao_accounting/setup/service.py cacao_accounting/setup/forms.py` -> sin errores.
- `ruff check cacao_accounting/setup/service.py cacao_accounting/setup/forms.py tests/test_08_reconciliation_reports.py` -> passed.
- `flake8 cacao_accounting/setup tests/test_08_reconciliation_reports.py --max-line-length=130` -> passed.
- `mypy cacao_accounting/setup/service.py cacao_accounting/setup/forms.py` -> passed.
- `pytest -q tests/test_08_reconciliation_reports.py::test_setup_with_predefined_catalog_creates_complete_company_defaults -q` -> passed.
- `git diff --check` -> passed.
