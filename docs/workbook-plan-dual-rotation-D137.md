# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Dos giros en el PDF de cuatro páginas

El plano conserva la portada y A202. Para cotejar texto y OCR también en A101, el caso usa el escaneo sintético de esa hoja de D131 con una capa de texto superpuesta. El expediente localiza A601 a 90° en la página 2 y A101 a 270° en la 4. En otra corrida, A601 está a 180° en la página 1 y A101 a 90° en la 3.

El inventario orienta los píxeles de cada escaneo según el giro del PDF. B05 y B06 verifican sus giros declarados, la identidad y la superficie en ambas capas. En los dos casos conciliados, las cuatro lecturas dan 1.000 m² y GC coincide. Se conservan las citas de página, la confianza OCR y los hashes del escaneo extraído y de la imagen orientada.

| Prueba sintética | Resultado |
| --- | --- |
| Falta A101 o A601 | PENDING con la hoja faltante identificada |
| A101 o A601 tiene un duplicado en posición normal | PENDING con las dos ubicaciones |
| En cualquiera de las hojas, el texto da 1.050 m² y el OCR 1.000 m² | PENDING con ambas citas |
| En cualquiera de las hojas falta la capa de texto | PENDING con la observación de OCR conservada |
| A101 da 1.000 m² y A601 da 1.050 m², con sus capas respectivas de acuerdo | PENDING con ambas superficies |
| El giro de A101 falta o contradice el PDF | PENDING |

El perfil cubre escaneos sintéticos de página completa con giros de 90°, 180° o 270° y hasta doce páginas. Los dos casos conciliados conservan el FAIL financiero simulado por equity/TDC de Downside. La decisión real queda PENDING en las trece corridas.

## Reproducción en el VPS

Usá las versiones de OCR del ensayo [D131](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-dual-rotation-D137.json \
  --plan templates/synthetic-dual-rotation-D137.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D137.json \
  --output /tmp/miniuw-D137
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D137 \
  --current-revision templates/synthetic-workbook-current-revision-D137.json
PYTHONPATH=src python3 tools/check_worksheet_plan_dual_rotation_D137.py
```
