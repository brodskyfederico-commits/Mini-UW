# D235 · Dictamen sintético de la ruta anual D234

El cotejo toma Base y Downside de `annual_hold_with_refinance` del expediente D234. Verifica la revisión vigente y reproduce el expediente desde sus fuentes. La configuración D230 de Lorena se usa en modo de simulación. El 1101 real y su retorno histórico siguen PENDING.

## Resultados por cada USD 10 iniciales

| Escenario | Aporte adicional | Refi | Cobros de operación | Venta | Cobro total | Sin recuperar |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Base | USD 4,87 | USD 2,03, 30 sep 2028 | USD 1,20, dic 2028 a sep 2029 | USD 13,68, 30 sep 2029 | USD 16,92 | USD 0,00 |
| Downside | USD 8,32 | USD 1,64, 30 mar 2029 | USD 0,21, jun a dic 2029 | USD 3,08, 30 mar 2030 | USD 4,94 | USD 13,38 |

El aporte inicial se registra el 30 de marzo de 2027 en ambos casos. Los aportes adicionales llegan hasta septiembre de 2028 en Base y marzo de 2030 en Downside. Downside aporta USD 0,13 el día de venta para cubrir el déficit operativo del último trimestre. Los totales se redondean después de sumar los movimientos exactos. El cotejo conserva cada fecha, importe y etapa originales.

## Criterios y RLV

- Base cumple las condiciones de YoC, spread, aporte al cierre de refinanciación y cash-on-cash post-refi. Recuperación al refinanciar, equity/TDC, TIR y múltiplo activan su condición FAIL. Ocupación de equilibrio y RLV quedan PENDING. La TIR anual es 6,12 % y el cash-on-cash post-refi es 9,38 %.
- Downside cumple la condición de aporte al cierre de refinanciación. Siete métricas quedan por debajo o fuera de sus condiciones PASS. La ocupación queda PENDING y el RLV figura N/A por la política Base-only de D230. La TIR anual es −43,69 % y el cash-on-cash post-refi es 0,52 %.
- El dictamen simulado queda PENDING por faltantes concurrentes con condiciones FAIL verificadas en Base, cuya precedencia sigue pendiente de confirmación en D230. La ruta original de D234 no tiene un NOI anual que concilie con la curva de ocupación económica. En el control sintético con NOI conciliado se calcula la ocupación en ambos escenarios con la reserva C60 y el servicio de deuda de la ruta anual. La búsqueda del RLV en Base aplica conjuntamente los nueve criterios, mantiene fija la deuda y ajusta el costo total por el movimiento del precio y C33. Ningún precio válido de la grilla ensayada llega a PASS.

El equity acumulado hasta estabilización alimenta los criterios que lo requieren. El equity retenido después del cierre se usa para el cash-on-cash anual. La TIR anual se calcula sobre la caja neta al cierre de cada trimestre. En el control con un solo cambio de signo se comprueba la raíz mediante un intervalo racional.

## Reproducción

```sh
PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_lorena_annual_route
PYTHONPATH=src:tools python3 tools/lorena_screening.py rehearse-workbook \
    criterios-lorena.json expediente --current-revision vigente.json \
    --route annual_hold_with_refinance
```

La prueba compara la caja evento por evento con la salida de D234, verifica el bloqueo de RLV en ambos casos y coteja que el expediente y la revisión designada conserven sus bytes. El comando devuelve el dictamen, las métricas, el saldo y las fechas, junto con los hashes de la caja y del expediente.
