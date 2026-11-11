# Si invierto USD 10, ¿cuánto cobro después de corregir C72?

El caso D118 recibe el XLSX sintético del perfil de ingreso D117. Se parte de la copia con C68 completo y C72 vacío. Cada corrección cambia sólo **Inputs!C72**, el DSCR mínimo. El préstamo solicitado se mantiene en **USD 150** a nivel del proyecto.

| C72 en la copia | Capacidad de refinanciación | Cobro total por USD 10 iniciales | Resultado |
| --- | ---: | ---: | --- |
| Vacía | PENDING | PENDING | El checklist señala C72. |
| 2,00× | USD 245,08 | USD 12,92 | La corrida sintética calcula los cobros. |
| 4,00× | USD 122,54 | PENDING | El préstamo supera la capacidad en USD 27,46. |

El límite por LTV es USD 400 en ambas copias completas. El límite por DSCR se calcula con el NOI bancario anual y el servicio anual por dólar prestado. El expediente vincula ese cálculo a la celda C72 y al hash del XLSX. Cuando el principal supera la capacidad, la página informa el límite y el motivo. El cierre, el retorno y el precio mínimo quedan PENDING.

En la variante compatible, aportás USD 10 el 01/01/2027. Cobrás USD 1 de operación el 01/03/2027, USD 2 de refinanciación el 01/04/2027, USD 1 de operación el 01/06/2027 y USD 8,92 de venta neta el 01/07/2027. El saldo nominal sin recuperar es cero. Los resultados son sintéticos. La decisión de inversión permanece PENDING.

## Reproducción

```bash
PYTHONPATH=src python3 tools/check_worksheet_capacity_case_D118.py --output /tmp/miniuw-D118
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D118/above-capacity
```

El verificador ejecuta las tres copias por el comando habitual, compara la capacidad contra un cálculo independiente y audita cada XLSX con su PDF de una página. Los expedientes D117 siguen usando su versión original. [Perfil de ingreso D117](worksheet-intake-case-D117.md).
