# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Cruce recalculado de Downside en una página](review/MiniUW_D245_Cruce_Downside_6M.pdf). El nuevo cruce es **1,3528 % mensual** con venta bruta de USD 6 millones y recorte del 50 % de la obra directa. La tasa de 1,7903 % corresponde a las cajas originales de D238. D245 usa las cajas modificadas de D244 y descuenta al 30/03/2027, fecha del primer aporte.

| Ruta | Aporte adicional por USD 10 | Cobro nominal total por USD 10 | Saldo en valor presente al nuevo cruce |
| --- | ---: | ---: | ---: |
| Con refi | USD 2,39 | USD 22,05 | **+USD 1,8721** |
| Sin refi | USD 2,27 | USD 22,44 | **+USD 1,8721** |

El aumento de precio agrega lo mismo a las dos rutas en la fecha de venta, después de la comisión del 7 %. Ese cambio común se cancela al comparar los VAN. El recorte altera los flujos de financiación de obra, sus pagos y el cobro adelantado con refi. La nueva tasa iguala los VAN de esas cajas fechadas. Por debajo del cruce, la ruta sin refi tiene mayor VAN. Por encima, la ruta con refi tiene mayor VAN.

La diferencia de las cajas empieza positiva con el adelanto de la refi y las diferencias posteriores son negativas. Esa estructura prueba un cruce único para tasas no negativas. El recibo conserva un intervalo exacto con cambio de signo para la diferencia y verifica que ambos VAN permanezcan positivos en todo ese intervalo. Los cobros y aportes nominales son los mismos de D244.

El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

    PYTHONPATH=src:tools python3 tools/miniuw_worksheet_v1.py compare-downside-fixed-sale-crossover expediente \
      --current-revision vigente.json --with-refi annual_hold_with_refinance \
      --without-refi annual_hold_without_refinance --output MiniUW_Cruce_Downside_6M.pdf

El recibo vincula las cajas de origen de D238, las cajas ajustadas de D244 y los intervalos verificados de ambas tasas. La prueba test_worksheet_annual_comparison coteja los VAN de las dos rutas con sus flujos fechados.
