# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Recorte de A601 o A101 en el mismo PDF

El plano conserva A601 a 90° en la página 2 y A101 a 270° en la 4. El caso principal aplica un rectángulo de recorte `CropBox` a A601. El OCR coteja los píxeles visibles tras orientar el escaneo. Una lectura del escaneo completo comprueba que las líneas exigidas caben enteras en el recorte y que la superficie es única. El expediente conserva la región visible, las citas y los hashes del escaneo completo y de los píxeles que recibió el OCR para el cotejo.

| Prueba sintética | Resultado |
| --- | --- |
| Recorte de A601 o de A101 que conserva todas las líneas | Texto y OCR dan 1.000 m². GC coincide |
| Superficie fuera del recorte en A101 o A601 | PENDING. Se conserva la declaración de texto y la ausencia en el OCR visible |
| Renglón de superficie cortado parcialmente | PENDING |
| Identificación de A601 fuera del recorte | PENDING |
| Texto de A101 declara 1.050 m² y el OCR visible lee 1.000 m² | PENDING con ambas citas |
| Recorte oculta una segunda línea de superficie del escaneo | PENDING por ambigüedad |
| Borde de recorte entre dos píxeles | PENDING |

El perfil cubre recortes rectangulares de PDF dentro de la página con bordes alineados a píxeles, en escaneos sintéticos de página completa con giros rectos. Los dos casos conciliados conservan el FAIL financiero simulado por equity/TDC de Downside. Las nueve corridas conservan los cobros fechados y la decisión real PENDING.

## Reproducción en el VPS

Usá las versiones de OCR del ensayo [D131](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-cropped-rotated-set-D138.json \
  --plan templates/synthetic-cropped-rotated-set-D138.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D138.json \
  --output /tmp/miniuw-D138
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D138 \
  --current-revision templates/synthetic-workbook-current-revision-D138.json
PYTHONPATH=src python3 tools/check_worksheet_plan_cropped_set_D138.py
```
