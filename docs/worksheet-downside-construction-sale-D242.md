# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Combinaciones de Downside en una página](review/MiniUW_D242_Obra_y_Venta_Downside.pdf). El ensayo usa el caso sintético D238, una tasa mensual de cruce original de 1,7903 % y venta el 30/03/2030. La obra directa inicial es USD 2.744.000 y el precio bruto inicial es USD 1.952.380,95.

| Recorte de obra directa | Ahorro directo | Precio mínimo con refi | Subida vs. D238 | Precio mínimo sin refi | Subida vs. D238 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 % | USD 0 | USD 8.919.058,39 | 356,83 % | USD 8.919.058,39 | 356,83 % |
| 25 % | USD 686.000 | USD 7.426.692,33 | 280,39 % | USD 7.450.445,38 | 281,61 % |
| 50 % | USD 1.372.000 | USD 5.967.646,91 | 205,66 % | USD 6.015.153,02 | 208,09 % |
| 75 % | USD 2.058.000 | USD 4.582.547,40 | 134,72 % | USD 4.696.913,53 | 140,57 % |
| 100 % | USD 2.744.000 | USD 3.407.011,14 | 74,51 % | USD 3.726.831,21 | 90,89 % |

Para cada recorte se reducen proporcionalmente obra vertical, estacionamiento y sitio. Se recalculan el presupuesto, la financiación de obra, los aportes y los cobros fechados con D241. Con esa caja se aplica D240 al precio de venta, usando la comisión de 7 %. El precio bruto mínimo es el primer centavo con valor presente neto no negativo en todo el intervalo que contiene la tasa de cruce. La tasa, las fechas y los demás términos se mantienen en el análisis. El recorte del 100 % es el límite con obra directa cero.

Con un recorte del 50 % y la venta en su mínimo, cada USD 10 iniciales exige USD 2,39 adicionales y cobra USD 21,93 en la ruta con refi. La ruta sin refi exige USD 2,27 adicionales y cobra USD 22,50. Son cobros nominales totales, incluyendo los flujos que se descuentan a la fecha inicial. La hoja muestra esos totales para los cinco recortes.

El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

    PYTHONPATH=src:tools python3 tools/miniuw_worksheet_v1.py compare-downside-construction-sale expediente \
      --current-revision vigente.json --with-refi annual_hold_with_refinance \
      --without-refi annual_hold_without_refinance --output MiniUW_Obra_y_Venta_Downside.pdf

El recibo conserva la caja recalculada de cada ruta al precio de D238, su huella, los límites de la tasa y las pruebas del precio mínimo y de un centavo menos. El caso sin recorte debe reproducir la caja original de D238 y los precios mínimos de D240.
