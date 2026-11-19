# Si invierto USD 10, ¿cuánto cobro y cuándo?

Continuación: [C61–C62, impuesto, NOI y caja por USD 10 en D260](workbook-tax-sensitivities-D260.md).

D259 conecta C60 con la caja restringida, el cierre y el retorno por USD 10, por separado y junto con los gastos C57–C59 de D258. El ensayo usa respaldos sintéticos D200 y la misma escala de 10/2.400.000 de equity inicial verificado. El aporte inicial ocurre el 30/03/2027; los aportes posteriores se conservan aparte. El dictamen operativo y el retorno personal sin términos de reparto permanecen PENDING.

| Escenario y variante | Aporte adicional por USD 10 iniciales | Cobro total por USD 10 | Caja sin recuperar después de venta |
|---|---:|---:|---:|
| Base original | USD 4,8670 | USD 18,0594 | USD 0,0000 |
| Base, sólo C60 +1 % | USD 4,8670 | USD 18,0594 | USD 0,0000 |
| Base, C57–C59 de D258 | USD 4,8670 | USD 18,0357 | USD 0,0000 |
| Base, C57–C60 juntos | USD 4,8670 | USD 18,0357 | USD 0,0000 |
| Downside original | USD 8,1893 | USD 6,0767 | USD 12,1126 |
| Downside, sólo C60 +1 % | USD 8,1893 | USD 6,0756 | USD 12,1137 |
| Downside, C57–C59 de D258 | USD 8,1893 | USD 6,0521 | USD 12,1372 |
| Downside, C57–C60 juntos | USD 8,1893 | USD 6,0510 | USD 12,1383 |

En Base conjunto se agregan aproximadamente USD 4,655375 el 30/09/2027 y USD 0,052917 por trimestre entre el 30/12/2027 y el 30/09/2028. Se cobran USD 2,846667 de refi el 30/09/2028 y USD 1,427822 de operación más USD 13,761245 de venta el 30/12/2028. En Downside conjunto se agregan USD 0,762275 el 30/06/2027, USD 0,035729 el 30/09/2027, USD 7,034046 el 30/12/2027 y USD 0,071458 por trimestre entre el 30/03/2028 y el 30/03/2029. Se cobran USD 2,445833 de refi el 30/03/2029 y USD 0,545462 de operación más USD 3,059743 de venta el 30/06/2029. Cada fecha e importe exacto se conserva en `cash_per_usd_10.events`; el redondeo se aplica después de totalizar.

## Reserva y liquidación

C60 conserva su definición de caja restringida. En el perfil de prueba se deposita la reserva anual al liquidar la operación, antes de la venta. La política de apertura cero y ausencia de otros movimientos debe estar declarada. La fracción liberada al vendedor y el remanente transferido al comprador tienen fuente propia. Los valores del ensayo no se adoptan como reglas para un deal real.

| Importe del proyecto completo, USD | Base original | Base con C60 +1 % | Downside original | Downside con C60 +1 % |
|---|---:|---:|---:|---:|
| Tarifa anual por unidad elegible | 1.200 | 1.212 | 2.000 | 2.020 |
| Depósito, 26 unidades elegibles | 31.200 | 31.512 | 52.000 | 52.520 |
| Liberación al vendedor al vender | 31.200 | 31.512 | 26.000 | 26.260 |
| Transferencia restringida al comprador | 0 | 0 | 26.000 | 26.260 |

La política declarada del caso devuelve el 100 % en Base y el 50 % en Downside. Por eso, en Base el aumento de C60 cambia la composición entre cobro operativo y venta, conservando el cobro nominal total. En Downside la parte transferida aumenta y el vendedor cobra menos. Se concilian ambos movimientos incluso cuando tienen la misma fecha; no se compensan antes de construir el flujo bruto.

