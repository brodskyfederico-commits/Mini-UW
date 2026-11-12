# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Escaneo girado con texto superpuesto

La revisión vincula el giro horario declarado para A601 con el hash del PDF. B06 compara ese giro con el indicado en la página. Si coincide, aplica el giro al escaneo extraído sin interpolar píxeles. El expediente guarda los hashes de la imagen extraída y de la entrada al OCR. Las regiones citadas por OCR se expresan en coordenadas de la imagen ya orientada. El texto PDF se lee por separado.

| Prueba sintética | Resultado |
| --- | --- |
| Giro declarado y PDF a 90°, 180° y 270° | Las tres corridas reproducen los píxeles de entrada del OCR de D133. Ambas lecturas dan 1.000 m² y GC coincide |
| Giro declarado de 270° y PDF a 90° | PENDING. Se registra la discrepancia de orientación |
| Giro ausente en la configuración | PENDING. El caso requiere una orientación explícita |
| Giro coherente, texto visible de 1.050 m² e imagen de 1.000 m² | PENDING. Se conservan ambas citas y el OCR lee los píxeles del escaneo |

El alcance es una composición sintética de dos hojas con un escaneo de página completa en A601 y giros rectos. Se verifica la superficie declarada. Los casos conciliados conservan el FAIL financiero simulado por equity/TDC de Downside. Los tres bloqueos suspenden el dictamen simulado y conservan los cobros fechados. La decisión real permanece PENDING.

## Reproducción en el VPS

Usá las versiones de OCR del ensayo [D131](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-rotated-overlay-D134.json \
  --plan templates/synthetic-rotated-overlay-D134.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D134.json \
  --output /tmp/miniuw-D134
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D134 \
  --current-revision templates/synthetic-workbook-current-revision-D134.json
PYTHONPATH=src python3 tools/check_worksheet_plan_rotation_D134.py
```
