# Si invierto USD 10, ¿cuánto cobro y cuándo?

En este piloto sintético se aportan USD 10 el 30/03/2027 y USD 3,54 adicionales el 30/06/2027 en ambos escenarios. Los cobros se normalizan por el aporte inicial del proyecto. Cada importe se redondea por separado.

| Fecha y concepto | Base | Downside |
| --- | ---: | ---: |
| 30/03/2028, refinanciación neta | USD 5,72 | USD 5,72 |
| 30/06/2028, operación neta de cuota | USD 1,58 | USD 1,03 |
| 30/06/2028, venta neta de costos y deuda | USD 12,92 | USD 7,08 |
| **Cobro total por USD 10 iniciales** | **USD 20,21** | **USD 13,82** |
| Saldo sin recuperar al vender | USD 0,00 | USD 0,00 |

## De la planilla al NOI

| Celdas | Vínculo probado |
| --- | --- |
| C7 | Selecciona USD por unidad al mes o USD por pie cuadrado rentable al mes |
| C8–C11 | Tarifas para estudios, unidades de uno, dos y tres dormitorios. Se vinculan al inventario explícito de unidades y superficies |
| C12 | Referencia de comparables. Se coteja con el registro y la fecha de la fuente sintética |
| C13 | Otros ingresos devengados. Multiplica la tarifa mensual por 20 unidades elegibles y 12 meses en esta prueba |
| C14 | Pérdida de renta residencial por vacancia y crédito |
| C15 | Concesiones de renta. La corrida principal usa la renta bruta como base explícita |

| Importe anual del proyecto | Base | Downside |
| --- | ---: | ---: |
| Renta bruta | USD 513.600,00 | USD 453.840,00 |
| Renta efectiva | USD 477.648,00 | USD 340.380,00 |
| Otros ingresos | USD 8.400,00 | USD 6.000,00 |
| **NOI** | **USD 423.765,60** | **USD 290.961,00** |

La comparación mantiene el programa de 26 unidades, el presupuesto de obra, los gastos, el cap de salida del 9 % y el préstamo solicitado de USD 1,4 millones. La administración se aplica a la renta residencial efectiva. Para dimensionar deuda, el NOI bancario agrega cinco puntos porcentuales de vacancia conforme al supuesto sintético de la corrida. La valoración, la caja operativa y el NOI de salida usan los mismos términos de renta en sus períodos declarados. El cobro de refinanciación coincide cuando la solicitud fija cabe en la capacidad de ambos escenarios.

Al cambiar únicamente C14 de Downside del 20 % al 5 %, el NOI pasa de USD 290.961,00 a USD 355.633,20 y el cobro sube de **USD 13,82 a USD 16,93** por USD 10 iniciales. También se prueban la equivalencia de las tarifas por unidad y por pie cuadrado, C13 en cero y C15 aplicado después de vacancia.

Si falta confirmar una celda requerida o su fuente, el escenario afectado queda PENDING. Si falta un criterio, se conservan los cobros calculados y queda PENDING el dictamen. Una solicitud por encima de la capacidad conserva el NOI calculado y deja PENDING el retorno dependiente de la refinanciación. La simulación comprueba un criterio sintético de múltiplo de equity por escenario. La decisión real sigue PENDING.

## Reproducción en el VPS

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-rental-inputs-D140.json \
  --workbook templates/synthetic-rental-base-D140.xlsx \
  --downside-workbook templates/synthetic-rental-downside-D140.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D140.json \
  --output /tmp/miniuw-D140
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D140 \
  --current-revision templates/synthetic-workbook-current-revision-D140.json
PYTHONPATH=src:tests python3 tools/check_worksheet_rental_inputs_D140.py
```
