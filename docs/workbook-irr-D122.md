# Si invierto USD 10, ¿cuánto cobro y cuándo?

El piloto D122 reproduce los cobros de las planillas Base y Downside y calcula la TIR anual del capital agregado del proyecto.

| Fecha de cobro | Concepto | Base | Downside |
| --- | --- | ---: | ---: |
| 01/03/2027 | Operación | USD 1,00 | USD 1,00 |
| 01/04/2027 | Refinanciación | USD 2,00 | USD 2,00 |
| 01/06/2027 | Operación | USD 1,00 | USD 1,00 |
| 01/07/2027 | Venta neta | USD 8,92 | USD 7,02 |
| | Total por USD 10 iniciales | USD 12,92 | USD 11,02 |

El aporte inicial es del 01/01/2027. Los aportes adicionales y el saldo sin recuperar son USD 0 en ambos escenarios. El PDF de una página muestra un intervalo de TIR de **82,77 % a 82,78 %** en Base y **26,36 % a 26,37 %** en Downside. El expediente conserva los límites exactos. El PDF redondea los límites hacia afuera a dos decimales.

## Cálculo y comparación

El caso declara una convención sintética mensual. La corrida agrupa aportes y cobros con signo en el primer día de cada mes e incluye los meses con flujo cero. Reutiliza el aislamiento exacto de raíces de T100 y la comparación de intervalos de T101. Anualiza con `(1 + TIR mensual)^12 - 1`. La evidencia registra el hash de la caja, el flujo neto por mes, la raíz aislada, los extremos anuales y la regla de cada escenario.

El caso incluido conserva el umbral sintético de TIR del 20 % anual y produce PASS simulado. Al elevar el umbral de Downside al 30 %, la simulación da FAIL y conserva los cobros. Si el intervalo cruza un umbral, hay más de una raíz admisible, las fechas salen de la grilla o falta la convención o una regla, la comparación queda PENDING. Una corrección del cap de salida en C67 recalcula la TIR y los cobros de Downside. Las referencias declaradas ligadas a la planilla anterior quedan PENDING.

La TIR es la cuarta métrica calculada del piloto. Las otras seis requieren referencias declaradas para el ensayo y mapeo a la planilla real. La decisión real, la convención aplicable a fechas reales y la validación de los criterios de Lorena siguen pendientes.

## Reproducción desde el repositorio

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-screening-pilot-D122.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --output /tmp/miniuw-D122
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D122
PYTHONPATH=src python3 tools/check_worksheet_irr_D122.py
```
