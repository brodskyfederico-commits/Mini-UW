# Si invierto USD 10, ¿cuánto cobro y cuándo?

La prueba sintética conserva el aporte inicial de USD 10 del 01/01/2027. En ambos escenarios se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Cadena local de los siete Dots

| Dot y bots | Evidencia de la prueba sintética |
| --- | --- |
| D01 · B01, B02, B03 | Orquestación, planillas por hash y clasificación de documentos estructurados por tipo y revisión |
| D02 · B04 | Checklist de las celdas conectadas y pendientes por escenario |
| D03 · B05, B06, B07, B09 | Dos lecturas separadas del mismo plano simulado, conciliación y cotejo de superficie con el registro de GC bajo una tolerancia explícita |
| D04 · B10, B11 | Verificación local de una copia archivada con origen sintético permitido, vigencia y ubicación del valor citado |
| D05 · B08, B12, B13, B14 | Lectura estructurada de GC, controles previos, caja por USD 10, diez métricas y veinte comparaciones |
| D06 · B15 | PDF de una página vinculado al resultado |
| D07 · B16, B17 | Reproducción desde fuentes con el comando de auditoría y pruebas de versión por separado |

B08 entrega el registro de GC antes del cotejo B09. Las lecturas A y B usan documentos estructurados distintos y conservan sus referencias originales. El ejemplo concilia 1.000 m² en ambos documentos y en el registro de GC con una diferencia máxima explícita de 0 m². B10 y B11 trabajan con la copia incluida en el caso. La ruta usa archivos estructurados y un origen de prueba reservado.

La evidencia complementaria se vincula por hash a las planillas del caso. Si falta una fuente o una regla, el dictamen integrado queda **PENDING** y el expediente conserva los cobros de los escenarios verificados. El caso completo da **PASS** simulado y una regla de equity/TDC más exigente da **FAIL** simulado. La auditoría rechaza resultados alterados aunque se vuelva a calcular el hash del manifiesto. La decisión real sigue **PENDING**.

El alcance de estas pruebas comprende los contratos locales de los 17 bots. Los adaptadores de planos y fuentes oficiales usan documentos sintéticos estructurados. La extracción de planos originales y las consultas a fuentes oficiales requieren sus entradas y reglas de aplicación.

## Reproducción en el VPS

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-local-chain-D127.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --output /tmp/miniuw-D127
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D127
PYTHONPATH=src python3 tools/check_worksheet_local_chain_D127.py
```
