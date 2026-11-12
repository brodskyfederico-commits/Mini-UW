# D150 · Impuesto inmobiliario, NOI y flujos por USD 10

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
| Cobro neto de venta, incluida la reserva liberada | 13,35 · 30/12/2028 | 5,59 · 30/06/2029 |
| **Total cobrado** | **17,78** | **9,00** |
| **Sin recuperar al cierre** | **0,00** | **9,19** |

Los totales se calculan antes de redondear. El expediente completo da **FAIL simulado** con su criterio de múltiplo de equity. La decisión real queda **PENDING**.

## Impuesto y NOI anuales del proyecto

| Período | Impuesto Base | NOI Base | Impuesto Downside | NOI Downside |
|---|---:|---:|---:|---:|
| Operación | 49.400,00 | 402.439,10 | 45.742,03 | 228.710,17 |
| Banco | 49.400,00 | 408.395,60 | 47.371,95 | 236.859,77 |
| Valoración y salida | 51.663,39 | 430.528,21 | 50.927,03 | 254.635,17 |

El caso declara 26 unidades comparables y un período de doce meses. **C62 × unidades** da el piso comparable del activo. El otro cálculo usa **C61 × tasa anual sobre valor fiscal ÷ tasa de capitalización de la estimación fiscal** como coeficiente `k`. El motor resuelve `NOI = resultado operativo antes de impuesto − max(piso, k × NOI)` con fracciones exactas. En la operación de Base domina el piso. En la operación de Downside domina la estimación fiscal. El impuesto anual se liquida con la caja operativa en el corte del piloto.

## Cobertura de C61–C62

| Requisito y ubicación | Definición sintética | Módulo y evidencia | Pendiente real |
|---|---|---|---|
| `Inputs!A61:F61` · Valor fiscal / valor de mercado | 0,80 en Base y 0,90 en Downside. Tasas anuales sobre valor fiscal de 1,50 % y 2,00 %. Tasas de capitalización fiscales de 10 % y 9 %. | M2-07 y motor de NOI. Se verifica el coeficiente de 0,12 y 0,20, la rama seleccionada y el residual exacto. | Base, unidad de tasa, fuentes y política fiscal aplicable. |
| `Inputs!A62:F62` · Comparable de impuesto por unidad/año | USD 1.900 en Base y USD 1.300 en Downside, normalizados sobre las unidades residenciales de un comparable de alcance total. | M2-07. Se verifican pisos de USD 49.400 y USD 33.800, cero explícito y el cambio de rama al modificar el comparable. | Comparables, conteo, alcance y período. |
| Caja, valoración y deuda | El impuesto devengado se liquida dentro de la operación anual. La valoración y el banco usan su respectivo NOI de doce meses. | M2, M5 y M7. Se verifican los cambios en cobro de operación y venta y el bloqueo por capacidad. | Calendario de pagos, fuentes y límites vigentes. |

Las tasas, los comparables y la regla del máximo son supuestos del piloto. El expediente conserva los localizadores exactos, las fuentes y la ecuación por período. [Planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx) · [F18 en `/cards/9`](current-structure/MiniUW_Contratos_Financieros_Complementarios_D10.json) · [Contrato M2-07](model-operations-contract.md#cierre-algebraico-condicionado-de-impuesto--noi-m2-07).

Si falta un dato fiscal o si el préstamo supera la capacidad, queda PENDING el escenario afectado. Si falta sólo el criterio de inversión o la revisión vigente, el expediente muestra los flujos calculables con dictamen PENDING. La solicitud sintética de USD 1.400.000 entra en ambos escenarios. Una solicitud de USD 1.550.000 deja Downside PENDING por capacidad.

## Reproducción en el VPS

Con el runtime de OCR de D131, el verificador reproduce catorce corridas y audita el expediente. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_property_tax_D150.py --output /tmp/miniuw-d150
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d150 \
  --current-revision templates/synthetic-workbook-current-revision-D150.json
```
