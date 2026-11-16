# Si invierto USD 10, ¿cuánto cobro y cuándo?

La corrida de planilla sintética conserva los diez movimientos de Base y los trece de Downside, con las mismas fechas, montos exactos y PDF de D229. Base aporta USD 4,87 adicionales y cobra USD 2,85 al refinanciar el 30/09/2028 y USD 16,66 por operación y venta el 30/12/2028. Recupera todo el capital aportado. Downside aporta USD 8,19 adicionales y cobra USD 2,45 el 30/03/2029 y USD 4,68 por operación y venta el 30/06/2029. Quedan USD 11,06 sin recuperar. El PDF conserva el calendario completo. Los montos usan equity agregado del proyecto sintético.

## Conexión y controles

`rehearse-workbook` reproduce el expediente mediante B16, verifica su revisión vigente y aplica el perfil sintético D230 con el SHA-256 exacto de la configuración. El resultado interno vincula las huellas de la caja, el resultado y el PDF. La entrega sigue mostrando el dictamen real PENDING. Se conservan el dictamen y el retorno histórico del 1101 como PENDING.

| Métrica | Base y trazabilidad |
| --- | --- |
| YoC, spread y ocupación de equilibrio | Registros D193 con período y definición compatibles. El spread usa el NOI correspondiente a la base del cap comparable. |
| Recuperación y aporte en refi | Importes del cierre cotejados con el libro de caja y divididos por el equity aportado hasta estabilización. El cero del cierre queda explícito. |
| Equity/TDC | Equity aportado hasta estabilización sobre TDC reconciliado. |
| CoC posrefi | Ventana anual íntegra respaldada, NOI después de reservas, servicio de deuda y equity remanente. |
| Múltiplo y TIR | Distribuciones sobre aportes brutos e intervalo anual verificado de TIR del calendario de tenencia documentado. |
| RLV | Base. Búsqueda a deuda fija con C33 y los umbrales de D230. Exige que el límite cumpla las demás métricas Base y que el vecino superior falle un criterio de precio. Si el intervalo de precio cruza un umbral, la comparación queda pendiente. |

Tres controles en la capa de métricas usan los productores de caja, TIR, CoC, YoC, spread y ocupación del Mini-UW. Los tres conservan el mismo libro de aportes y cobros por fecha. El control de referencia cumple las 19 comparaciones aplicables. Un cap comparable de Downside distinto lleva el spread a la banda de **HOLD** económico. Un cap comparable de Base distinto lleva el spread por debajo del umbral de **FAIL** de Base. Los cambios corresponden al cap de referencia del spread. El precio de salida y la valuación de refi conservan sus propios caps.

El expediente sintético de planilla completa quedó **PENDING** en D230. En ambos escenarios el CoC cubre tres meses y requiere una ventana anual respaldada. El RLV Base también requiere esa métrica y el conjunto de entradas compatibles. El expediente conserva los cruces verificados de FAIL en Base y los faltantes. La adopción de criterios para casos reales y la precedencia entre esos hallazgos siguen pendientes.

## Reproducción

Desde la raíz del repositorio, con el [runtime OCR](workbook-plan-scan-D131.md) configurado, compilar D230 siguiendo [la guía](lorena-screening-D230.md) y ejecutar:

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_lorena_screening test_lorena_screening test_threshold_rehearsal test_scenario_threshold_rehearsal
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/lorena_screening.py rehearse-workbook /tmp/criterios-lorena.v1.json ./Expediente --current-revision ./Vigente.json
```
