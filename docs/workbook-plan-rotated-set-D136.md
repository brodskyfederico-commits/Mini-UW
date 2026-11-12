# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## A601 girada dentro del PDF de cuatro páginas

El plano de prueba conserva portada, A601, A202 y A101. A601 está girada a 90° en la página 2 y A101 aparece en la 4. El inventario usa la orientación registrada por el PDF para normalizar cada escaneo y leer su identidad. La revisión vincula el hash del PDF y el giro declarado para A601. Tras localizarla, B06 comprueba ese giro y coteja su texto con el OCR. El expediente conserva las citas de ambas lecturas y los hashes del escaneo extraído y de la imagen que recibió el OCR.

| Prueba sintética | Resultado |
| --- | --- |
| A601 a 90°, 180° y 270° | Ambas lecturas dan 1.000 m² y GC coincide. En el caso a 270°, A601 aparece en la página 3 |
| Falta A101 o A601 | PENDING. Se identifica la hoja faltante |
| A101 duplicada en un escaneo o A601 duplicada en posición normal | PENDING. Se guardan las dos ubicaciones |
| El texto de A601 declara 1.050 m² y su imagen 1.000 m² | PENDING. Se conservan las dos lecturas |
| A101 declara 1.050 m² y A601 declara 1.000 m² | PENDING. B07 conserva ambas superficies |
| El giro declarado es 270° y el PDF indica 90° | PENDING. Se conservan ambos giros |
| Falta la capa de texto de A601 | PENDING. El expediente conserva lo que leyó el OCR |

El perfil cubre hasta doce páginas sintéticas y giros rectos de escaneos de página completa. Las once corridas conservan los cobros fechados. Las tres conciliadas conservan el FAIL financiero simulado por equity/TDC de Downside. La decisión real queda PENDING en todos los casos.

## Reproducción en el VPS

Usá las versiones de OCR del ensayo [D131](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-rotated-sheet-set-D136.json \
  --plan templates/synthetic-rotated-sheet-set-D136.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D136.json \
  --output /tmp/miniuw-D136
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D136 \
  --current-revision templates/synthetic-workbook-current-revision-D136.json
PYTHONPATH=src python3 tools/check_worksheet_plan_rotated_set_D136.py
```
