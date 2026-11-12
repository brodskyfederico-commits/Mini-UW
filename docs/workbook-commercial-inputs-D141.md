# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 30/03/2027 y USD 3,54 adicionales el 30/06/2027 en ambos escenarios. Se redondea cada importe por separado.

| Cobro por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Refinanciación neta · 30/03/2028 | USD 5,72 | USD 5,72 |
| Operación neta de cuota · 30/06/2028 | USD 1,68 | USD 1,03 |
| Venta neta de costos y deuda · 30/06/2028 | USD 16,12 | USD 8,79 |
| **Cobro total** | **USD 23,52** | **USD 15,53** |
| Saldo sin recuperar | USD 0,00 | USD 0,00 |

## C16–C21 y el inicio del alquiler

C16–C18 aportan las tarifas NNN en USD por pie cuadrado al año. La prueba declara 1.200 pies cuadrados de retail, 800 de restaurante y 1.000 de oficina. C19 se aplica sobre la renta comercial bruta reconocida. C20 se aplica sobre la renta comercial posterior a vacancia y se deduce una vez, dentro de la línea neta.

C21 cuenta meses completos desde el TCO sintético del 01/07/2027. Con ocho meses de plazo, Base reconoce renta desde el 01/03/2028. Con catorce meses, Downside comienza el 01/09/2028. La operación usa los doce meses desde julio de 2027, la valoración de refinanciación y el NOI bancario los doce desde abril de 2028, y la salida los doce desde julio de 2028. Los períodos de valoración comienzan en el primer mes completo siguiente a sus respectivos cierres.

| Efecto comercial | Base | Downside |
| --- | ---: | ---: |
| Meses reconocidos en operación | 4 | 0 |
| Renta comercial neta de operación | USD 24.282,00 | USD 0,00 |
| NOI anual de operación | USD 448.047,60 | USD 290.961,00 |
| Meses reconocidos en el NOI de salida | 12 | 10 |
| Renta comercial neta en el NOI de salida | USD 72.846,00 | USD 38.887,50 |
| Aumento del cobro frente a la variante residencial | USD 3,31 | USD 1,71 |

Con C21 de Downside en cero, el cobro sube a USD 16,07 por USD 10. La prueba conserva las fuentes residenciales y la financiación del ensayo D140. Los usos no aplicables requieren declaración explícita y celdas vacías. Un dato o una fuente pendiente bloquea el retorno afectado. Un criterio pendiente conserva el cálculo de caja disponible y deja PENDING el dictamen simulado. La decisión real queda PENDING.

## Reproducción en el VPS

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-commercial-inputs-D141.json \
  --workbook templates/synthetic-commercial-base-D141.xlsx \
  --downside-workbook templates/synthetic-commercial-downside-D141.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D141.json \
  --output /tmp/miniuw-D141
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D141 \
  --current-revision templates/synthetic-workbook-current-revision-D141.json
PYTHONPATH=src:tests python3 tools/check_worksheet_commercial_inputs_D141.py
```
