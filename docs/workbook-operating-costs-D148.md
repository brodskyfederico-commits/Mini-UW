# D148 · Gastos operativos, aportes y cobros por USD 10

## Si invierto USD 10, ¿cuánto aporto y cuándo cobro?

Los importes de la tabla son USD por cada USD 10 iniciales de equity agregado del piloto sintético.

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
| Cobro de operación | 1,65 · 30/12/2028 | 0,91 · 30/06/2029 |
| Cobro neto de venta | 14,96 · 30/12/2028 | 7,19 · 30/06/2029 |
| **Total cobrado** | **19,68** | **10,96** |
| **Sin recuperar al cierre** | **0,00** | **7,23** |

Los totales se calculan antes de redondear. El NOI operativo anual del proyecto queda en USD 439.839,10 en Base y USD 262.452,20 en Downside. Frente a D147, el cobro por USD 10 baja USD 0,52 y USD 1,15 respectivamente, calculado antes de redondear. La solicitud sintética de refinanciación de USD 1.400.000 queda dentro de la capacidad en ambos escenarios. El criterio de múltiplo de equity da **FAIL simulado** en el expediente completo. La decisión real queda **PENDING**.

## Cobertura de C57–C59

Las ubicaciones corresponden a la [planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx). Las definiciones del piloto siguen las condiciones de alcance de F03 y F04. [Contratos en `/cards/2` y `/cards/3`](current-structure/MiniUW_Contratos_Financieros_Prioritarios_D09.json).

| Celda y ubicación | Definición en el piloto | Módulo y cálculo | Evidencia y pendiente |
|---|---|---|---|
| C57 · `Inputs!A57:F57` | Tarifa anual de USD 1.300 en Base y USD 1.600 en Downside por cada una de las 26 unidades declaradas. El total incluye los servicios C25–C28 | M2. Desglosa el total en servicios y resto controlable | USD 33.800 y USD 41.600 anuales. La prueba de cambio de C25 conserva el total dentro del presupuesto. Alcance real pendiente. |
| C58 · `Inputs!A58:F58` | 5 % en Base y 6 % en Downside del EGI residencial elegible. Incluye renta residencial efectiva y otros ingresos residenciales C13 | M2. Recalcula la base en cada período según la vacancia y las concesiones | Administración anual operativa de USD 24.302,40 y USD 20.782,80. La prueba de cero explícito elimina ambas partidas de administración. Composición real del EGI pendiente. |
| C59 · `Inputs!A59:F59` | USD 300 y USD 550 anuales por unidad asegurada, con inventario de 26 unidades por escenario | M2. Gasto anual sintético íntegramente pagado dentro de la ventana operativa | USD 7.800 y USD 14.300. La falta de inventario bloquea el cálculo. Póliza, alcance y pagos reales pendientes. |

En este perfil, C57 absorbe el total controlable. Si la suma de C25–C28 supera ese total, el escenario queda PENDING. La comisión de C58 excluye la renta comercial. El caso declara USD 10.800 de gastos fijos ajenos a esas partidas por período, más el impuesto separado. C60 queda pendiente de vinculación a una política de reserva y a su tratamiento en el cierre.

El gasto conciliado llega al NOI operativo, bancario, de valoración y de salida. Si falta una tasa o una base, queda PENDING el escenario afectado. Si los gastos reducen la capacidad por debajo del préstamo solicitado, se bloquea su flujo de refinanciación. Si falta sólo el criterio o la revisión vigente, se preservan los flujos calculables con dictamen PENDING.

## Reproducción en el VPS

Con el runtime de OCR de D131, la prueba reproduce doce corridas integradas y audita el expediente. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_operating_costs_D148.py --output /tmp/miniuw-d148
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d148 \
  --current-revision templates/synthetic-workbook-current-revision-D148.json
```
