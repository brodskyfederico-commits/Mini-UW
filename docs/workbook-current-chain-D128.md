# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético, el aporte inicial es USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Reposición y vigencia

La cadena compara las fuentes y reglas del caso con una referencia sintética designada en un archivo externo al expediente. La referencia vincula las planillas, los insumos financieros, los documentos de planos y GC, la copia oficial y su fecha de consulta, el criterio de GC y las reglas de inversión. Cada grupo tiene su propio SHA-256. La copia oficial conserva además la comprobación de su período de validez.

| Estado de la reposición | Simulación |
| --- | --- |
| Faltan la copia oficial, el criterio de GC y la regla de inversión de Downside | PENDING |
| Se repone la copia oficial vigente | PENDING |
| Se repone también el criterio vigente de GC | PENDING |
| Se repone la regla de inversión vigente y coinciden los tres elementos con la referencia | PASS |

Reinsertar una copia oficial, un criterio de GC o una regla de inversión de la revisión anterior deja **PENDING**, incluso cuando las verificaciones locales y financieras por separado dan PASS. El expediente señala el grupo cuyo hash difiere. Una copia oficial vencida también deja PENDING cuando sus bytes coinciden con la referencia.

El expediente guarda la referencia observada al correr. La auditoría reproduce los archivos guardados y compara la referencia observada con la que se le suministra como vigente. Si cambió, identifica el resultado como **HISTÓRICO** y el dictamen vigente queda **PENDING**. Sin una referencia externa, la vigencia también queda PENDING. El caso real permanece PENDING.

## Reproducción en el VPS

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-current-chain-D128.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D128.json \
  --output /tmp/miniuw-D128
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D128 \
  --current-revision templates/synthetic-workbook-current-revision-D128.json
PYTHONPATH=src python3 tools/check_worksheet_current_chain_D128.py
```
