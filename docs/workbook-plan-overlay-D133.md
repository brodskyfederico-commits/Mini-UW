# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Dos lecturas de la misma hoja

La hoja A601 combina una imagen escaneada de página completa y una capa de texto. B06 lee el texto del PDF y extrae la imagen original para el OCR. Guarda página, hoja, renglón y método para cada lectura. Para el OCR guarda también el hash de la imagen procesada, la región y la confianza de las palabras citadas.

| Prueba sintética en A601 | Resultado |
| --- | --- |
| Texto y OCR declaran 1.000 m² | B06 concilia. B07 compara con A101 y B09 coteja con GC |
| Texto visible declara 1.050 m² y la imagen declara 1.000 m² | PENDING. Se guardan ambos valores y el hash de la imagen original coincide |
| Texto declara 1.000 m² y la imagen declara 1.050 m² | PENDING. Se guardan ambos valores |
| Falta la superficie en el texto | PENDING. Se conserva la superficie observada por OCR |
| Falta la superficie en la imagen | PENDING. Se conserva la superficie observada en el texto |
| Falta el idioma requerido por OCR | PENDING. Se conserva la lectura del texto |

La prueba usa una composición fija de dos hojas y compara superficies escritas. La revisión vigente vincula la ruta de cada hoja y el hash del plano. La auditoría reproduce las lecturas a partir de los archivos guardados. El caso conciliado conserva el FAIL financiero simulado por el criterio de equity/TDC de Downside. Los otros cinco casos dejan PENDING también el dictamen simulado. Las seis corridas conservan los cobros fechados y la decisión real PENDING.

## Reproducción en el VPS

Usá las versiones locales de OCR del ensayo [D131](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-overlay-chain-D133.json \
  --plan templates/synthetic-overlay-plan-D133.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D133.json \
  --output /tmp/miniuw-D133
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D133 \
  --current-revision templates/synthetic-workbook-current-revision-D133.json
PYTHONPATH=src python3 tools/check_worksheet_plan_overlay_D133.py
```
