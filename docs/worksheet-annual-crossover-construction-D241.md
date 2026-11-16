# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Reducción de obra en una página](review/MiniUW_D241_Reduccion_Obra.pdf). La sensibilidad usa las cajas auditadas de D238, el precio y la fecha de venta de cada escenario y las tasas de cruce originales de D239. Se mantiene el aporte inicial de referencia. El recorte proporcional se aplica a obra vertical, estacionamiento y sitio. D144 y D146 recalculan contingencia, indirectos, desembolsos, intereses, comisiones y aportes. Los términos bancarios y los demás supuestos del expediente se conservan.

| Ruta | Tasa mensual | Recorte mínimo de obra directa | Ahorro de presupuesto con contingencia e indirectos | VAN por USD 10 en la prueba |
| --- | ---: | ---: | ---: | ---: |
| Base con refi | 0,6532 % | USD 125.513,82 | USD 144.968,46 | USD 0,00 al mínimo |
| Base sin refi | 0,6532 % | USD 125.487,65 | USD 144.938,24 | USD 0,00 al mínimo |
| Downside con refi | 1,7903 % | Inalcanzable recortando obra | USD 3.410.792,00 al llevar obra directa a cero | −USD 2,98 |
| Downside sin refi | 1,7903 % | Inalcanzable recortando obra | USD 3.410.792,00 al llevar obra directa a cero | −USD 3,63 |

En Base la obra directa de USD 2.540.000 baja aproximadamente 4,94 % en ambas rutas. El precio de venta permanece en USD 4.571.428,57. Los cobros totales por cada USD 10 iniciales son USD 17,05 con refi y USD 17,22 sin refi. Los dos casos aportan USD 4,38 adicionales y venden el 30/09/2029.

En Downside se conserva el precio de USD 1.952.380,95. El recorte de USD 2.744.000 lleva a cero el costo directo de las tres partidas y sus porcentajes dependientes de presupuesto. Con ese recorte límite, la venta sigue siendo el 30/03/2030 y los cobros llegan a USD 11,47 con refi y USD 12,00 sin refi por cada USD 10 iniciales. El VAN conserva un déficit en ambas rutas, aun con esos cobros nominales.

La corrida con recorte cero reproduce D238. Se verifica que el gasto de obra neto de desembolsos crece con el costo en cada fecha de aporte bajo las fórmulas de D144 y D146. El saldo de obra y el efectivo disponible se vuelven a conciliar al refinanciar o vender. En Base se comprueba que un centavo menos de recorte deja déficit y que el mínimo informado lo cubre en el intervalo que contiene la tasa de cruce.

El dictamen real del 1101 y el retorno histórico siguen PENDING.

## Reproducción

    PYTHONPATH=src:tools python3 tools/miniuw_worksheet_v1.py compare-annual-crossover-construction expediente \
      --current-revision vigente.json --with-refi annual_hold_with_refinance \
      --without-refi annual_hold_without_refinance --output MiniUW_Reduccion_Obra.pdf

El recibo JSON vincula las cuatro cajas de origen y conserva los flujos fechados de cada prueba, los límites de la tasa y la comprobación del centavo. La prueba test_worksheet_annual_comparison coteja el recorte mínimo y el resultado al reducirlo en un centavo. También verifica el déficit de Downside con obra directa cero.
