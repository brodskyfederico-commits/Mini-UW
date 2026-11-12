# D152 · Deuda permanente, capacidad y flujos por USD 10

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
| Cobro de operación | 1,43 · 30/12/2028 | 0,55 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 14,02 · 30/12/2028 | 3,76 · 30/06/2029 |
| **Total cobrado** | **18,52** | **7,17** |
| **Sin recuperar al cierre** | **0,00** | **11,02** |

Los totales se calculan antes de redondear. El expediente completo da **FAIL simulado** con el criterio sintético de múltiplo de equity. El dictamen real queda **PENDING**.

## Capacidad y servicio de la deuda del proyecto

| Partida | Base | Downside |
|---|---:|---:|
| C69 · Tasa nominal anual | 5,00 % | 6,50 % |
| C70 · Años de amortización | 20 | 11 |
| Cuota trimestral sobre el principal solicitado | USD 27.785,13 | USD 44.784,50 |
| Servicio anual equivalente para capacidad | USD 111.140,53 | USD 179.137,98 |
| C71 · LTV máximo | 65 % | 65 % |
| Límite LTV | USD 2.945.719,36 | USD 1.439.242,25 |
| C72 · DSCR mínimo | 1,25× | 1,30× |
| Límite DSCR | USD 4.115.537,81 | USD 1.423.928,91 |
| **Capacidad y límite vinculante** | **USD 2.945.719,36 · LTV** | **USD 1.423.928,91 · DSCR** |
| Principal solicitado | USD 1.400.000,00 | USD 1.400.000,00 |
| Saldo cancelado al vender después de pagar la primera cuota | USD 1.389.714,87 | USD 1.377.965,50 |

## Cobertura de C69–C72

| Requisito y ubicación | Definición sintética | Módulo y evidencia | Pendiente real |
|---|---|---|---|
| `Inputs!A69:F69` · Tasa permanente | Tasa fija nominal anual convertible cuatro veces al año. El caso declara pagos trimestrales vencidos. | M6 y T10. Se concilian tasa trimestral, interés, capital y saldo, incluido cero explícito. | Tipo de tasa, frecuencia y fuente bancaria vigentes. |
| `Inputs!A70:F70` · Años de amortización | Años enteros × cuatro pagos por año. El plazo a vencimiento se declara por separado en ocho pagos para el ejemplo principal. | M6, M7, T10 y T31. La primera cuota se paga al cierre operativo en la fecha de venta. El saldo posterior se paga en el cierre de venta. Se comprueba que cambiar el vencimiento recalcule el calendario. | Frecuencia, vencimiento y fechas contractuales. |
| `Inputs!A71:F71` · LTV máximo | Fracción aplicada al valor de refinanciación calculado desde C66. | M6 y T35. Se verifica el cambio de restricción activa y que la igualdad exacta a capacidad sea admisible. | Límite, base de valor e inventario de restricciones aplicables. |
| `Inputs!A72:F72` · DSCR mínimo | El NOI bancario se divide por el DSCR mínimo y el servicio anual equivalente por dólar de préstamo. | M6 y T35. Se coteja el límite con el LTV. El servicio equivalente se usa para capacidad y la cuota fechada se usa en caja. | DSCR, período de NOI y regla de capacidad vigentes. |

Las tasas, la convención trimestral, el vencimiento de dos años y el inventario de límites son supuestos de prueba. Los flujos del cierre incorporan una cuota regular y el saldo de principal pendiente tras esa cuota. El préstamo solicitado se conserva como entrada. [Planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx) · [F07 en `/cards/6`](current-structure/MiniUW_Contratos_Financieros_Prioritarios_D09.json) · [Contrato de refinanciación](model-refinance-contract.md).

Un término sin confirmar, una convención incompatible o una solicitud superior al menor límite deja el escenario PENDING y retiene el cobro proyectado. Las pruebas bloquean Downside al bajar el LTV máximo a 63 % o subir el DSCR mínimo a 1,34×. Si falta sólo el criterio de inversión o la revisión vigente, los flujos calculables quedan condicionados al expediente con dictamen PENDING.

## Reproducción en el VPS

Con el runtime de OCR de D131, el verificador reproduce diecisiete corridas y audita el expediente. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_permanent_loan_D152.py --output /tmp/miniuw-d152
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d152 \
  --current-revision templates/synthetic-workbook-current-revision-D152.json
```
