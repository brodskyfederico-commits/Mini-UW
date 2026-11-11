# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético, el aporte inicial es de USD 10 el 01/01/2027. Los aportes adicionales y el saldo sin recuperar son USD 0 en ambos escenarios.

| Fecha | Cobro | Base | Downside |
| --- | --- | ---: | ---: |
| 01/03/2027 | Operación | USD 1,00 | USD 1,00 |
| 01/04/2027 | Refinanciación | USD 2,00 | USD 2,00 |
| 01/06/2027 | Operación | USD 1,00 | USD 1,00 |
| 01/07/2027 | Venta neta | USD 8,92 | USD 7,02 |
| | **Total por USD 10 iniciales** | **USD 12,92** | **USD 11,02** |

## Yield on Cost y spread

Las planillas del piloto se complementan con los insumos sintéticos de D70 dentro del JSON D123. Los importes operativos, el presupuesto y el cap de referencia conservan los valores del ensayo D70. Cada inventario identifica su escenario y el hash de la planilla vigente. El año operativo estabilizado de prueba va del 01/01/2027 al 01/01/2028.

| Insumo o cálculo | Fuente o fórmula | Base | Downside |
| --- | --- | ---: | ---: |
| NOI estabilizado anual | Ingresos devengados menos gastos e impuesto del perfil sintético T19 | USD 100 | USD 75 |
| Costo total de desarrollo (TDC) | Adquisición, obra, costos blandos, financiación y otros | USD 1.000 | USD 1.100 |
| Cap de referencia de mercado | Fuente específica del escenario en `yield_inputs` | 8,00 % | 8,50 % |
| Yield on Cost | NOI estabilizado dividido por TDC | 10,00 % | 6,82 % |
| Spread | Diferencia entre YoC y cap de referencia, en puntos básicos | +200,00 pb | −168,18 pb |

El cap de referencia del spread tiene su propia fuente. C66 y C67 siguen representando el cap de refinanciación y el de salida. El expediente guarda los valores racionales exactos, los hashes de los insumos y los bloqueos por métrica. El PDF redondea para lectura.

- **FAIL simulado** con los umbrales del caso. Downside queda por debajo del mínimo de 7,5 % de YoC y de −100 pb de spread.
- **PASS simulado** en una revisión de prueba que fija los mínimos inclusivos exactamente en los resultados calculados de Downside.
- **PENDING** al retirar el cap de referencia de Downside o una regla de spread. Cuando falta el cap, el YoC disponible y los cobros verificados se conservan. Si falta un componente del TDC o un renglón requerido del NOI, quedan pendientes ambos indicadores.

El piloto ya calcula seis de sus diez métricas. Cuatro conservan referencias declaradas para la prueba. La vinculación de estos insumos a fuentes reales y la decisión de inversión siguen PENDING.

## Reproducción desde el repositorio

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-screening-pilot-D123.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --output /tmp/miniuw-D123
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D123
PYTHONPATH=src python3 tools/check_worksheet_yoc_spread_D123.py
```
