# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Un PDF con hojas de texto y escaneadas

El caso declara la página y el método de lectura para A101 y A601. La revisión vigente vincula esa asignación y los bytes del plano. B05 y B06 conservan la cita de cada hoja, el renglón y el método. La lectura por OCR incluye la región y la confianza de las palabras citadas.

| Prueba sintética | Resultado |
| --- | --- |
| A101 con texto y A601 escaneada | Ambas lecturas dan 1.000 m². B07 y GC coinciden |
| A101 escaneada y A601 con texto | Ambas lecturas dan 1.000 m². B07 y GC coinciden |
| A601 sin superficie | PENDING. Se conserva la lectura de A101 |
| Texto declara 1.000 m² y OCR lee 1.050 m² | PENDING. Se conservan las dos citas y los valores |
| Una sola hoja tiene texto superpuesto a la imagen | PENDING por composición de página fuera del perfil sintético |
| Falta el motor o el idioma de OCR | PENDING. Se conserva la lectura de la hoja con texto |

El lector verifica la identidad de la hoja antes de asociar el dato. El formato de prueba admite dos hojas con métodos separados. Los dos casos conciliados conservan el FAIL financiero simulado por el criterio de equity/TDC de Downside. En las seis corridas coinciden los cobros fechados. La decisión real sigue PENDING.

## Reproducción en el VPS

Usá la instalación local y las versiones de OCR del ensayo [D131](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-mixed-chain-D132.json \
  --plan templates/synthetic-mixed-plan-D132.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D132.json \
  --output /tmp/miniuw-D132
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D132 \
  --current-revision templates/synthetic-workbook-current-revision-D132.json
PYTHONPATH=src python3 tools/check_worksheet_plan_mixed_D132.py
```
