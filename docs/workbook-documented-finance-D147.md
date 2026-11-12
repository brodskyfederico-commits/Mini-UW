# D147 · Validación documental, aportes y cobros por USD 10

## Si invierto USD 10, ¿cuánto aporto y cuándo cobro?

Los importes de la tabla son USD por cada USD 10 iniciales de equity agregado del piloto sintético.

| Flujo | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00 | 10,00 |
| Aporte · 30/06/2027 | 0,00 | 0,76 |
| Aporte · 30/09/2027 | 4,66 | 0,04 |
| Aporte · 30/12/2027 | 0,05 | 7,03 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,05 cada fecha | 0,07 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,07 cada fecha |
| **Total aportado** | **14,87** | **18,19** |
| Cobro neto de refinanciación | 3,07 · 30/09/2028 | 2,86 · 30/03/2029 |
| Cobro de operación | 1,69 · 30/12/2028 | 1,01 · 30/06/2029 |
| Cobro neto de venta | 15,43 · 30/12/2028 | 8,24 · 30/06/2029 |
| **Total cobrado** | **20,19** | **12,10** |
| **Sin recuperar al cierre** | **0,00** | **6,09** |

Los totales se calculan antes de redondear. Los flujos fechados reproducen D146 exactamente. El expediente completo da **FAIL simulado** con su regla de múltiplo de equity. El dictamen real queda **PENDING**.

## Evidencia de la corrida integrada

| Requisito | Fuente y ubicación | Aplicación y evidencia |
|---|---|---|
| Planillas y revisión | `case.json` en `/workbook_sha256`, `/native_mapping` y la referencia externa `current_revision.json` | D01 y D02 comprueban las huellas y los campos. B12 bloquea el dictamen ante una revisión incompatible. |
| Superficie y alcance | `Plan.pdf`, hojas A101 p. 4 y A601 p. 2. `case.json` en `/local_sources/finance_binding` | B05 y B06 cotejan texto y OCR, incluido el recorte del PDF. B07 y B09 verifican 1.000 m² de superficie bruta contra GC. |
| Cotización por escenario | `case.json` en `/local_sources/documents/gc_budget/document/budget_by_scenario` y `Inputs!A34:F36` | B08 lee la cotización vertical por escenario. Se compara con la obra vertical calculada antes de entregar el presupuesto a B13. El alcance de la cotización excluye estacionamiento y trabajos de sitio. |
| Copia oficial | `case.json` en `/local_sources/documents/official_snapshot` y `/local_sources/official_request` | B10 y B11 cotejan origen, vigencia y valor de la copia local al 01/03/2027, fecha de la planilla sintética. Es una condición del dictamen. |
| Presupuesto, deuda y retorno | `results.json` en `/scenarios/{Base,Downside}` | Cada `construction_budget` conserva la huella de `document_financial_binding`. D146 referencia ese presupuesto para calcular desembolsos, intereses, cancelación al refinanciar y caja por USD 10. |
| Informe y reproducción | `MiniUW_Resumen.pdf`, `package.json` y archivos fuente guardados | B15 genera una página. B16 verifica los bytes mediante una corrida desde las fuentes. B17 comprueba la versión con su batería aparte. |

La prueba de Downside usa superficie bruta documentada en pies². Se coteja de forma exacta con el plano mediante 1 pie² = 0,09290304 m². Como el plano trae la superficie, la celda auxiliar C36 se marca como no aplicable y C35 usa la tarifa sintética de USD 232,2576 por pie². Así se conserva la cotización vertical de USD 2.500.000 de D146. Base conserva su cotización por unidad de USD 2.340.000 en total.

La falta del plano o de su cotejo de superficie bloquea ambos escenarios. Una cotización de GC ausente o contradictoria, una superficie financiera incompatible o un dato de deuda faltante bloquea la caja del escenario afectado. Una copia oficial, una revisión o un criterio faltantes dejan PENDING el dictamen y los flujos que sí pueden calcularse quedan identificados como condicionados al expediente. La copia oficial y las cotizaciones de GC son sintéticas y locales.

## Reproducción en el VPS

Con el runtime de OCR del ensayo D131 y las dependencias del repositorio, una orden genera el expediente y el PDF de una página. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-documented-finance-D147.json \
  --workbook templates/synthetic-construction-financing-base-D146.xlsx \
  --downside-workbook templates/synthetic-documented-finance-downside-D147.xlsx \
  --plan templates/synthetic-cropped-rotated-set-D138.pdf \
  --current-revision templates/synthetic-workbook-current-revision-D147.json \
  --output /tmp/miniuw-d147
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d147 \
  --current-revision templates/synthetic-workbook-current-revision-D147.json
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_documented_finance_D147.py
```
