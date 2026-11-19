# Si invierto USD 10, ¿cuánto cobro y cuándo?

D263 resuelve, en el contrato optativo de sensibilidades v11 de C69–C72, el bloqueo de precisión detectado en D262. La tasa Base de **5,01 %** se conserva y llega al cierre y a la caja por USD 10 sin redondear. Downside se prueba con **6,51 %**. Son datos sintéticos con PDF bancario y anexo verificados; no corresponden al 1101 ni a One Hollywood. El dictamen real y el retorno personal sin términos de reparto siguen PENDING.

## Resultado del ensayo

El equity inicial del proyecto es USD 2.400.000, verificado en el perfil D200. Se mantiene el factor `10 / 2.400.000`, sin usar los aportes posteriores como denominador. El ensayo conserva los otros cambios de D262: amortización a 21/12 años, LTV máximo a 64,99 % y DSCR mínimo a 1,251/1,301, respectivamente. La solicitud de refi sigue fija en USD 1.400.000. No son criterios nuevos ni recomendaciones de financiación.

| Corrida | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar al vender |
|---|---:|---:|---:|---:|
| Base original, C69 = 5,00 % | 10,00000000 | 4,86704167 | 18,05935435 | 0,00000000 |
| Base conjunto v11, C69 = 5,01 % | 10,00000000 | 4,86704167 | 18,05920852 | 0,00000000 |
| Downside original, C69 = 6,50 % | 10,00000000 | 8,18934167 | 6,07670398 | 12,11263769 |
| Downside conjunto v11, C69 = 6,51 % | 10,00000000 | 8,18934167 | 6,07655815 | 12,11278352 |

USD por USD 10 iniciales. Los números se presentan con ocho decimales; los cálculos conservan numerador y denominador exactos. La caja sin recuperar compara todos los aportes con los cobros hasta el cierre y no certifica una pérdida económica final.

| Movimiento del conjunto | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00000000 | 10,00000000 |
| Aporte · 30/06/2027 | — | 0,76227500 |
| Aporte · 30/09/2027 | 4,65537500 | 0,03572917 |
| Aporte · 30/12/2027 | 0,05291667 | 7,03404583 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,05291667 cada fecha | 0,07145833 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,07145833 cada fecha |
| Cobro neto de refi | 2,84666667 · 30/09/2028 | 2,44583333 · 30/03/2029 |
| Cobro de operación | 1,43416697 · 30/12/2028 | 0,56023938 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 13,77837487 · 30/12/2028 | 3,07048544 · 30/06/2029 |

El aporte operativo explícito cero se conserva en los eventos. El aumento de tasa reduce el cobro conjunto en USD 0,0001458333 por USD 10: `1.400.000 × 0,0001 / 4 × 10 / 2.400.000`. En este calendario hay una cuota antes de cancelar el préstamo al vender. El cambio de amortización redistribuye operación y venta, conservando su suma si la tasa no cambia. La prueba compara también el cronograma completo y no generaliza esa identidad a otra duración.

## Corrección técnica y versión

El cronograma de D262 ya calculaba correctamente 5,01 %, pero el principal de la cuota generaba 370/366 dígitos de numerador/denominador. Los lectores de los puentes de caja sólo admitían 256 por entero. D263 amplía el transporte exacto a **1.300 dígitos**, conservando el presupuesto aritmético existente de **4.096 bits**, los límites de archivos y el rechazo de datos inválidos. No aplica redondeos, conversión a punto flotante ni sustitución de valores.

El contrato `miniuw.synthetic-worksheet-sensitivities.v11` conserva el inventario de cambios y respaldos de v10. Selecciona un motor de caja con dependencias aisladas para las variantes C69–C72. Las funciones financieras se reutilizan con su mismo código, en espacios de ejecución privados que enlazan los lectores y productores compatibles. No se modifican las variables globales ni los archivos de los módulos anteriores.

Cada variante registra `exact_cash_transport`: perfil, revisión, hash del adaptador, algoritmos y dependencias con sus rutas y SHA-256, límite de dígitos, presupuesto aritmético y ausencia de redondeo. Las huellas de los productores adaptados combinan el hash del algoritmo con la revisión del transporte. Se verifican once fuentes; un cambio de algoritmo no revisado deja PENDING, sin volver automáticamente al motor anterior.

