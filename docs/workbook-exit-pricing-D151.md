# D151 · Valor para refi, precio de salida y cobros por USD 10

## Si invierto USD 10, ¿cuánto aporto y cuándo cobro?

Los importes de la tabla son USD por cada USD 10 iniciales de equity agregado en el piloto sintético.

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
| Cobro de operación | 1,36 · 30/12/2028 | 0,55 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 14,09 · 30/12/2028 | 3,79 · 30/06/2029 |
| **Total cobrado** | **18,52** | **7,19** |
| **Sin recuperar al cierre** | **0,00** | **11,00** |

Los totales se calculan antes de redondear. El expediente completo da **FAIL simulado** con su criterio de múltiplo de equity. La decisión real queda **PENDING**.

## Valoración y venta del proyecto

| Partida | Base | Downside |
|---|---:|---:|
| C66 · Cap de refinanciación | 9,50 % | 11,50 % |
| Valor para refinanciación | USD 4.531.875,94 | USD 2.214.218,84 |
| Capacidad calculada y límite vinculante | USD 2.558.756,33 · DSCR | USD 1.439.242,25 · LTV |
| C67 · Cap de salida | 8,75 % | 10,50 % |
| Precio bruto de venta | USD 4.920.322,45 | USD 2.425.096,83 |
| C68 · Costo agregado sobre precio bruto | 4,00 % | 7,00 % |
| Costo de venta pagado al cierre | USD 196.812,90 | USD 169.756,78 |

## Cobertura de C66–C68

| Requisito y ubicación | Definición sintética | Módulo y evidencia | Pendiente real |
|---|---|---|---|
| `Inputs!A66:F66` · Cap de refinanciación | NOI anual de valoración dividido por C66 en la fecha de refi. El NOI bancario alimenta la prueba de DSCR. | M6 y T35. Se verifica el cambio de restricción activa entre LTV y DSCR y el bloqueo al superar la capacidad. | Fuente, vigencia y alcance de valoración y de los límites bancarios. |
| `Inputs!A67:F67` · Cap de salida | NOI de los doce meses posteriores a la venta dividido por C67. La regla de prueba usa ese valor como precio bruto. | M7 y T41. Se prueba el recálculo del precio, el costo de venta y el neto al cambiar C67. | Fuente del cap y soporte del precio de venta. |
| `Inputs!A68:F68` · Costos de venta | Fracción única y completa del precio bruto, pagada al cierre. El principal y la liberación de reserva se registran por separado. | M7, T43 y T29. Se concilian precio, fecha, huella del cálculo, deducción única y residual de caja. Se verifica cero explícito. | Inventario completo y alcance de los cargos de venta. |

Las tasas, el alcance y el uso del valor de salida como precio son supuestos del piloto. La valoración para refi alimenta capacidad, y la caja registra el desembolso neto de la refinanciación. La venta registra una sola distribución que incorpora el precio, el costo de venta, el pago de deuda y la reserva liberada. [Planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx) · [F06 y F08 en `/cards/5` y `/cards/7`](current-structure/MiniUW_Contratos_Financieros_Prioritarios_D09.json).

La solicitud sintética de USD 1.400.000 entra en ambos escenarios. Con C66 de 12 % en Downside, la capacidad LTV queda por debajo de esa solicitud y el escenario queda PENDING. Si falta una tasa, el alcance o el inventario de cargos, también se bloquean los flujos afectados. Una venta que requiere fondos adicionales queda PENDING mientras falte su regla de aporte. Si falta sólo el criterio de inversión o la revisión vigente, el dictamen queda PENDING y el expediente conserva los flujos calculables.

## Reproducción en el VPS

Con el runtime de OCR de D131, el verificador reproduce quince corridas y audita el expediente. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_exit_pricing_D151.py --output /tmp/miniuw-d151
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d151 \
  --current-revision templates/synthetic-workbook-current-revision-D151.json
```
