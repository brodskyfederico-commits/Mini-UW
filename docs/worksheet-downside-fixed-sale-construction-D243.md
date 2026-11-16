# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Recortes con precios de venta fijos en una página](review/MiniUW_D243_Recorte_Obra_Venta_Fija.pdf). Se usan los flujos sintéticos de Downside de D238 y se conserva su tasa de cruce original de **1,7903 % mensual**. La venta se mantiene el 30/03/2030 y paga una comisión del 7 % sobre el precio bruto. La obra directa de referencia es USD 2.744.000.

| Venta bruta | Recorte directo con refi | Recorte directo sin refi |
| ---: | ---: | ---: |
| USD 4.000.000 | USD 2.397.953,38 · 87,39 % | USD 2.550.826,92 · 92,96 % |
| USD 5.000.000 | USD 1.826.958,96 · 66,58 % | USD 1.857.193,81 · 67,68 % |
| USD 6.000.000 | USD 1.356.788,54 · 49,45 % | USD 1.379.242,41 · 50,26 % |

El recorte se aplica proporcionalmente a obra vertical, estacionamiento y sitio. Se recalculan contingencia, indirectos, financiación de obra y aportes con D241. El aumento del precio agrega caja al cierre después de la comisión. El precio de cada escenario se fija durante toda la búsqueda del recorte mínimo.

Al mínimo se recuperan en valor presente los USD 10 iniciales y todos los aportes adicionales. Un centavo menos de recorte deja déficit en todo el intervalo que contiene la tasa de cruce. Por ejemplo, con una venta de USD 6 millones, los aportes adicionales y cobros totales nominales por USD 10 son USD 2,46 y USD 22,04 con refi, y USD 2,23 y USD 22,45 sin refi.

El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

    PYTHONPATH=src:tools python3 tools/miniuw_worksheet_v1.py compare-downside-fixed-sale expediente \
      --current-revision vigente.json --with-refi annual_hold_with_refinance \
      --without-refi annual_hold_without_refinance --output MiniUW_Recorte_Obra_Venta_Fija.pdf

El recibo conserva las cajas modificadas, su vínculo a D238 y las comprobaciones de los seis mínimos. La prueba test_worksheet_annual_comparison registra los seis recortes y verifica sus signos en el intervalo de tasa. Los controles anteriores de D241 y D242 se conservan.
