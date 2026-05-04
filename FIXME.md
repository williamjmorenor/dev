- no se estan usando series e identificadores según se definio en modulos/contexto/series.md se requiere refactor masivo para alinear los registros del sistema para alinear los registros del sistema para usar la definición de series e indentificadores definida

- en el modulo de administración debe existir la opción de administrar series e identificadores un registro puede tener varios identificadores y el formulario de crear debe tener un selector para seleccionar la serie, la serie debe estar asociada a la compañia es decir el usurio debe seleccionar la compañia y el sistema solo debe mostrar las series disponibles para ese documento asociados a esa compañia

- en todo registro siempre debe haber campos para compañia, serie, fecha de contabilización

- todo registro debe especificar moneda del registro

- la fecha de contabilización desde respetar si el periodo contable esta abierto o cerrado

- todas las listas deben tener un boton "Nuevo #####"

- /cash_management/payment/new incluye tres tipos Cobro / Pago / Transferencia Interna de debe mover Transferencia Interna a una transacción independiente

- /cash_management/payment/new la logica del formulario es incompleta a como se definio en modulos/contexto/aging.md el pago debe asociarte a un registro 

- /cash_management/cash no estan mapeados todos lo registros definidos en modulos/contexto/registros_overview.md

- /accounting/ solo tiene mapeado un tipo de registro "Comprobantes Contables" no estan definidos los registros definidos en modulos/contexto/registros_overview.md

- /accounting/gl/new totalmente desacoplado del backend

- /cash_management/bank/list no boton "Nuevo Banco"

- /cash_management/bank/list la lista de bancos no permite acceder a registro del banco

- /buying/supplier/list no hay boton a "Nuevo Proveedor"

- /buying/supplier/new totalmente infuncional

- /buying/purchase-order/list no hay boton "Nueva Orden de Compra"

- /buying/purchase-order/new incompleto y con errores de html

- /buying/purchase-receipt/list esto debe estar compartido entre los modulos de almacen y compras, el almacen debe recepcionar bienes inventariables compras puede recepcionar servicios o bienes no inventariables

- /buying/purchase-receipt/new incompleto y con errores de html

- /buying/purchase-invoice/list no hay boton "Nueva Factura"

- /buying/purchase-invoice/new incompleto y con errores de html