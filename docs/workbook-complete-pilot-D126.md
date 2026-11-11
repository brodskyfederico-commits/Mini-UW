# Si invierto USD 10, ¿cuánto cobro y cuándo?

El piloto sintético toma un aporte inicial de USD 10 el 01/01/2027. El aporte adicional y el saldo sin recuperar son USD 0 en ambos escenarios.

| Fecha | Cobro | Base | Downside |
| --- | --- | ---: | ---: |
| 01/03/2027 | Operación | USD 1,00 | USD 1,00 |
| 01/04/2027 | Refinanciación | USD 2,00 | USD 2,00 |
| 01/06/2027 | Operación | USD 1,00 | USD 1,00 |
| 01/07/2027 | Venta neta | USD 8,92 | USD 7,02 |
| | **Total por USD 10 iniciales** | **USD 12,92** | **USD 11,02** |

## Las diez métricas del piloto

| Métrica | Base | Downside | Evidencia de cálculo |
| --- | ---: | ---: | --- |
| Yield on Cost | 10,00 % | 6,82 % | NOI estabilizado y presupuesto D70 |
| Spread | +200,00 pb | −168,18 pb | YoC y cap de referencia D70 |
| Equity recuperado al refinanciar | 20,00 % | 20,00 % | Cobro neto de refinanciación y aporte inicial auditados |
| Equity cash-in al refinanciar | USD 0 | USD 0 | Aporte al cierre de refinanciación auditado |
| Ocupación de equilibrio | 87,32 % | 103,94 % | Renta y costos D72, servicio regular del préstamo posrefinanciación. Downside es inviable |
| CoC posrefinanciación del tramo | 10,00 % | 10,00 % | Cobro operativo de USD 100 entre el 01/04 y el 01/07 sobre base declarada de USD 1.000. Cifras del proyecto |
| Equity/TDC | 40,00 % | 45,45 % | Aportes aplicados D71 y costo total D70 |
| Múltiplo de equity | 1,29x | 1,10x | Cobros brutos sobre aportes brutos auditados |
| TIR anual, intervalo de presentación | 82,77 % a 82,78 % | 26,36 % a 26,37 % | Flujos fechados y convención mensual sintética |
| Asking / precio soportado | 0,82x | 1,40x | Asking de USD 350 y máximos de USD 426 y USD 250, respectivamente |

El cash-on-cash usa sólo cobros operativos del tramo posrefinanciación hasta la venta, con la base explícita recuperada de la corrida de caja. El resultado se publica para ese tramo. Una tasa anual y el capital efectivamente retenido requieren sus fuentes y su definición aplicable.

El precio soportado usa los objetivos explícitos de Yield on Cost y múltiplo de equity. Prueba 701 precios en la grilla sintética cerrada de USD 0 a USD 700, en pasos de USD 1. Cada candidato cambia únicamente el costo de adquisición y el equity inicial en el mismo importe. El NOI, la deuda, los demás costos, las fechas y los cobros se mantienen según el perfil declarado. El expediente conserva la evaluación del máximo y del siguiente precio. La definición general de RLV y los objetivos del caso real siguen pendientes.

## Flujo local de los Dots y bots

| Dot | Bots | Evidencia en la corrida |
| --- | --- | --- |
| D01 Recepción y coordinación | B01, B02 | Inventario de fuentes de Base y Downside, hashes y estado de ingreso |
| D02 Validación de entrada | B04 | Checklist de las celdas conectadas y de los insumos sintéticos del perfil |
| D05 Cálculo y cotejo | B12, B13, B14 | Caja por USD 10, diez métricas por escenario, bloqueos y veinte comparaciones |
| D06 Informe | B15 | PDF de una página vinculado al resultado por hash |
| D07 Auditoría y pruebas | B16, B17 | Reproducción del expediente desde sus fuentes y prueba de alteración con hashes recalculados |

El caso principal da **FAIL simulado**. Se prueba **PASS** con una revisión sintética compatible y **PENDING** por dato, regla o celda faltante. Los cobros verificados siguen disponibles. El flujo cubre las entradas estructuradas del piloto. Los lectores de planos, la investigación oficial y los mapeos de los campos reales conservan sus propios contratos y pendientes.

## Para cerrar el Mini-UW real

La decisión de inversión sigue **PENDING**. El primer caso real requiere la planilla completa y sus fuentes, las definiciones y criterios vigentes por escenario, y el cotejo independiente de los cálculos y del PASS/FAIL. En particular, hay que confirmar el período y la base de equity para CoC, la definición de ocupación y los objetivos y alcance del precio soportado. Para un retorno personal también hacen falta los términos de reparto.

## Reproducción

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-screening-pilot-D126.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --output /tmp/miniuw-D126
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D126
PYTHONPATH=src python3 tools/check_worksheet_complete_pilot_D126.py
```
