# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el caso sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0. La prueba compara las planillas, los flujos fechados y los importes exactos entre revisiones.

## Nuevo máximo de equity/TDC de Downside

La revisión sintética R3 baja el máximo inclusivo del 50 % al 45 %. El cálculo de Downside sigue siendo USD 500 de equity aplicado sobre USD 1.100 de TDC, igual a 5/11 o 45,45 % redondeado. En Base, el equity/TDC sigue en 40,00 % frente al máximo del 50 %. El hash de las reglas de inversión es el único hash de grupo que cambia.

| Expediente | Referencia usada al auditar o correr | Resultado |
| --- | --- | --- |
| R2 | R2 | PASS simulado archivado |
| R3 | R3 | **FAIL simulado vigente** |
| R2 auditado | R3 | **PENDING** vigente. El PASS queda histórico |
| R2 vuelto a correr | R3 | PENDING por revisión incompatible |
| R3 vuelto a correr | R2 | PENDING por revisión incompatible |

La comparación de equity/TDC de Downside es la única de las veinte que cambia. La auditoría del expediente R2 conserva sus archivos. La decisión real permanece **PENDING**. El PDF usa el formato de una página del piloto D128. Los identificadores de la revisión R3 se guardan en el caso, su referencia y el resultado de auditoría.

## Reproducción en el VPS

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-current-chain-D129.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D129.json \
  --output /tmp/miniuw-D129
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D129 \
  --current-revision templates/synthetic-workbook-current-revision-D129.json
PYTHONPATH=src python3 tools/check_worksheet_equity_limit_revision_D129.py
```
