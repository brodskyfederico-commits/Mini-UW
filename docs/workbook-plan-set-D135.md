# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## PDF de cuatro páginas

B03 inventaría cada página por su identificación y la referencia del plano. Para una hoja con imagen y texto superpuesto, comprueba ambas identidades. A601 aparece en la página 2 y A101 en la página 4. La portada y el detalle A202 quedan registrados. Ambas hojas requeridas dan 1.000 m² y B09 coteja la superficie con GC.

| Prueba sintética | Resultado |
| --- | --- |
| A101 o A601 ausente | PENDING. El expediente identifica la hoja faltante |
| A101 repetida en una página sólo escaneada | PENDING. Se registran las páginas 4 y 5 |
| A601 repetida o detalle A202 repetido | PENDING. Se registran ambas ubicaciones |
| El texto dice A602 y el OCR lee A601 en la misma página | PENDING. Se conservan las dos identificaciones |
| El texto de A601 declara 1.050 m² y su imagen 1.000 m² | PENDING. Se conservan ambas lecturas |
| A101 declara 1.050 m² y A601 declara 1.000 m² | PENDING. B07 conserva ambas lecturas |
| Página adicional sin identificación | PENDING. No se puede verificar la unicidad de las hojas requeridas |

El perfil admite hasta doce páginas sintéticas en orientación normal, con identidad y referencia explícitas por página. Admite texto, imagen escaneada de página completa y una capa de texto sobre la imagen. El expediente conciliado conserva el FAIL simulado por el criterio de equity/TDC de Downside. Los nueve casos bloqueados dejan PENDING también el dictamen simulado. La decisión real queda PENDING en las diez corridas.

## Reproducción en el VPS

Usá las versiones de OCR del ensayo [D131](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-sheet-set-D135.json \
  --plan templates/synthetic-sheet-set-D135.pdf \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D135.json \
  --output /tmp/miniuw-D135
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D135 \
  --current-revision templates/synthetic-workbook-current-revision-D135.json
PYTHONPATH=src python3 tools/check_worksheet_plan_set_D135.py
```
