# D144 · Presupuesto de obra y aportes por USD 10

## Si invierto USD 10, ¿cuánto aporto y cuándo cobro?

Los importes de esta tabla son USD por cada USD 10 iniciales de equity agregado del piloto sintético.

| Concepto | Fecha | Base | Downside |
|---|---|---:|---:|
| Aporte inicial | 30/03/2027 | 10,00 | 10,00 |
| Aporte adicional | 30/06/2027 | 6,31 | 9,22 |
| Aporte adicional | 30/09/2027 | 0,78 | 0,82 |
| **Total aportado** | | **17,09** | **20,04** |
| Cobro de refinanciación neta | 30/03/2028 | 5,72 | 5,72 |
| Cobro de operación | 30/06/2028 | 1,62 | 0,94 |
| Cobro de venta neta | 30/06/2028 | 15,43 | 7,90 |
| **Total cobrado** | | **22,76** | **14,55** |
| **Capital sin recuperar al cierre** | 30/06/2028 | **0,00** | **5,49** |

Los totales se calculan antes de redondear cada flujo. El presupuesto del proyecto para las partidas de este piloto es USD 4.100.700 en Base y USD 4.809.792 en Downside. El cambio de costos afecta los aportes y el múltiplo de equity. El caso conserva las condiciones de operación, refinanciación y venta del piloto D143. El dictamen real queda **PENDING**. El expediente vigente de prueba da **FAIL simulado** con la regla sintética de múltiplo de equity heredada.

## Cobertura de C37–C42

La ubicación de cada fila corresponde a la [planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx). Los [contratos complementarios](current-structure/MiniUW_Contratos_Financieros_Complementarios_D10.json) fijan los requisitos de evidencia en F14 (`/cards/5`), F15 (`/cards/6`) y F16 (`/cards/7`). Los montos de la tabla son USD del proyecto.

| Celda y ubicación | Definición en el perfil sintético | Módulo | Base / Downside | Evidencia y pendiente |
|---|---|---|---:|---|
| C37 · `Inputs!A37:F37` · F14 | Tarifa por plaza × 24 plazas con fuente explícita | M3 presupuesto, M5 aportes | 120.000 / 144.000 | Variación de tarifa verificada. Conteo y alcance reales pendientes. |
| C38 · `Inputs!A38:F38` · F14 | Monto de obras del sitio separado de la cotización vertical | M3, M5 | 80.000 / 100.000 | Variación de monto verificada. Alcance real pendiente. |
| C39 · `Inputs!A39:F39` · F15 | Fracción sobre obra vertical, parking y sitio. Reserva fondeada en el piloto | M3, M5 | 127.000 / 274.400 | Variación de fracción y base verificada. Política real de reserva pendiente. |
| C40 · `Inputs!A40:F40` · F15 | Fracción del hard con reserva. Incluye honorarios de desarrollo. TI/LC es una partida separada | M3, M4 calendario, M5 | 266.700 / 392.392 | Variación de fracción verificada. Base y exclusiones reales pendientes. |
| C41 · `Inputs!A41:F41` · F15 | Tarifa de mejoras y comisiones de alquiler × 3.000 pies² comerciales elegibles | M3, M5 | 45.000 / 60.000 | Variación de tarifa, aplicabilidad y ausencia verificadas. Área y alcance reales pendientes. |
| C42 · `Inputs!A42:F42` · F16 | Fracción de C40 fondeada en meses 1–3 | M4, M5 | 80.010 / 196.196 | Variantes 0 % y 100 % conservan el total y mueven la fecha del aporte. Curva real pendiente. |

Para esta prueba se declara que el hard, la reserva y TI/LC se fondean el 30/06/2027 junto al tramo adelantado de soft costs. El saldo de soft se fondea el 30/09/2027. La reserva representa fondos apartados en el presupuesto. El caso supone que permanecen comprometidos hasta el cierre. El libro cubre primero los usos con el aporte inicial y atribuye el faltante de cada fecha a capital adicional. Este calendario trimestral viene de la declaración de prueba.

Los datos y criterios sin confirmar producen **PENDING**. Si falta una partida aplicable, su alcance, el conteo de plazas o el calendario, se bloquea el cálculo de aportes del escenario afectado. Si sólo falta un criterio de inversión, el expediente conserva los cálculos sintéticos y retiene el dictamen. Una revisión anterior del expediente también queda PENDING.

## Reproducción

En el VPS, con las dependencias del repositorio y desde su raíz, el verificador ejecuta 17 corridas de planilla, audita el expediente inicial y genera el PDF de una página. También comprueba la no aplicabilidad de C41 con un inventario comercial vacío confirmado.

```bash
PYTHONPATH=src:tests python3 tools/check_worksheet_construction_budget_D144.py --output /tmp/miniuw-d144
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d144 \
  --current-revision templates/synthetic-workbook-current-revision-D144.json
```
