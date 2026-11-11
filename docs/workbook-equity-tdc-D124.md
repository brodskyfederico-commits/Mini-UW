# Si invierto USD 10, ¿cuánto cobro y cuándo?

En ambos escenarios se aportan USD 10 el 01/01/2027. El aporte adicional y el saldo sin recuperar son USD 0.

| Fecha | Cobro | Base | Downside |
| --- | --- | ---: | ---: |
| 01/03/2027 | Operación | USD 1,00 | USD 1,00 |
| 01/04/2027 | Refinanciación | USD 2,00 | USD 2,00 |
| 01/06/2027 | Operación | USD 1,00 | USD 1,00 |
| 01/07/2027 | Venta neta | USD 8,92 | USD 7,02 |
| | **Total por USD 10 iniciales** | **USD 12,92** | **USD 11,02** |

## Equity aplicado sobre costo total

El caso usa el registro sintético de fondos aplicados de D71 al 31/12/2026 y el TDC que la misma corrida calcula para Yield on Cost. Los hashes vinculan cada registro con la planilla del escenario y con su presupuesto en `yield_inputs`. La reconciliación verifica que los desembolsos de deuda y el equity aplicado sumen el TDC.

| Concepto | Base | Downside |
| --- | ---: | ---: |
| Equity aplicado | USD 400 | USD 500 |
| Deuda desembolsada y aplicada | USD 600 | USD 600 |
| Costo total de desarrollo (TDC) | USD 1.000 | USD 1.100 |
| **Equity / TDC** | **40,00 %** | **45,45 %** |

El registro declara un compromiso de USD 750 en ambos escenarios. El cuadre usa los USD 600 desembolsados. Los cobros por USD 10 se calculan desde el libro de caja de las planillas y se auditan junto con la métrica.

- **PASS de equity/TDC** en ambos escenarios con el máximo sintético del 50 %. El caso principal da **FAIL global simulado** por el YoC y el spread de Downside.
- **PASS global simulado** en una revisión de prueba con reglas compatibles de YoC y spread. Al bajar el máximo de equity/TDC de Downside a 45 %, esa métrica por sí sola lleva la simulación a **FAIL**. Se conservan ambos retornos.
- **PENDING** si falta el equity aplicado, el costo total, la regla requerida, o si los fondos corresponden a otra revisión o no cuadran con el costo. El expediente conserva la caja verificada.

El piloto calcula siete métricas y prueba tres con referencias declaradas. La adopción de criterios reales y la decisión de inversión siguen PENDING.

## Reproducción desde el repositorio

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-screening-pilot-D124.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --output /tmp/miniuw-D124
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D124
PYTHONPATH=src python3 tools/check_worksheet_equity_tdc_D124.py
```
