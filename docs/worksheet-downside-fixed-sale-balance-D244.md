# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Saldo de Downside en una página](review/MiniUW_D244_Saldo_Downside_6M.pdf). El ensayo sintético fija la venta bruta en **USD 6 millones** y recorta **50 % de la obra directa**, de USD 2.744.000 a USD 1.372.000. Usa la tasa de cruce original de Downside de **1,7903 % mensual**, los flujos de D238 y la comisión de venta del 7 %.

| Ruta | Aporte adicional por USD 10 | Cobro total nominal por USD 10 | VAN por USD 10 |
| --- | ---: | ---: | ---: |
| Con refi | USD 2,39 | USD 22,05 | **+USD 0,0662** |
| Sin refi | USD 2,27 | USD 22,44 | **−USD 0,0310** |

Se reducen proporcionalmente obra vertical, estacionamiento y sitio. Se recalculan contingencia, indirectos y financiación de obra. Todo el efectivo se descuenta al 30/03/2027, fecha del aporte inicial. Con refi se reciben USD 3,07 al refinanciar el 30/03/2029 y USD 18,77 netos de venta el 30/03/2030. Sin refi, se reciben USD 21,93 netos de venta en esa misma fecha. El PDF lista las fechas de los aportes adicionales y de los cobros operativos. Los flujos nominales visibles se redondean a centavos y el cálculo usa los importes exactos.

Los signos del VAN se verifican en todo el intervalo que contiene la tasa de cruce. El punto concilia con D243. El recorte del 50 % supera el mínimo con refi de 49,45 % y queda debajo del mínimo sin refi de 50,26 %. El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

    PYTHONPATH=src:tools python3 tools/miniuw_worksheet_v1.py compare-downside-fixed-sale-balance expediente \
      --current-revision vigente.json --with-refi annual_hold_with_refinance \
      --without-refi annual_hold_without_refinance --output MiniUW_Saldo_Downside_6M.pdf

El recibo vincula las cajas originales de D238 con los flujos recalculados, el intervalo de la tasa y el saldo descontado. La prueba test_worksheet_annual_comparison reproduce el VAN con los flujos fechados de cada ruta.