| Variable o proceso | Definición y conexión | Evidencia de validación | Estado |
|---|---|---|---|
| Inputs!C60 | Tarifa anual × unidades elegibles acreditadas | D149: depósito exacto y cita del cambio | Conectado en sintético |
| Caja operativa | NOI menos servicio y depósito, con aporte adicional si falta caja bajo la política declarada | Conciliación D200 de fuentes y usos; aporte y cobro separados | Validado en sintético |
| Caja restringida | Depósito = liberación + transferencia al comprador | Saldos y residuales de operación y venta exactos | Validado en sintético |
| NOI operativo, bancario y de valoración | Conservan su base ante un cambio aislado de C60 | Comparación por período, capacidad y precio bruto de venta sin variación | Validado en sintético |
| NOI operativo después de reserva | NOI del período operativo menos su depósito efectivo | Salida `operating_noi_after_reserve` con período, huella de NOI y cita de C60 | Validado en sintético |
| C57–C60 juntos | Recálculo de gastos y reserva con sus bases separadas | Ocho cambios individuales y dos conjuntos; conciliación de cada flujo por USD 10 | Validado en sintético |

La salida después de reserva corresponde a la ventana operativa declarada. Las métricas de desempeño mantienen sus definiciones y períodos vigentes. La comparación por deltas nominales de caja no constituye un criterio PASS/FAIL: dos variantes pueden cobrar lo mismo y tener distinta necesidad de fondos o distinto NOI después de reservas.

## Contrato sintético v7

`rent_inputs.sensitivities` admite `miniuw.synthetic-worksheet-sensitivities.v7` en el perfil de aceptación técnica. Extiende el contrato de gastos [D258](workbook-expense-sensitivities-D258.md) con C60 y hasta cuatro cambios distintos por escenario. Los contratos anteriores conservan su alcance.

C60 exige una operación explícita, valor y fuente. La unidad de reemplazo es `USD_per_eligible_unit_per_year`; también admite cambios relativos. Los puntos básicos y porcentuales siguen reservados a las fracciones, como C58. Se conserva `expense_support` individual y conjunto; sólo los cambios que incluyen C59 requieren revisión del seguro. Elegibilidad, fracción de liberación y política de fondeo de la reserva se toman de sus respaldos originales, sin deducirlos del valor de C60.

El ensayo agrega C60 +1 % relativo a C57 +1 %, C58 +1 pb y C59 +1 % de D258. Cada campo se ejecuta solo y los cuatro juntos. La evidencia agrega el detalle de reserva de reposición, la cuenta permanente separada, el servicio de deuda y el cierre de venta. El JSON conserva el límite de 48 KiB y B16 reproduce el expediente desde sus respaldos. El PDF integral original conserva su alcance.

## Faltantes, cero y necesidad de fondos

Los controles prueban C60 vacío en la base o en el cambio y verifican que nunca se convierta en cero. También prueban ausencia de elegibilidad, de la fracción liberada y de su fuente: el cálculo afectado queda PENDING. Una cantidad elegible igual a cero sólo produce depósito cero cuando está declarada explícitamente.

Otro ensayo declara C60 = 0 en Downside y verifica depósito, saldo restringido, liberación y transferencia cero. Para Base se declara una tarifa de control de USD 100.000 por unidad/año, generando una reserva superior a la caja operativa disponible. La política sintética vigente solicita un aporte antes de liquidar la venta: se conservan USD 9,272275 adicionales por USD 10 iniciales el 30/12/2028 y el cobro de venta posterior de USD 24,484963 en esa misma fecha. Con la liberación completa de Base el beneficio nominal permanece igual, aunque los aportes y cobros brutos aumentan. El perfil conserva el orden declarado de liquidación; la disponibilidad real de esos fondos sigue pendiente de evidencia.

Este control comprueba que un neto total correcto no oculte una llamada de capital. Los escenarios con información faltante permanecen PENDING y su ranking incompleto queda vacío. Los datos de prueba no autorizan fondeo ni decisiones reales.

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_reserve_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_replacement_reserve_D149.py --output /tmp/miniuw-d259-d149
```

Se utilizan las dependencias de referencia y OCR del repositorio. Los paquetes generados y registros del VPS quedan locales; GitHub conserva código, pruebas y esta descripción. La validación profesional, otros períodos de reserva y el uso real mantienen sus requisitos de fuente y aprobación. Sin despliegue.

En el VPS pasaron las tres pruebas nuevas: ocho cambios individuales y dos conjuntos válidos, además de los controles de faltantes, aporte adicional y cero explícito. D149 pasó sus trece casos de planilla, con siete PENDING esperados. B16 reprodujo sin diferencias el expediente D258 guardado con sensibilidades v6. Son verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.