La cadena adaptada comprende NOI a caja, refi, capacidad, cancelación de deuda a la venta, cierre, eventos brutos y retorno. Los tipos, unidades, períodos, ecuaciones, fuentes y controles financieros se conservan. La modificación amplía el dominio numérico, sin adoptar una política financiera o de redondeo.

### Alcance de la activación

V11 es optativo y se aplica a estas sensibilidades documentadas. La corrida de entrada original y los otros contratos conservan su motor y sus reglas. D262 sigue reproduciendo el PENDING histórico de su caso de 5,01 % con v10; D263 calcula esa variante al solicitar v11. No se reescriben expedientes ni se activa un cambio general por defecto. La integración de este transporte en otros productores o en una entrada original que ya supere el dominio anterior requiere su propia revisión y pruebas.

## Cobertura y evidencia

| Requisito o variable | Ubicación / definición | Cálculo y validación | Estado |
|---|---|---|---|
| C69 = 5,01 % Base | `Inputs!A69:F69`, cambio explícito con PDF/anexo de D262 | Cuota, intereses, saldo y flujos exactos por USD 10 | Calculado en v11; v10 conserva su estado anterior |
| C70–C72 aislados y conjunto | `Inputs!A70:F72`, mismos términos y vencimientos documentados | Ocho cambios individuales y dos conjuntos; pago, LTV, DSCR, debt yield y fuentes/usos | Calculados en el ensayo sintético compatible |
| Mayor precisión sin redondeo | `worksheet_exact_cash_D263.exact_fraction` | Fracciones mayores a 256 dígitos; rechazo sobre 1.300; cálculo adicional a 30 años con denominadores mayores a 500 dígitos | Verificado dentro del presupuesto aritmético |
| Aislamiento y versión | `worksheet_exact_cash_D263.cash_engine` | Dos motores creados concurrentemente, identidad del código, enlaces de dependencias y ausencia de mutación global; fuente no reconocida rechazada | Verificado, revisión explícita obligatoria |
| Vacío distinto de cero | Lector racional y contrato de cambio | `null`, cadena vacía, espacios, fuente ausente; tasa cero con interés cero | Faltantes PENDING; cero explícito conservado |
| Capacidad | Solicitud fija y menor límite aplicable | Refi sobre DSCR en Base o LTV en Downside | PENDING, sin cobro ficticio ni ajuste automático |
| Reproducción histórica y actual | B16 y revisión vigente externa | Comparación con D262 y reproducción del paquete nuevo | Cada contrato conserva su revisión |

Pruebas: `tests/test_worksheet_exact_cash.py`. `ExactCashTransportTests` verifica lector, aislamiento, versiones y límites. `ExactCashIntegrationTests.test_precision_case_full_cash_replay_and_legacy_compatibility` coteja v10/v11 en importes y fechas, calcula el caso antes bloqueado y concilia cronogramas y caja con fórmulas independientes. Las citas y huellas pueden cambiar entre versiones; se verifica separadamente que los importes compatibles permanezcan iguales.

## Reproducción y pendientes

Con el runtime de OCR del VPS, desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_exact_cash
```

Las reglas de Lorena, la evidencia, los términos de reparto y las aprobaciones reales conservan sus puertas. La precisión sigue acotada: una operación que exceda los presupuestos o carezca de fuente mantiene PENDING; no se garantiza cobertura ilimitada de tasas y plazos. La entrega externa del motor conserva un PDF de una página. Este documento es un registro técnico interno. Datos sintéticos, sin despliegue ni decisiones reales; el respaldo excluye credenciales, expedientes reales, paquetes generados y registros de ejecución.

Validación en el VPS: cinco pruebas nuevas distintas —la integrada y cuatro controles unitarios—, nueve controles anteriores, auditoría B16 del caso histórico D262 y reproducción B16 del paquete nuevo. El ensayo integrado y sus tres primeros controles pasaron en 262,452 segundos; el bloque unitario final pasó en 0,043 segundos. Se probaron ocho cambios individuales y dos conjuntos del caso antes bloqueado, equivalencia financiera v10/v11, 30 años, tasa cero, faltantes y capacidad excedida. Los diez archivos de consola y D198 coincidieron byte a byte. La batería general completa no se repitió en este hito.
