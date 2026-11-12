# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 30/03/2027 y USD 3,54 adicionales el 30/06/2027 en ambos escenarios. Se redondea cada importe por separado.

| Cobro por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Refinanciación neta · 30/03/2028 | USD 5,72 | USD 5,72 |
| Operación neta de cuota · 30/06/2028 | USD 1,62 | USD 0,94 |
| Venta neta de costos y deuda · 30/06/2028 | USD 15,43 | USD 7,90 |
| **Cobro total** | **USD 22,76** | **USD 14,55** |
| Saldo sin recuperar | USD 0,00 | USD 0,00 |

## Gasto de servicios por tipo de unidad

Para este piloto, el propietario paga el gasto adicional y el presupuesto operativo de D141 lo excluye. Cada tarifa mensual se multiplica por las unidades elegibles confirmadas de su tipo y por los doce meses de cada período. El gasto reduce el NOI operativo, bancario, de valoración y de salida. La renta y los demás supuestos se mantienen para medir el efecto. La interpretación de asignaciones reguladas y su validación con fuentes reales quedan PENDING.

| Celda | Tipo | Unidades elegibles | Base mensual por unidad | Downside mensual por unidad |
| --- | --- | ---: | ---: | ---: |
| C25 | Estudio | 4 | USD 35 | USD 45 |
| C26 | 1 dormitorio | 12 | USD 45 | USD 60 |
| C27 | 2 dormitorios | 8 | USD 60 | USD 75 |
| C28 | 3 dormitorios | 2 | USD 75 | USD 95 |

| Efecto del gasto | Base | Downside |
| --- | ---: | ---: |
| Gasto anual del proyecto | USD 15.720 | USD 20.280 |
| NOI operativo de referencia | USD 448.047,60 | USD 290.961,00 |
| NOI operativo con el gasto | USD 432.327,60 | USD 270.681,00 |
| Disminución del cobro total por USD 10 | USD 0,76 | USD 0,98 |

El préstamo fijo de USD 1,4 millones sigue dentro de la capacidad de ambos escenarios en el caso principal. Se prueba C26 de Downside de USD 60 a USD 70 y se verifica el aumento anual de USD 1.440. El cero confirmado y la no aplicabilidad documentada conservan su significado. Una tarifa, población elegible o alcance del gasto sin confirmar deja PENDING el retorno afectado. Con un criterio faltante, quedan disponibles los cobros calculados y queda PENDING el dictamen. La decisión real queda PENDING.

## Reproducción en el VPS

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-utility-inputs-D142.json \
  --workbook templates/synthetic-utilities-base-D142.xlsx \
  --downside-workbook templates/synthetic-utilities-downside-D142.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D142.json \
  --output /tmp/miniuw-D142
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D142 \
  --current-revision templates/synthetic-workbook-current-revision-D142.json
PYTHONPATH=src:tests python3 tools/check_worksheet_utility_inputs_D142.py
```
