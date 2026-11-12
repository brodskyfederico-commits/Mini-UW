# D145 · Obra, estabilización y flujos por USD 10

## Si invierto USD 10, ¿cuánto aporto y cuándo cobro?

Los importes son USD por cada USD 10 iniciales de equity agregado en el piloto sintético.

| Flujo | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00 | 10,00 |
| Aporte de obra · 30/06/2027 | 0,30 | 2,11 |
| Aporte al fin de obra | 6,79 · 30/09/2027 | 7,93 · 30/12/2027 |
| Aporte para estabilización, fondeado al fin de obra | 0,12 · 30/09/2027 | 0,50 · 30/12/2027 |
| **Total aportado** | **17,21** | **20,54** |
| Cobro neto de refinanciación | 5,72 · 30/09/2028 | 5,72 · 30/03/2029 |
| Cobro de operación | 1,69 · 30/12/2028 | 1,01 · 30/06/2029 |
| Cobro neto de venta | 15,43 · 30/12/2028 | 8,24 · 30/06/2029 |
| **Total cobrado** | **22,84** | **14,96** |
| **Sin recuperar al cierre** | **0,00** | **5,58** |

Los totales se calculan antes de redondear. El escenario Base llega a la estabilización el 01/01/2028, tres meses después del TCO declarado del 01/10/2027. Downside llega a la estabilización el 01/07/2028, seis meses después de su TCO del 01/01/2028. El criterio de múltiplo de equity produce **FAIL simulado** en el expediente completo. El dictamen real queda **PENDING**.

## Cobertura y supuestos del calendario

Las celdas están en la [planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx). El contrato F16 en `/cards/7` vincula las duraciones con el origen, los hitos y la convención documentados. Las relaciones M4-01 a M4-06 describen las dependencias de calendario y financiación. [Contrato F16](current-structure/MiniUW_Contratos_Financieros_Complementarios_D10.json) · [Relaciones de calendario y financiación](model-budget-schedule.md#m4-devengo-desembolso-e-hitos).

| Celda y ubicación | Definición en el piloto | Módulo y cálculo | Evidencia y pendiente |
|---|---|---|---|
| C46 · `Inputs!A46:F46` | Meses desde el inicio de obra declarado hasta fin de obra. Base 6, Downside 9 | M4 fecha de terminación. M5 fecha del aporte restante | Reducir C46 de 9 a 3 meses adelanta ese aporte. Si la obra termina después del TCO declarado, la corrida queda PENDING. Inicio, distribución de pagos y calendario reales pendientes. |
| C47 · `Inputs!A47:F47` | Meses desde TCO confirmado hasta estabilización. Base 3, Downside 6 | M4 estabilización. M2 NOI. M5 reserva de caja, fecha de refi, capacidad y deuda. M6 fecha de venta y retorno | Con 0 meses explícitos se usa el TCO como inicio estabilizado, se elimina el aporte para estabilización y se recalculan fechas y cobros. TCO, reglas y caja real pendientes. |

El perfil usa puntos de caja trimestrales el día 30 y duraciones entre 0 y 36 meses en múltiplos de tres. C46 requiere al menos tres meses. El inicio de obra se declara en la fecha de compra. El TCO es un dato independiente de cada escenario. Las duraciones fuera de esta convención quedan PENDING.

El primer corte incluye el 50 % del hard directo y el tramo de costos indirectos de C42. Al fin de obra se aporta el saldo, junto con el fondeo de una necesidad de caja durante el lease-up de USD 10.000 al mes en Base y USD 20.000 al mes en Downside. Esos importes sintéticos representan el faltante neto de tenencia y operación de esa etapa. El caso declara caja neta cero en los intervalos previos fuera de las partidas programadas. El presupuesto de obra de D144 se conserva y el fondeo del lease-up se identifica como un aporte separado.

La prueba fija la refinanciación nueve meses después del corte de estabilización y la venta doce meses después de ese mismo corte. La operación estabilizada se modela durante doce meses y se liquida en el corte de venta. El mismo día se paga la primera cuota de la deuda y se cancela el saldo con el cierre. El inicio comercial sigue usando C21 desde el TCO. Los cortes son una convención sintética del piloto.

Si falta una duración, un hito o una base de caja, el escenario afectado queda PENDING. El mismo bloqueo se aplica si el préstamo supera la capacidad. Si falta el criterio de inversión, los flujos trazables siguen disponibles con dictamen PENDING. Una revisión anterior también queda PENDING.

## Reproducción en el VPS

Desde la raíz del repositorio y con las dependencias instaladas, el verificador reproduce trece corridas y genera el PDF de una página. La auditoría vuelve a calcular el expediente con los archivos y la revisión suministrados.

```bash
PYTHONPATH=src:tests python3 tools/check_worksheet_project_calendar_D145.py --output /tmp/miniuw-d145
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d145 \
  --current-revision templates/synthetic-workbook-current-revision-D145.json
```
