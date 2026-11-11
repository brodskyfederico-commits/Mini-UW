# Si invierto USD 10, ¿cuánto cobro y cuándo?

D107 reproduce el efecto de dos revisiones sintéticas de un plano en los aportes y cobros de Base y Downside. Todas las filas comienzan con un aporte de USD 10 el **30/03/2027**. Los dos cobros se liquidan el **30/06/2028**, primero la caja del año operativo y luego el neto de venta. El ejemplo representa el capital agregado del proyecto.

| Escenario y plano | Aporte extra 30/06/2027 | Cobro de operación 30/06/2028 | Cobro neto de venta 30/06/2028 | Cobro total | Sin recuperar al vender |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base, original | 3,54 | 1,57 | 16,59 | 18,16 | 0,00 |
| Base, revisado | 0,42 | 1,07 | 11,34 | 12,41 | 0,00 |
| Downside, original | 3,54 | 1,24 | 10,68 | 11,92 | 1,63 |
| Downside, revisado | 0,42 | 0,84 | 7,24 | 8,08 | 2,34 |

Importes en USD por USD 10 iniciales. El saldo sin recuperar compara lo cobrado con los USD 10 iniciales más todos los aportes extra, sin descuento. El motor calcula con racionales exactos y redondea cada importe mostrado de forma independiente.

## Qué cambió y de dónde sale cada número

Los [cuadros D105](plan-schedule-intake-D105.md) declaran 20 unidades 1BR-A, con área rentable de 710 → 690 ft² por unidad, y un grupo 2BR-A que pasa de 6 unidades a 0. La segunda revisión carece de superficie bruta del edificio. Las [tarifas D106](plan-calculation-impact-D106.md) se reutilizan para ambas revisiones. El ensayo elige los demás datos sintéticos y conserva los mismos supuestos de cada escenario al cambiar el plano.

| Concepto | Supuesto de la prueba |
| --- | --- |
| Costo y financiación de obra | USD 125.000 por unidad. USD 2.400.000 de equity inicial y aporte de la diferencia al pagar la obra. Deuda y refinanciación ausentes por diseño. |
| Renta y gastos | USD 2/ft² al mes en 1BR-A y USD 1.800/unidad al mes en 2BR-A. Gastos de USD 600/unidad al año, USD 900/mes fijos, administración del 5 % de renta residencial efectiva e impuesto fijo sintético de USD 12.000/año. |
| Base | Vacancia del 5 % y concesiones del 2 %, sobre el bruto. Cap de salida del 9 %. |
| Downside | Vacancia del 20 % y concesiones del 5 %, sobre el bruto. Cap de salida del 11 %. |
| Operación y venta | Se cobran y pagan todos los devengos al terminar el año operativo. El NOI de los 12 meses desde la venta se calcula aparte bajo el supuesto de las mismas rentas y costos. Precio de venta sintético igual a ese NOI dividido por el cap. Costos de venta del 5 % del precio. |

El modelo lleva el conteo al presupuesto vertical y al aporte extra de obra. Lleva el conteo y el área rentable a renta, gastos, NOI operativo y NOI de salida. Concilia la caja operativa y los saldos que pasan al cierre. El libro de aportes y cobros toma como denominador exclusivamente el aporte inicial. Se prueban también los cambios de área rentable, unidades y superficie bruta por separado.

**PENDING** si falta un dato necesario. Si la cotización usa GSF, el plano revisado carece de ese dato y Downside retira todas sus cifras por USD 10 en esa variante. Si falta un conteo o un área rentable exigida por la tarifa, el resultado afectado se retira también. El cero declarado de unidades conserva su efecto en las ramas por unidad.

## Reproducción

```bash
PYTHONPATH=src python3 tools/plan_return_D107.py check
PYTHONPATH=src python3 tools/plan_return_D107.py report
```

El JSON conserva los hashes y punteros de los cuadros, los hashes de las corridas de renta a NOI, conciliación, valor de salida, cierre y retorno, y los flujos fechados en racionales exactos. El caso usa los productores existentes T21/T22, T25, T41 y T29/T30 con el libro de capital T23. El ejemplo abarca obra, un año estabilizado y venta. Quedan pendientes el piloto con datos de Lorena, la conciliación técnica del plano y la decisión de inversión. El ensayo conserva el alcance de capital agregado y las tarifas sólo pertenecen a la prueba.
