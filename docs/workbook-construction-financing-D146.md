# D146 · Deuda de obra, aportes y cobros por USD 10

## Si invierto USD 10, ¿cuánto aporto y cuándo cobro?

Los importes de la tabla son USD por cada USD 10 iniciales de equity agregado del piloto sintético.

| Flujo | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00 | 10,00 |
| Aporte · 30/06/2027 | 0,00 | 0,76 |
| Aporte · 30/09/2027 | 4,66 | 0,04 |
| Aporte · 30/12/2027 | 0,05 | 7,03 |
| Aporte · 30/03, 30/06 y 30/09 de 2028 | 0,05 cada fecha | 0,07 cada fecha |
| Aporte · 30/12/2028 y 30/03/2029 | — | 0,07 cada fecha |
| **Total aportado** | **14,87** | **18,19** |
| Cobro neto de refinanciación | 3,07 · 30/09/2028 | 2,86 · 30/03/2029 |
| Cobro de operación | 1,69 · 30/12/2028 | 1,01 · 30/06/2029 |
| Cobro neto de venta | 15,43 · 30/12/2028 | 8,24 · 30/06/2029 |
| **Total cobrado** | **20,19** | **12,10** |
| **Sin recuperar al cierre** | **0,00** | **6,09** |

Los totales se calculan antes de redondear. El primer desembolso del banco es el 30/06/2027. El segundo ocurre al fin de obra, el 30/09/2027 en Base y el 30/12/2027 en Downside. En cada fecha el banco desembolsa USD 317.500 en Base y USD 343.000 en Downside. El saldo que se cancela al refinanciar asciende a USD 635.000 y USD 686.000 respectivamente. Los intereses de obra suman USD 57.150 en Base y USD 102.900 en Downside. El criterio de múltiplo de equity del expediente completo da **FAIL simulado** y el dictamen real queda **PENDING**.

## Cobertura y trazabilidad

Las celdas pertenecen a la [planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx). F17 define las condiciones de evidencia y los contratos M5-01 a M5-10 describen los puentes de caja y deuda. [Contrato F17 en `/cards/8`](current-structure/MiniUW_Contratos_Financieros_Complementarios_D10.json) · [Contratos M5](model-construction-finance.md).

| Celda y ubicación | Definición en el piloto | Módulo y cálculo | Evidencia y pendiente |
|---|---|---|---|
| C51 · `Inputs!A51:F51` | LTC de 60 % en Base y 50 % en Downside aplicado al hard directo elegible. El compromiso es el menor entre ese resultado y el tope contractual | M5 compromiso no revolvente. T68 controla disponibilidad por fecha y acumulada | Compromisos USD 1.524.000 y USD 1.250.000. Se verifica el bloqueo por exceso de desembolso. Elegibilidad y límites reales pendientes. |
| C52 · `Inputs!A52:F52` | Tasa nominal anual simple de 8 % y 10 %, con convención sintética 30/360. Se aplica 2 % y 2,5 % por trimestre al saldo de apertura más el draw del corte | M5 intereses pagados por fecha y aporte para cubrir el faltante | Se coteja cada intervalo, cero explícito y el incremento al adelantar el segundo draw. Tasa y convención reales pendientes. |
| C53 · `Inputs!A53:F53` | Comisión de 1 % y 1,5 % sobre el compromiso. Se paga al abrir la línea | M5 uso de caja inicial y recálculo de aportes | Comisiones de USD 15.240 y USD 18.750. Se verifica que un cero explícito reduzca los aportes. Base y forma de pago reales pendientes. |
| Calendario · `Inputs!A46:F47` | El banco financia el 25 % de las facturas elegibles de cada corte de obra. El vencimiento y el límite por corte vienen de los términos sintéticos | M4 orden de pagos, M5 desembolsos e intereses, M6 cancelación del principal y remanente de refi | Adelantar el fin de obra Downside de diciembre a septiembre suma USD 8.575 de interés. Se bloquea un vencimiento anterior a la refi. Calendario, disponibilidad y condiciones reales pendientes. |

La caja de apertura se usa antes de pedir aportes adicionales. El libro completa el faltante verificado de cada fecha con equity según la regla sintética declarada. Los intereses se pagan en efectivo, incluido el último trimestre hasta la refi. La liquidación de refi paga el principal de obra una sola vez y distribuye el remanente después de su comisión. El costo elegible excluye la financiación y evita circularidad entre intereses y compromiso. Los cobros operativos estabilizados y la venta conservan sus calendarios del piloto D145. Si el calendario tiene muchos cortes, el expediente de cálculo conserva todas las fechas.

Los datos sin confirmar y los límites excedidos dejan **PENDING** el escenario afectado. Se incluyen disponibilidad insuficiente, vencimiento y una refi que no cubre la deuda. Si falta el criterio de inversión o la revisión vigente, el dictamen queda PENDING y los cálculos sintéticos trazables siguen disponibles en el expediente.

## Reproducción en el VPS

El verificador reproduce quince corridas de planilla y audita el expediente original. Genera un PDF de una página y el detalle fechado de usos, aportes, deuda e intereses.

```bash
PYTHONPATH=src:tests python3 tools/check_worksheet_construction_financing_D146.py --output /tmp/miniuw-d146
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d146 \
  --current-revision templates/synthetic-workbook-current-revision-D146.json
```
