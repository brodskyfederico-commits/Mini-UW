# Caja del equity, calendario de retorno y comparación — contratos candidatos

Se vinculan las referencias del ledger con M7 y las condiciones de M9. Los nuevos contratos son `investor-return-bridge.schema.json` y `return-metric-bridge.schema.json`; las referencias son `validate_investor_return_bridge.py` y `validate_return_metric_bridge.py`. Todos los ejemplos son sintéticos; no se completa ningún criterio real.

## Caja bruta y neta

Se exige conciliación del ledger de origen antes de calcular retornos. Todos y sólo los eventos clasificados como aporte o distribución del equity agregado del proyecto necesitan un vínculo temporal explícito. IDs duplicados, eventos omitidos y referencias inexistentes se rechazan. La clasificación documental de un movimiento no se autentica por introducirlo en este contrato.

Por punto se conservan los IDs y sumas brutas A/D; el flujo neto es D−A. El múltiplo usa suma(D)/suma(A), no las partes positivas/negativas del vector neto. Aportes cero dejan el múltiplo indefinido. Banco, operación, venta y reservas no se convierten automáticamente en distribuciones del inversor. La referencia no añade valor terminal, proceeds hipotéticos ni caja retenida al retorno.

Ejemplo existente: aportes 15, distribuciones 5, múltiplo 1/3 y vector neto [-10,0]. Agregar un aporte y una distribución documentados de 5 deja igual el neto pero cambia el múltiplo a 1/2. Esta prueba demuestra por qué no se reconstruyen brutos desde el neto; no justifica generar movimientos circulares.

## Cuadrícula temporal expresa

Cada punto tiene índice consecutivo desde cero, fecha y período del calendario. Los puntos sin movimientos se mantienen como ceros explícitos de agregación de un ledger proporcionado; eso no prueba que falten cero movimientos en la realidad. No se comprime un intervalo vacío para aumentar el retorno.

Se admiten pasos expresos en días fijos o meses de calendario conservando el mismo día. Fechas incompatibles con el paso se rechazan; no se ajusta fin de mes o año bisiesto automáticamente. Febrero/marzo pueden tener distinta duración real y ser un paso mensual declarado; eso no habilita XIRR o una convención bancaria.

Cada evento exige coincidencia exacta de fecha o asignación explícita al punto dentro del mismo período del calendario, con referencia de evidencia/regla. La asignación a bucket es una aproximación temporal declarada, no una detección del momento económico ni una regla aprobada. Cruces de período y otros ajustes necesitan contratos separados. Los costos de financiación no se reinterpretan como equity por su signo.

## TIR y relación con el criterio

El vector neto completo alimenta el aislamiento periódico existente con ancho de intervalo y límite de bisecciones expresos. Se conserva el estado del aislamiento: ledger conciliado no significa TIR determinada. Polinomio cero, sin raíces, múltiples raíces o trabajo agotado permanecen diferenciados. No se elige la tasa más favorable.

La comparación exige contexto, identidad/definición de métrica, unidad adimensional, base/horizonte y operador compatibles con el criterio expreso. Faltantes/conflictos conservan sus afirmaciones y causas. Aplicabilidad no resuelta o exclusión requieren tratamiento separado; no se usa una exclusión para certificar el conjunto.

Con una raíz aislada, se compara el intervalo entero, conservando extremos abiertos/cerrados. Si todos sus valores satisfacen la condición, la relación es verdadera; si todos la incumplen, falsa. Si el umbral cruza el intervalo, queda pendiente de refinamiento. No se decide con punto medio, redondeo o tolerancia supuesta. Una relación individual verdadera o falsa no es un PASS/FAIL del deal ni aplica una agregación de la casa.

## Anualización condicionada

La tasa periódica se mantiene sin anualizar por defecto del registro. Una métrica anual necesita frecuencia y regla expresas: para un paso declarado de meses, pasos por año multiplicados por meses por paso deben ser 12. Sólo entonces se transforma cada extremo con `(1+r)^m−1`, conservando su apertura/cierre por monotonía. Esto comprueba coherencia matemática de parámetros suministrados, no autoridad de esa política. Una cuadrícula en días queda pendiente de una convención de año; no se supone 365, 360 o Actual/Actual.

## Evidencia y límites

Se retienen 43 controles del puente caja/calendario/retornos y 31 del puente métrica/criterio; estos últimos incluyen una tabla exhaustiva de 180 combinaciones de extremos, operadores y umbrales. Hay ejemplos de dos raíces desde un ledger conciliado, períodos sin flujos, brutos distintos con neto igual, bloqueo por discrepancias y anualización condicionada.

No acreditan completitud de los movimientos originales, fuentes auténticas, LP/JV/waterfall, fiscalidad, valor terminal, XIRR, agregación de escenarios, auditoría independiente, aprobación profesional o producción. Todas las salidas conservan PENDING a nivel deal y publicación desautorizada. Los originales, R02 y la plantilla real vacía se preservan.
