# Capacidad por LTV y DSCR en la corrida del Mini-UW

La corrida toma la menor capacidad entre LTV y DSCR. C71 fija el LTV máximo sobre el valor del activo. C72 fija el DSCR mínimo sobre el NOI bancario y el servicio anual de deuda. El ensayo mantiene el préstamo solicitado en **USD 150** a nivel del proyecto.

| C71 LTV | C72 DSCR | Capacidad LTV | Capacidad DSCR | Menor límite | Cobro total por USD 10 |
| ---: | ---: | ---: | ---: | --- | ---: |
| 80 % | 2,00× | USD 400,00 | USD 245,08 | DSCR | USD 12,92 |
| 40 % | 2,00× | USD 200,00 | USD 245,08 | LTV | USD 12,92 |
| 30 % | 2,00× | USD 150,00 | USD 245,08 | LTV | USD 12,92 |
| 29,99 % | 2,00× | USD 149,95 | USD 245,08 | LTV | PENDING |
| 40 % | 4,00× | USD 200,00 | USD 122,54 | DSCR | PENDING |
| Vacía | 2,00× | PENDING | PENDING | PENDING | PENDING |

El caso de USD 150 exactos pasa el control de capacidad. Si la solicitud excede el límite, el expediente conserva ambos límites y la solicitud original. El cierre y el retorno quedan PENDING. La decisión de inversión permanece PENDING para todo el ensayo.

En los casos compatibles, aportás USD 10 el 01/01/2027 y cobrás USD 1 de operación el 01/03, USD 2 de refinanciación el 01/04, USD 1 de operación el 01/06 y USD 8,92 de venta neta el 01/07/2027. Los flujos coinciden porque el importe del préstamo y el resto de los términos siguen fijos.

```bash
PYTHONPATH=src python3 tools/check_worksheet_ltv_case_D119.py --output /tmp/miniuw-D119
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D119/at-ltv-limit
```

El ensayo usa el perfil de ingreso D118, compara los límites con un cálculo independiente y audita el XLSX y el PDF de cada variante. [Perfil de corrida D118](worksheet-capacity-case-D118.md).
