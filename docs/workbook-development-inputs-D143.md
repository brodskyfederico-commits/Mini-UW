# Si invierto USD 10, ¿cuánto cobro y cuándo?

En este piloto sintético el capital inicial del proyecto es USD 2,4 millones y se usa como base de todos los importes de esta tabla. Se redondea cada importe por separado.

| Aporte o cobro por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aporte adicional · 30/06/2027 | USD 4,42 | USD 6,00 |
| **Total aportado** | **USD 14,42** | **USD 16,00** |
| Refinanciación neta · 30/03/2028 | USD 5,72 | USD 5,72 |
| Operación neta de cuota · 30/06/2028 | USD 1,62 | USD 0,94 |
| Venta neta de costos y deuda · 30/06/2028 | USD 15,43 | USD 7,90 |
| **Cobro total** | **USD 22,76** | **USD 14,55** |
| **Saldo sin recuperar** | **USD 0,00** | **USD 1,44** |

## C32–C36 y los aportes

| Costo del proyecto | Base | Downside |
| --- | ---: | ---: |
| Terreno · C32 cotejada con el precio evaluado | USD 1.100.000 | USD 1.300.000 |
| Cierre del terreno · C33 sobre el precio evaluado | USD 22.000 · 2 % | USD 39.000 · 3 % |
| Obra vertical · C34–C36 | USD 2.340.000 · USD 90.000 × 26 unidades | USD 2.500.000 · USD 100 × 25.000 pies cuadrados brutos |
| **Total del alcance** | **USD 3.462.000** | **USD 3.839.000** |

El alcance de obra vertical excluye estacionamiento y trabajos de sitio. La corrida admite una base por unidad, por pie cuadrado bruto o por monto total. En la rama por superficie, C36 se usa sólo si el plano declara GSF pendiente y existe una fuente confirmada para la celda. Cuando el plano declara el GSF, se usa esa fuente con C36 marcada como no aplicable. En las otras dos ramas también se documenta su no aplicabilidad.

El aporte inicial cubre el terreno y el cierre en la fecha de adquisición. El saldo del aporte inicial y el aporte adicional cubren la obra. Se conservaron la operación y la financiación de D142 para aislar el efecto de los costos de adquisición y obra en los aportes. En Downside la caja cobrada queda por debajo del aporte total y el criterio sintético de múltiplo da FAIL. La decisión real queda PENDING.

El retorno afectado queda PENDING si faltan datos, si el precio evaluado discrepa de C32 o si el aporte inicial queda por debajo del desembolso al adquirir. Si falta el criterio, se conservan los cobros calculados y el dictamen queda PENDING.

## Reproducción en el VPS

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-development-inputs-D143.json \
  --workbook templates/synthetic-development-base-D143.xlsx \
  --downside-workbook templates/synthetic-development-downside-D143.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D143.json \
  --output /tmp/miniuw-D143
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D143 \
  --current-revision templates/synthetic-workbook-current-revision-D143.json
PYTHONPATH=src:tests python3 tools/check_worksheet_development_inputs_D143.py
```
