# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético, el aporte inicial es USD 10 el 01/01/2027. En ambos escenarios se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Lectura y conciliación de planos PDF

B05 lee la fila de superficie bruta del cuadro de áreas en A101. B06 lee el valor declarado en el resumen de A601. Cada lector usa su propia hoja y conserva la página, el renglón original y el hash del PDF. B07 concilia las dos superficies declaradas. B09 coteja el resultado con el registro de GC y la tolerancia explícita del caso.

| Prueba | Evidencia | Resultado |
| --- | --- | --- |
| Lecturas coincidentes | A101 y A601 declaran 1.000 m². GC también declara 1.000 m² | Conciliado. El máximo de equity/TDC de D129 conserva el FAIL simulado |
| Dato faltante | A601 omite la superficie. A101 conserva sus 1.000 m² | PENDING |
| Lecturas discrepantes | A101 declara 1.000 m² y A601 declara 1.050 m² | PENDING. Se conservan ambas lecturas |
| Diferencia con GC | A101 y A601 declaran 1.050 m². GC declara 1.000 m² | PENDING |
| PDF ausente | Falta el archivo declarado | PENDING |
| PDF de otra revisión | Los bytes del PDF difieren del hash de la referencia vigente | PENDING |

La auditoría conserva los bytes del plano y reproduce la extracción desde el archivo guardado. También se prueba una unidad incompatible y la sustitución del PDF con un manifiesto recalculado. Los flujos de caja coinciden en las seis corridas. La decisión real sigue PENDING.

El lector de prueba cubre PDF con texto y dos formatos de área declarada. La primera corrida real requiere validar el formato de sus planos y su mapeo, cotejar las lecturas y aplicar las fuentes y los criterios vigentes de ese caso.

## Reproducción en el VPS

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-plan-chain-D130.json \
  --plan templates/synthetic-plan-D130.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D130.json \
  --output /tmp/miniuw-D130
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D130 \
  --current-revision templates/synthetic-workbook-current-revision-D130.json
PYTHONPATH=src python3 tools/check_worksheet_plan_pdf_D130.py
```
