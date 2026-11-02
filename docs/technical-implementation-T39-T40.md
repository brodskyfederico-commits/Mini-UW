# T39–T40 — revisión de venta desde fuentes hasta caja y retorno

Dentro del alcance Mini-UW de renta/refinanciación/venta de activo, se pasa de editar un cobro neto aislado a recalcular el cierre de venta desde proceeds brutos y costos de cierre suministrados. El resto de las fuentes se mantiene bajo hipótesis explícita. No se implementa una regla fiscal, comisión porcentual, escenario de mercado completo, venta por unidades ni Full UW.

## T39: revisión de fuente de venta

Entrada: evidencia tipada completa T36 y especificación estricta, con revisión identificada, hash del inventario íntegro de fuentes/resultados/bindings, ID del cierre de venta y referencia de la hipótesis de mantener otros inputs fijos. Proceeds y costos se reciben como dos declaraciones monetarias completas con valor/moneda/fecha/base/fuente, incluyendo cero explícito. La hipótesis de financiación de un aporte necesario también es explícita o ausente; nunca acredita fondos disponibles.

Se verifica primero el replay exacto de T36, incluso si su resultado está bloqueado. Solo se sustituyen esas dos declaraciones y la referencia de financiación del cierre seleccionado. Se conservan fecha/contexto, préstamos y obligaciones, operaciones, refi, saldos, reservas, retención, valuación declarada y targets del inversor. Se identifican revisiones de fuente mediante su ID/hash; no se les atribuye un escenario Downside ni se renombra el contexto de toda la cadena.

La revisión reproduce cierre T29, comprobación de deuda T31, manifiesto/continuidad T33 y camino guardado T36. Se actualizan únicamente las huellas del cierre, su binding de deuda, el nodo de venta en el manifiesto y las referencias del binding de retorno al nuevo manifiesto/resultado. Los límites de capacidad, NOI bancario, préstamo y cierre de refinanciación siguen idénticos; no se modifican para permitir un retorno. Un bloqueo bancario preservado impide compilar el ledger del inversor aunque la caja revisada cuadre.

Un cierre puede mostrar distribución positiva o aporte necesario separado. Para exportar un aporte requiere hipótesis de financiación y un target bruto de contribución vacío explícitamente configurado. No se crea ese target automáticamente, no se presume que alguien financiará la brecha y no se convierte cash-in en distribución negativa. Si falta dato, fecha/moneda/base/fuente o una regla requerida, la etapa afectada bloquea; no publica retorno parcial. Resultados intermedios de cierre/deuda/caja con sus bloqueos permanecen visibles.

Solo si el camino guardado compila se agrega T37 sobre el ledger producido, con cobros/aportes brutos, resultado, brecha al corte, pico de equity, EM e IRR desde sus productores. Retorno personal y pérdida económica final permanecen pendientes. Un error sintáctico o evidencia alterada se rechaza; un caso financieramente incompleto se conserva bloqueado. `recover_sale_revision` verifica todo el reporte y devuelve la cadena revisada reproducida; no confía en hashes autoafirmados.

## T40: comparación de revisiones explícitas

Se compara un inventario acotado de especificaciones T39 contra la misma evidencia base. Cada especificación debe tener hash de base e ID de revisión únicos/coherentes. La tabla muestra claims de proceeds/costos, estado de cierre/deuda/caja/financiación, aporte/distribución proyectados y, únicamente cuando se generaron por el camino guardado, cobros, resultado, EM e IRR del proyecto. Un caso bloqueado no se elimina ni se trata como retorno cero. No se calcula un promedio o un "mejor" caso que oculte faltantes. Un inventario incompleto bloquea la afirmación de comparación completa.

La comparación no añade por defecto casos, shocks, tolerancias, probabilidades o criterios. Las revisiones no adoptan políticas ni autorizan inversiones; todos los estados decisorios siguen PENDING. Se conserva el bloqueo original de T35/T36; una prueba de software compatible es una hipótesis independiente explícita, sin reemplazar los archivos anteriores.

## Límites y validación

No se recalculan automáticamente impuestos/costos como función del precio, calendario de venta, prepago contractual no suministrado, refinanciación alternativa, construcción previa, cobros personales LP/JV o disponibilidad real de capital. La valuación declarada no se transforma en cobro de venta. No hay precio/exit cap de equilibrio financiero completo, despliegue o decisiones reales.

La evidencia registra fuentes originales y revisadas, hashes de código/definición/resultados, cambios con localizadores y replay compatible. No se agrega un bundle SQLite runtime; la recuperación exige conservar los inputs originales y especificaciones además del reporte. Las pruebas verifican identidades de caja, costo y proceeds independientes, deuda/retención sin cambios, cash-in separado, fuentes manipuladas, bloqueo bancario, targets incompletos y recuperación del reporte. Los casos financieros de aceptación originales continúan abiertos.
