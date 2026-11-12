# D154 · Crecimiento de rentas y gastos, NOI y retorno

## Si invierto USD 10, ¿cuánto cobro y cuándo?

Importes en USD por cada USD 10 iniciales del equity agregado del piloto sintético.

| Flujo | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00 | 10,00 |
| Aporte · 30/06/2027 | — | 0,76 |
| Aporte · 30/09/2027 | 4,66 | 0,04 |
| Aporte · 30/12/2027 | 0,05 | 7,03 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,05 cada fecha | 0,07 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,07 cada fecha |
| **Aporte adicional** | **4,87** | **8,19** |
| **Total aportado** | **14,87** | **18,19** |
| Cobro neto de refinanciación | 2,85 · 30/09/2028 | 2,45 · 30/03/2029 |
| Cobro de operación | 1,43 · 30/12/2028 | 0,55 · 30/06/2029 |
| Cobro neto de venta | 14,82 · 30/12/2028 | 3,81 · 30/06/2029 |
| **Total cobrado** | **19,10** | **6,80** |
| **Sin recuperar al cierre** | **0,00** | **11,39** |

Los totales se calculan antes de redondear. Frente al caso de crecimiento cero, el cobro por venta sube USD 0,60 en Base y baja USD 0,12 en Downside. El criterio sintético de múltiplo de equity da **FAIL simulado** para el expediente completo. El dictamen real queda **PENDING**.

## Tasas sintéticas y efecto en el NOI del proyecto

| Partida | Base | Downside |
|---|---:|---:|
| C75 · Crecimiento anual de rentas | +3,00 % | −0,50 % |
| C76 · Crecimiento anual de gastos | +2,00 % | +3,00 % |
| Fecha base de estabilización | 01/01/2028 | 01/07/2028 |
| NOI operativo · primeros 12 meses | USD 402.439,10 | USD 228.710,17 |
| NOI anual bancario | USD 418.133,44 | USD 234.530,11 |
| NOI anual de valoración para refi | USD 440.405,68 | USD 252.238,85 |
| NOI de los 12 meses posteriores a la venta | USD 443.698,17 | USD 251.440,07 |
| Cambio del NOI de salida frente a crecimiento cero | +USD 13.169,95 | −USD 3.195,09 |
| Capacidad para préstamo solicitado de USD 1.400.000 | USD 3.013.302,02 · LTV | USD 1.409.923,69 · DSCR |
| Precio bruto de venta | USD 5.070.836,20 | USD 2.394.667,37 |

El piloto aplica factores anuales efectivos `(1 + tasa) ^ aniversarios cumplidos` desde la estabilización. Los doce meses de operación usan valores base. Las ventanas de valoración de refi y del banco empiezan nueve meses después de estabilizarse y combinan tres meses base con nueve ajustados. El NOI de salida toma doce meses ajustados y se utiliza para calcular el precio de venta. El expediente conserva las fechas y los factores de cada mes.

## Cobertura y pendientes

| Requisito y ubicación | Definición aplicada en la prueba | Módulo y evidencia | Pendiente real |
|---|---|---|---|
| `Inputs!A75:F75` · Rent growth | Tasa anual efectiva sobre renta base residencial y renta comercial desde su mes de reconocimiento. C13 conserva su base. La comisión porcentual se recalcula sobre su ingreso elegible. | B04, B13, M2, M6 y M7. Cotejo exacto de renta bruta, pérdidas, renta neta y meses comerciales, incluyendo un inicio de alquiler en una ventana que cruza el aniversario. | Tasa por escenario, fecha base, alcance y escalas por contrato vigentes. |
| `Inputs!A76:F76` · Expense growth | Tasa anual efectiva sobre gasto fijo, controlable con servicios incluidos una sola vez, y seguro. El impuesto se recalcula con el piso comparable documentado y la rama de valoración de C61–C62. Las reservas y la deuda conservan sus términos propios. | B04, B13, M2, M6 y M7. Conciliación exacta de gastos, impuesto, NOI de operación y de salida, límites de préstamo y caja por USD 10. B16 reproduce el expediente. | Tasa y alcance por componente, base fiscal y frecuencia de ajuste vigentes. |

[Planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx) · [F20 en `/cards/11`](current-structure/MiniUW_Contratos_Financieros_Complementarios_D10.json) · [M7-02 y fronteras de período](model-hold-exit-returns.md).

Una celda vacía, una tasa que produce un factor anual no positivo o una convención sin confirmar deja el escenario PENDING. El caso con C75 de −12 % en Downside verifica el bloqueo de la refinanciación por capacidad. Si falta sólo el criterio de inversión o la revisión está desactualizada, se conservan los flujos calculables del expediente con dictamen PENDING. Una tasa de 0 % confirmada reproduce el cálculo con valores base.

## Reproducción en el VPS

El verificador ejecuta doce corridas D154, con ocho casos PENDING, y coteja el expediente con B16. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_growth_D154.py --output /tmp/miniuw-d154
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d154 \
  --current-revision templates/synthetic-workbook-current-revision-D154.json
```
