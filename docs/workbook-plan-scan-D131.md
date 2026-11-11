# Si invierto USD 10, ¿cuánto cobro y cuándo?

El aporte sintético es USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## OCR de un plano escaneado

La prueba usa dos páginas rasterizadas a 216 dpi en escala de grises. El PDF conserva una sola imagen por página. B05 recupera la superficie declarada en A101 y B06 la del resumen A601. Los dos leen **1.000 m²** en el escaneo completo. El expediente conserva la página, el renglón reconocido, la región de píxeles y la confianza mínima de las palabras citadas. B07 concilia los valores y B09 reproduce la coincidencia con GC. El caso completo conserva el FAIL simulado del criterio de equity/TDC de D129.

| Prueba | Resultado |
| --- | --- |
| Falta la superficie en A601 | PENDING. Se conserva la lectura de A101 |
| A101 y A601 declaran 1.000 y 1.050 m² | PENDING. Se conservan las dos observaciones |
| Una palabra citada queda por debajo del mínimo declarado para el ensayo | PENDING. El dato reconocido queda como observación |
| El motor o los datos de idioma requeridos faltan | PENDING |

El caso sintético fija un mínimo de confianza de 75 sobre 100. La prueba de bloqueo eleva ese mínimo a 100 con la misma imagen. El expediente registra Tesseract 5.3.4, Leptonica 1.82.0 y el hash del archivo de idioma inglés. El auditor vuelve a leer las imágenes guardadas con ese perfil. Una prueba separada confirma el bloqueo cuando cambia el hash del idioma.

El soporte de este hito abarca escaneos sintéticos de dos páginas con una imagen completa por página y superficies escritas en los cuadros. Queda pendiente cotejar la extracción de formatos reales y sus criterios de aceptación. La decisión real sigue PENDING.

## Reproducción

El VPS ejecutó Tesseract desde una carpeta de trabajo. En Ubuntu 24.04 la prueba usa los paquetes `tesseract-ocr=5.3.4-1build5` y `tesseract-ocr-eng=1:4.1.0-2`. Si se usan paquetes extraídos a una carpeta local, configurá `PATH`, `LD_LIBRARY_PATH` y `TESSDATA_PREFIX` para el binario, las bibliotecas y el archivo de idioma de esa carpeta.

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-scan-chain-D131.json \
  --plan templates/synthetic-scanned-plan-D131.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D131.json \
  --output /tmp/miniuw-D131
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D131 \
  --current-revision templates/synthetic-workbook-current-revision-D131.json
PYTHONPATH=src python3 tools/check_worksheet_plan_scan_D131.py
```
