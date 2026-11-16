# Si invierto USD 10, ¿cuánto cobro y cuándo?

La ruta sintética de tenencia anual proyecta cuatro trimestres después de la refinanciación. Los importes se expresan por cada USD 10 iniciales de equity agregado. Se calculan antes de redondear.

| Movimiento | Base | Downside |
| --- | ---: | ---: |
| Aporte inicial | USD 10,00 el 30/03/2027 | USD 10,00 el 30/03/2027 |
| Aportes adicionales totales | USD 4,87 | USD 8,32 |
| Cobro neto de refi | USD 2,03 el 30/09/2028 | USD 1,64 el 30/03/2029 |
| Primer trimestre operativo | USD 0,32 el 30/12/2028 | USD 0,10 el 30/06/2029 |
| Segundo trimestre operativo | USD 0,31 el 30/03/2029 | USD 0,05 el 30/09/2029 |
| Tercer trimestre operativo | USD 0,34 el 30/06/2029 | USD 0,07 el 30/12/2029 |
| Cuarto trimestre operativo | USD 0,24 el 30/09/2029 | Aporte USD 0,13 el 30/03/2030 |
| Cobro neto de venta | USD 13,68 el 30/09/2029 | USD 3,08 el 30/03/2030 |
| Cobro total | USD 16,92 | USD 4,94 |
| Caja sin recuperar al cierre | USD 0,00 | USD 13,38 |
| CoC anual posrefi | 9,38 % | 0,52 % |

Las fechas de cada aporte de obra se conservan en `cash_by_period` y `cash_per_usd_10.events`. El CoC concilia la caja de operación después de la reserva y la deuda con el equity remanente de la ruta. Los cobros de refi y venta pertenecen a sus respectivos cierres.

## Configuración y controles

En `rent_inputs.calendar_checks`, la ruta `interest_only_then_amortize` admite `quarterly_noi_before_reserves`, con cuatro importes fechados con evidencia por escrito. `sale_payment_index` se fija en 4 para la ruta anual y el NOI de salida debe corresponder a los 12 meses posteriores a la venta. Se simula un trimestre de sólo interés y tres amortizantes. La reserva anual C60 se deposita una sola vez, en el cuarto trimestre antes de la venta. El cierre concilia el principal restante y la disposición de reservas.

El cotejo comprueba el saldo de capital, la continuidad de cada movimiento y la coincidencia del CoC con la caja operativa. Un trimestre vacío o una solicitud de refi por encima de la capacidad deja PENDING la ruta. El cero explícito se conserva en su fecha. El resultado de la ruta se reproduce desde la planilla y queda en el expediente auditado. La planilla principal conserva el resultado y el PDF ya verificados. El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Reproducción

Desde la raíz del repositorio, con el [runtime OCR](workbook-plan-scan-D131.md) configurado:

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tests/test_worksheet_annual_holding.py --output /tmp/miniuw-d234
```
