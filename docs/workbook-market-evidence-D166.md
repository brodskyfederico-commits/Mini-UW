# Si invierto USD 10, ¿cuánto cobro y cuándo?

D166 · Control de mercado, seguro y banco para el piloto sintético. Las cifras corresponden al equity agregado del proyecto. El aporte inicial de ambos escenarios es USD 10 el 30/03/2027.

| Por USD 10 iniciales | Base | Downside |
|---|---|---|
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| Total cobrado | USD 19,10 | USD 6,80 |
| Ganancia o déficit de caja | +USD 4,23 | −USD 11,39 |
| Múltiplo sobre todos los aportes | 1,28x | 0,37x |
| Sin recuperar al cierre | USD 0,00 | USD 11,39 |

El PDF de una página lista cada aporte adicional por fecha. Los totales usan cifras sin redondear. Con respaldos completos se reproducen las fechas, cobros y capacidad de D164. El retorno personal y el dictamen real siguen PENDING.

## Control previo al cálculo

La nueva versión del caso requiere cinco respaldos estructurados por escenario. B08 valida su huella, referencia, vigencia, caso, escenario, unidad y base. El expediente guarda el valor de la planilla, su ubicación y el dato de respaldo. Las bandas son datos del ejemplo sintético.

| Supuesto o dato | Evidencia exigida en el piloto | Comparación |
|---|---|---|
| Renta residencial por tipo (C8–C11) | Rango documentado por tipo de unidad y base de renta declarada en C7 | Inclusión exacta en cada rango, incluidos sus extremos |
| Concesiones (C15) | Rango y base de concesiones aplicable | Fracción sobre la misma base |
| Absorción (C47) | Rango de meses entre TCO y estabilización | Duración de la planilla dentro del rango |
| Tasa de salida (C67) | Rango anual compatible con NOI de los 12 meses posteriores | Cotejo del escenario de origen y de la alternativa C80, cuando se solicita |
| Seguro (C59) | Cotización con prima anual por unidad asegurada, número de unidades y referencia de cobertura | Coincidencia exacta de los tres campos |
| Préstamos de obra y permanentes | PDF de evidencia bancaria del perfil D164 | OCR cotejado con la planilla y los términos complementarios; LTV y DSCR se calculan después |

La vigencia se evalúa a la fecha del expediente. Si falta respaldo o hay una diferencia, se retiran el NOI, la capacidad y los cobros del escenario afectado. Una alternativa fuera de su rango queda PENDING y conserva la corrida respaldada del escenario de origen. B16 reproduce el expediente. El registro de esta versión ubica B08 antes de B09 y las pruebas B17 fuera de la corrida por proyecto.

## Casos de prueba

| Variante | Resultado esperado |
|---|---|
| Falta el respaldo de absorción de Base | Base PENDING |
| Downside tiene prima distinta, concesiones vencidas y renta fuera del rango | Downside PENDING con los tres motivos |
| La tasa de salida Base está expresada en otra unidad | Base PENDING |
| Cambia la cotización de Downside y su huella queda desactualizada | Downside PENDING |
| C80 de Base queda fuera del rango y C67 sigue respaldada | C80 Base PENDING y corrida de origen disponible |
| El OCR de Downside discrepa de los términos en la capa de texto | Downside PENDING |
| El PDF de Downside difiere del plazo cargado en los términos complementarios | Downside PENDING con el campo discrepante |

Quedan pendientes la extracción y revisión de comparables y cotizaciones de seguro reales, la autoridad de las fuentes, los criterios de selección de comparables y la validación con documentos bancarios reales. D166 conserva el cotejo bancario sintético y usa registros estructurados de mercado y seguro para probar el control.

## Reproducción en el VPS

El script genera el PDF bancario sintético a partir de D164 y verifica su recorrido con el caso y la revisión vigentes de D166. Usá el [runtime OCR del piloto](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_market_evidence_D166.py --output /tmp/miniuw-d166
```
