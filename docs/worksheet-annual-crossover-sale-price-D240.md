# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Precio mínimo de venta en una página](review/MiniUW_D240_Precio_Minimo_Venta.pdf). La recuperación se mide en valor presente desde el día del primer aporte, con la tasa mensual de cruce de cada escenario de D239. El cálculo conserva los flujos fechados de D238, la fecha de venta, los saldos de deuda al cierre y la regla de costos de venta.

| Escenario | Tasa mensual de cruce | Venta bruta de D238 | Mínimo con y sin refi | Aumento de precio |
| --- | ---: | ---: | ---: | ---: |
| Base | 0,6532 % | USD 4.571.428,57 | USD 4.749.316,96 | USD 177.888,39 · 3,89 % |
| Downside | 1,7903 % | USD 1.952.380,95 | USD 8.919.058,39 | USD 6.966.677,44 · 356,83 % |

La comisión sobre el precio es 4 % en Base y 7 % en Downside. El costo fijo permanece en USD 10.000 y USD 0, respectivamente. Al cruce las dos rutas tienen el mismo VAN. También comparten la fecha de salida y la fracción de cada dólar adicional del precio que llega al proyecto. Por eso, el precio bruto mínimo coincide dentro de cada escenario, aunque el cobro neto de venta por ruta difiere.

El aumento necesario se obtiene convirtiendo el déficit de valor presente en el efectivo adicional que debe entrar al cierre. Ese efectivo se divide por la escala de USD 10 y por la parte del precio que queda después de la comisión. Para cada ruta se comprueba que un centavo menos sigue dejando un déficit y que el centavo informado lo cubre en todo el intervalo exacto que encierra la tasa. El porcentaje de subida se calcula sobre el precio bruto de D238.

El dictamen real del 1101 y su retorno histórico siguen PENDING.

## Reproducción

    PYTHONPATH=src:tools python3 tools/miniuw_worksheet_v1.py compare-annual-crossover-sale expediente \
      --current-revision vigente.json --with-refi annual_hold_with_refinance \
      --without-refi annual_hold_without_refinance --output MiniUW_Precio_Minimo_Venta.pdf

El recibo JSON conserva el intervalo de tasa, las huellas de las cuatro cajas de D238, los costos, los saldos al cierre y la prueba del centavo en cada ruta. La prueba test_worksheet_annual_comparison vuelve a verificar ambos centavos con los eventos fechados originales.
