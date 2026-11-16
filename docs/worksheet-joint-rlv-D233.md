# Si invierto USD 10, ¿cuánto cobro y cuándo?

El expediente sintético vigente conserva los 10 movimientos de Base y los 13 de Downside. Por USD 10 iniciales, Base aporta USD 4,87 extra y cobra USD 2,85 el 30/09/2028 y USD 16,66 el 30/12/2028. Downside aporta USD 8,19 extra y cobra USD 2,45 el 30/03/2029 y USD 4,68 el 30/06/2029. Quedan USD 0,00 y USD 11,06 sin recuperar, respectivamente. Se reproduce el mismo PDF de D232.

## Búsqueda conjunta del valor residual

El comparador D230 evalúa cada precio de la grilla con las nueve métricas aplicables de Base que anteceden al RLV. Incluye YoC y spread en su base compatible, recuperación y aporte en refi, ocupación de equilibrio, CoC anual, equity/TDC, TIR y múltiplo. Con deuda fija, el cambio en TDC y equity es el cambio de precio multiplicado por `1 + C33`. Se usa el calendario de caja auditado. La búsqueda prueba cambios de precio en memoria y conserva los aportes y cobros publicados.

El informe interno muestra el mayor precio aprobado de la grilla y el siguiente precio, excluido. También identifica qué métricas dejan de cumplir PASS en ese segundo precio. Se comprueba la dirección de cada métrica, con una dirección diferente para el aporte en refi cuando aumenta la base de equity. Un intervalo totalmente negativo conserva sus límites y una bandera. Una grilla sin precio que cumpla queda PENDING con motivo. La comparación porcentual del precio pedido requiere un RLV positivo.

| Control de cálculo, USD sintéticos | Mayor precio que cumple | Siguiente precio | Métrica que limita |
| --- | ---: | ---: | --- |
| Recuperación de equity en refi | 160 | 170 | Recuperación en refi |
| Límite de capital sobre costo | 270 | 280 | Equity/TDC |
| Precio máximo negativo | −50 | −40 | Spread |
| Ocupación fuera del límite en toda la grilla | PENDING | — | Ocupación de equilibrio |

En una grilla de USD 1, C33 de 0 % y 2 % produce límites inferiores de USD 166 y USD 167 en el control de recuperación. En el expediente vigente, el CoC posrefi incompleto conserva el RLV Base PENDING. El dictamen real y el retorno histórico del 1101 siguen PENDING.

## Reproducción

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_lorena_screening test_worksheet_annual_coc test_lorena_screening test_threshold_rehearsal test_scenario_threshold_rehearsal
```

La prueba del expediente vigente usa `rehearse-workbook`, como se indica en [D231](worksheet-lorena-screening-D231.md). El respaldo conserva código, pruebas y esta guía. Los expedientes y PDF de validación quedan en el VPS.
