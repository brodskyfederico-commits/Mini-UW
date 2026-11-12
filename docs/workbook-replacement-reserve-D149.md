# D149 · Reserva de reposición, aportes y cobros por USD 10

## Si invierto USD 10, ¿cuánto aporto y cuándo cobro?

Los importes de esta tabla son USD por cada USD 10 iniciales de equity agregado en el piloto sintético.

| Flujo | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00 | 10,00 |
| Aporte · 30/06/2027 | 0,00 | 0,76 |
| Aporte · 30/09/2027 | 4,66 | 0,04 |
| Aporte · 30/12/2027 | 0,05 | 7,03 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,05 cada fecha | 0,07 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,07 cada fecha |
| **Total aportado** | **14,87** | **18,19** |
| Cobro neto de refinanciación | 3,07 · 30/09/2028 | 2,86 · 30/03/2029 |
| Cobro de operación | 1,52 · 30/12/2028 | 0,69 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 15,09 · 30/12/2028 | 7,30 · 30/06/2029 |
| **Total cobrado** | **19,68** | **10,85** |
| **Sin recuperar al cierre** | **0,00** | **7,34** |

Los totales se calculan antes de redondear. Base deposita USD 31.200 de caja del proyecto y libera los USD 31.200 al vender. Downside deposita USD 52.000, libera USD 26.000 y transfiere USD 26.000 restringidos al comprador. El criterio sintético de múltiplo de equity da **FAIL simulado** en el expediente completo. La decisión real queda **PENDING**.

## Cobertura de C60

| Requisito y ubicación | Definición sintética | Módulo y evidencia | Pendiente real |
|---|---|---|---|
| `Inputs!A60:F60` · Reserva de reposición | C60 por unidad y año × 26 unidades elegibles confirmadas. USD 1.200 por unidad en Base y USD 2.000 en Downside. | M2 y T25. El depósito es una transferencia de caja libre a restringida, fuera del NOI. El saldo inicial se declara en cero y el saldo final coincide con el depósito. | Tarifa, unidades, política y calendario efectivos. |
| Destino al vender · `rent_inputs/replacement_reserve/scenarios` | Liberación de 100 % en Base y 50 % en Downside. El remanente se entrega al comprador como caja restringida. | M7 y T29. El cierre toma el saldo restringido de T25 y concilia la liberación y el saldo entregado. La liberación se suma una vez al cobro neto de venta. | Instrucción de cierre y titularidad documentadas. |
| Faltante de caja · `rent_inputs/replacement_reserve/rules/shortfall_funding` | Si la caja de operación después de deuda queda por debajo del depósito, la regla de prueba permite un aporte por la diferencia. | M5 y T23–T25. En la prueba de estrés, Downside requiere USD 0,18 adicionales por USD 10 el 30/06/2029. | Autorización y fuente de aportes adicionales. |

El depósito se registra en la liquidación anual de operación, antes del cierre de venta del mismo día. La política declara que el cálculo del NOI, la capacidad de refinanciación y el precio bruto de venta se basan en las partidas operativas de D148, con la reserva registrada en caja. El expediente guarda la conciliación, la fecha de ambos movimientos y la huella de cada corrida. [Planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx) · [Contrato F05 en `/cards/4`](current-structure/MiniUW_Contratos_Financieros_Prioritarios_D09.json).

Un faltante de tasa, unidades, política o destino del saldo deja **PENDING** el escenario afectado. Si falta sólo el criterio o la revisión vigente, el dictamen queda PENDING y los flujos calculables se muestran condicionados al expediente.

## Reproducción en el VPS

Con el runtime de OCR de D131, el verificador reproduce trece corridas y audita el expediente. La prueba incluye depósito cero, liberaciones de 0 %, 50 % y 100 %, variación de unidades y aporte por caja insuficiente. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_replacement_reserve_D149.py --output /tmp/miniuw-d149
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d149 \
  --current-revision templates/synthetic-workbook-current-revision-D149.json
```
