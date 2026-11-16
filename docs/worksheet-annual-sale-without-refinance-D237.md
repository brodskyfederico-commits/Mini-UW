# Si invierto USD 10, ¿cuánto cobro y cuándo?

D237 añade la venta al término de cuatro trimestres conservando la deuda de obra. El ensayo usa el mismo calendario de obra, NOI trimestral, precio y fecha de venta que la ruta anual con refinanciación. Se mantienen los flujos brutos y sus fechas sobre USD 10 de equity inicial del proyecto. El dictamen real y los retornos histórico y personal siguen PENDING.

| Escenario y ruta | Aporte adicional | Cobros por refinanciación | Cobros de operación | Cobro neto de venta | Cobro total | Sin recuperar |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| Base con refi | USD 4,87 | USD 2,03 el 30/09/2028 | USD 1,20 | USD 13,68 el 30/09/2029 | USD 16,92 | USD 0,00 |
| Base sin refi | USD 4,87 | N/A | USD 1,35 | USD 15,73 el 30/09/2029 | USD 17,08 | USD 0,00 |
| Downside con refi | USD 8,32 | USD 1,64 el 30/03/2029 | USD 0,21 | USD 3,08 el 30/03/2030 | USD 4,94 | USD 13,38 |
| Downside sin refi | USD 8,23 | N/A | USD 0,41 | USD 4,82 el 30/03/2030 | USD 5,22 | USD 13,01 |

El aporte inicial de USD 10 se fecha el 30/03/2027. En la ruta sin refi, los cobros operativos empiezan el 30/12/2028 en Base y el 30/06/2029 en Downside. Downside requiere un aporte operativo de USD 0,04 el día de la venta. Las sumas se redondean sobre importes exactos. La hoja de una página identifica cada movimiento con su fecha.

## Requisitos de la ruta y criterios

- Declara cuatro trimestres de NOI y cuatro tasas de interés de intervalo sobre la deuda de obra. El cero explícito se respeta. Un trimestre sin importe o fuente deja la ruta PENDING.
- El principal permanece constante durante la tenencia y se paga en la venta. El vencimiento debe cubrir esa fecha. El ensayo usa una extensión documentada en cada escenario con comisión explícita de USD 0. Una extensión con costo o sin documentación queda PENDING en esta versión.
- La reserva anual de reposición se deposita una vez y se concilia al cierre. El valor de salida usa el NOI de los 12 meses posteriores a la venta, con su base declarada antes de reservas.
- La caja de la ruta se reproduce aun cuando se retiran los campos de deuda permanente y capacidad. El cotejo de Lorena deja como N/A la recuperación, el aporte y el CoC de refi. TIR y múltiplo se cotejan sobre toda la caja fechada. El RLV Base de esta ruta sigue PENDING hasta confirmar su criterio aplicable. En Downside el RLV figura N/A bajo D230.

## Reproducción

    PYTHONPATH=src:tests:tools python3 tests/test_worksheet_annual_sale_without_refi.py --output /tmp/miniuw-d237

El ensayo guarda el expediente y la revisión designada, un recibo auditable y el PDF de la ruta sin refi. La opción --annual-pdf también está disponible al cotejar --route annual_hold_without_refinance desde el expediente vigente.
