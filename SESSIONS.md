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
- El módulo de ventas no tiene ruta de lista ni creación de nota de crédito de cliente.
- El formulario de proveedor nuevo es no funcional (documentado en FIXME).
- `StockEntry` no genera `StockLedgerEntry` ni actualiza `StockBin` al hacer submit.
- La reconciliación bancaria, cierre de período y revalorización cambiaria tienen modelos pero sin UI ni servicio.

### Verificacion ejecutada
- Inspección completa de: modelos DB, rutas de todos los módulos, templates, API endpoints.
- Revisión de FIXME.md, SESSIONS.md previos, y todos los archivos de definición de módulos.

### Notas para siguiente iteracion
1. Priorizar implementación de posting contable (Bloque 1 de PENDIENTE.md).
2. Corregir formularios documentados como no funcionales en FIXME.md.
3. Implementar nota de crédito de venta (gap crítico en módulo ventas).

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
