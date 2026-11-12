# D153 · Costos y reserva de refinanciación en el cierre

## Si invierto USD 10, ¿cuánto aporto y cuándo cobro?

Importes en USD por cada USD 10 iniciales de equity agregado. Los datos y los criterios de estos dos escenarios son sintéticos.

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
| Cobro neto de venta, con las reservas liberadas | 14,22 · 30/12/2028 | 3,93 · 30/06/2029 |
| **Total cobrado** | **18,49** | **6,92** |
| **Sin recuperar al cierre** | **0,00** | **11,27** |

Los totales se calculan antes de redondear. El criterio sintético de múltiplo de equity da **FAIL simulado** en la corrida completa. El dictamen real queda **PENDING**.

## Conciliación de la refinanciación en USD del proyecto

| Partida | Base | Downside |
|---|---:|---:|
| Préstamo desembolsado | 1.400.000 | 1.400.000 |
| Cancelación de deuda de obra | 635.000 | 686.000 |
| C73 · Costo sobre el desembolso | 2,50 % · 35.000 | 3,50 % · 49.000 |
| C74 · Depósito permanente por 26 unidades elegibles | 1.800/unidad · 46.800 | 3.000/unidad · 78.000 |
| **Cobro neto de refinanciación** | **683.200** | **587.000** |
| Reserva permanente liberada al vender | 46.800 | 39.000 |
| Reserva permanente transferida al comprador como caja restringida | 0 | 39.000 |
| Capacidad de refinanciación | 2.945.719,36 · LTV | 1.423.928,91 · DSCR |

## Cobertura y pendientes

| Requisito y ubicación | Definición aplicada en la prueba | Módulo y evidencia | Pendiente real |
|---|---|---|---|
| `Inputs!A73:F73` · Costo de refinanciación | La fracción se aplica al principal bruto del préstamo desembolsado. El inventario declara que este importe cubre los cargos de refinanciación. | B04, B13 y T29. Se reconcilia con el préstamo bruto, la cancelación de obra, el depósito y el cobro neto. Se prueba cero explícito y faltante. | Fracción, base, inventario de cargos y cancelación de deuda documentados. |
| `Inputs!A74:F74` · Reserva permanente | La tasa por unidad se multiplica por las unidades elegibles. La caja queda restringida en una cuenta separada de C60. Al vender se libera la fracción declarada y se transfiere el remanente restringido. | B04, B13, T29, T31 y B16. Se cotejan el depósito, el saldo previo a la venta y su liquidación. Se prueban cambios de unidades y liberación del 0 %, 50 % y 100 %. | Monto por unidad, inventario elegible y reglas de custodia y liquidación vigentes. |

[Planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx) · [F19 en `/cards/10`](current-structure/MiniUW_Contratos_Financieros_Complementarios_D10.json) · [Contrato de refinanciación](model-refinance-contract.md).

Si faltan datos o si el préstamo supera el menor límite entre LTV y DSCR, el escenario queda PENDING y se retiene el cobro afectado. Si el cierre necesita efectivo y falta una fuente de financiación, el modelo conserva el faltante como diagnóstico. La prueba produce un faltante de USD 115.000 y verifica que la corrida retenga la distribución. Un cierre con exactamente USD 0 de cobro sí se concilia. Si falta el criterio de inversión o la revisión está desactualizada, el dictamen queda PENDING con los flujos calculables del expediente.

## Reproducción en el VPS

El verificador ejecuta dieciséis corridas sintéticas con el runtime de OCR de D131, comprueba nueve casos PENDING y reproduce el expediente con B16. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_refinance_costs_D153.py --output /tmp/miniuw-d153
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d153 \
  --current-revision templates/synthetic-workbook-current-revision-D153.json
```
