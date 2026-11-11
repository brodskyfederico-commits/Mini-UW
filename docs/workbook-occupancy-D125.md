# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027 en ambos escenarios. Se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Ocupación económica de equilibrio

La prueba usa la renta potencial y los costos sintéticos del perfil D72. La deuda se toma del préstamo posrefinanciación que pasó por la corrida de caja. Su cuota regular, expresada como equivalente anual por el motor de deuda, suma USD 612,04 en ambos escenarios. El expediente registra el préstamo y su corrida por hash. El equivalente anual representa el servicio regular del perfil estabilizado. Las fechas y pagos efectivos de la simulación de compra, refinanciación y venta se conservan en el libro de caja.

| Concepto anual | Base | Downside |
| --- | ---: | ---: |
| Renta potencial al 100 % | USD 1.000 | USD 900 |
| Costos fijos | USD 200 | USD 250 |
| Servicio regular equivalente | USD 612,04 | USD 612,04 |
| Impuesto del perfil a la altura del equilibrio | USD 61,20 | USD 73,44 |
| Ocupación económica requerida | **87,32 %** | **103,94 %** |

El cálculo divide costos fijos, servicio e impuesto del perfil por la renta potencial. El motor de NOI verifica la cobertura al cruzar el umbral. Downside queda inviable dentro del rango de 0 % a 100 %. Ambos escenarios dan FAIL en esta métrica con el máximo sintético del 85 %. Una variante de renta más alta prueba PASS con reglas compatibles. Si falta renta, costo, deuda compatible o regla, el dictamen queda PENDING y se conservan los cobros que sí se pudieron verificar.

El piloto calcula ocho métricas. La definición aplicable al caso real y su decisión siguen PENDING.

## Reproducción

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-screening-pilot-D125.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --output /tmp/miniuw-D125
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D125
PYTHONPATH=src python3 tools/check_worksheet_occupancy_D125.py
```
