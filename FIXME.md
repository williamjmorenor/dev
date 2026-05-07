Para trabajar en estos issues primeto debes cargar el contexto disponible de:

- AGENTS.md
- ESTADO_ACTUAL.md
- SESSIONS.md
- PENDIENTE.md

Los siguientes directorios contienen contexto adicional:

- .github/instructions
- modulos

Al finalizar cada iteración actualiza:

- ESTADO_ACTUAL.md
- SESSIONS.md
- PENDIENTE.md


Issues actuales que deben corregirse:

- No esta clara la diferencia entre Año Fiscal y Período Contable, hay que aclarar ambos conceptos:

Año fiscal es el contenedor de los periodos fiscales.

Un año Fiscal puede tener varios años fiscales asociados.

Un año fiscal representa un ejercicio contable completo.

Un periodo contable es una periodo de tiempo definido dentro de un año contable.

Si un Año Fiscal se cierra el ledger debe rechazar cualquier movimiento asociado a ese año fiscal.

Si un periodo contable se cierra no es un cierre definitivo, puede seguir recibiendo movimiento unicamente desde el modulo contable, es decir cerrar un periodo contable equivale al cierre de transacciones operativas: Bancos, Compras, Ventas e Inventarios.

Al cerrrar un periodo contable puede ser trabajando en el periodo en transacciones no operativas, para tal motivo el comprobante contable debe tener una una bandera boolena is_closing.

La unica diferencia entre ambos registros es esa bandera boolena.

Manejarlo a nivel de UX como un selector Etapa de Cierre: Operativo / Cierre

Al crear una empresa en el sistema crear el año actual como año fiscal y los doce periodos contable respectivos

Agregar en el setup inicial y en el formulario de creación de empresa la opción de inicio año fiscal (mes/día) fin del año fiscal (mes/día) para permtir periodos fiscales que inician a mediados de un año y finalizan el siguiente.

El comprobante contable no tiene selector de moneda. El servicio de posting debe recibir el comprobante contable con la moneda definida por el usuario y en backend hacer la conversión a la moneda definida en el libro contable.

Para esa conversión se requiere el tipo de cambio registrado.

Advertir al usuario si no existe tipo de cambio disponible para la moneda del registro y todas las monedas que requieran los libros contables activos.

