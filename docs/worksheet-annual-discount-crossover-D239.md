# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Tasas de cruce en una página](review/MiniUW_D239_Tasa_Mensual_Refi.pdf). D239 aplica una tasa mensual efectiva a los 52 movimientos de caja auditados de D238. Cada cobro y aporte se descuenta al 30/03/2027, fecha del aporte inicial de USD 10 de equity del proyecto. El descuento usa los meses calendario transcurridos.

| Escenario | Tasa mensual de cruce | VAN común aproximado por USD 10 | Adelanto por refi |
| --- | ---: | ---: | --- |
| Base | 0,6532 % | −USD 0,59 | USD 2,03 el 30/09/2028 |
| Downside | 1,7903 % | −USD 14,25 | USD 1,64 el 30/03/2029 |

Por debajo de la tasa de cruce, vender sin refinanciar da un VAN mayor. Por encima, refinanciar da un VAN mayor. El cálculo usa caja neta, que incluye aportes adicionales y cobros parciales. El VAN compara valor después de restar el aporte inicial y los demás aportes fechados.

Al cancelar los movimientos idénticos, la diferencia con refi menos sin refi empieza positiva en el cierre de refi y las diferencias posteriores son negativas. Al descontar al primer movimiento diferencial, el saldo de esas diferencias aumenta estrictamente con la tasa mensual no negativa y pasa de negativo a positivo una vez. El recibo conserva los dos extremos exactos del intervalo y los signos del VAN calculado desde el aporte inicial.

El dictamen real del 1101 y el retorno histórico siguen PENDING.

## Reproducción

    PYTHONPATH=src:tools python3 tools/miniuw_worksheet_v1.py compare-annual-crossover expediente \
      --current-revision vigente.json --with-refi annual_hold_with_refinance \
      --without-refi annual_hold_without_refinance --output MiniUW_Tasa_Mensual_Refi.pdf

El recibo JSON vincula la revisión, los resultados fuente y las cuatro cajas con sus huellas SHA-256. Los extremos del cruce se cotejan movimiento por movimiento con test_worksheet_annual_comparison.
