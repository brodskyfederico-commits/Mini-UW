# Piloto sintético con diez métricas de inversión

La corrida D121 recibe las planillas Base y Downside y un caso sintético con la revisión de criterios. El expediente conserva las planillas, el caso, las comparaciones y un PDF de una página con el retorno por USD 10 y la simulación. El comando de auditoría reproduce el resultado desde esos archivos.

## Métricas y fuentes

| Métrica | Unidad | Fuente en este piloto |
| --- | --- | --- |
| Múltiplo de equity | Múltiplo | Cobros totales sobre aportes totales del libro de caja |
| Equity recuperado al refinanciar | Fracción | Distribución neta al refinanciar sobre capital inicial del libro |
| Aporte al refinanciar | USD | Aporte al refinanciar en el libro de caja del proyecto |
| Yield on Cost (YoC) | Fracción | Referencia declarada de NOI estabilizado sobre costo total (TDC) |
| Spread | Puntos básicos | Referencia declarada de YoC menos cap de referencia |
| Ocupación de equilibrio | Fracción | Referencia declarada de ocupación económica para cubrir el servicio de deuda |
| Cash-on-cash posrefinanciación | Fracción | Referencia declarada de caja anual posrefinanciación sobre la base de equity del caso |
| Equity / TDC | Fracción | Referencia declarada de equity aplicado sobre TDC |
| TIR anual | Fracción | Referencia sintética declarada con seis decimales |
| Asking / precio soportado | Múltiplo | Referencia declarada de precio pedido sobre precio soportado |

Las tres primeras métricas se calculan en la corrida. Las otras siete llegan como valores sintéticos declarados en el caso JSON, cada uno con definición, unidad, período y fuente. Se vinculan al SHA-256 de la planilla de su escenario. Las reglas identifican la misma definición, unidad y período. Las referencias y umbrales prueban el circuito de cotejo. El mapeo de esas siete métricas a la planilla real y las reglas aplicables requieren los datos y definiciones vigentes de Lorena.

## Resultado por USD 10 iniciales

En ambos escenarios se aportan USD 10 el 01/01/2027. Se cobra USD 1 el 01/03 por operación, USD 2 el 01/04 por refinanciación y USD 1 el 01/06 por operación. El último cobro llega con la venta el 01/07.

| Escenario | Venta neta por USD 10 | Cobro total | Aporte extra | Saldo sin recuperar |
| --- | ---: | ---: | ---: | ---: |
| Base | USD 8,92 | USD 12,92 | USD 0,00 | USD 0,00 |
| Downside | USD 7,02 | USD 11,02 | USD 0,00 | USD 0,00 |

- **PASS simulado** con 20 comparaciones completas, diez por escenario.
- **FAIL simulado** al elevar el YoC mínimo de Downside de 7,5 % a 9 % frente a su valor sintético de 8 %. Se conservan ambos retornos.
- **PENDING** al retirar el valor de TIR y la regla de cash-on-cash de Downside, incluso con la falla de YoC ya observada. Se conservan ambos retornos. Una referencia de otra revisión de la planilla o con unidad incompatible también deja pendiente su métrica.

Si faltan insumos para calcular la caja o el préstamo supera la capacidad, el retorno del escenario también queda PENDING. La decisión de inversión real permanece **PENDING** en los tres ensayos.

## Reproducción desde el repositorio

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-screening-pilot-D121.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --output /tmp/miniuw-D121
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D121
PYTHONPATH=src python3 tools/check_worksheet_reference_metrics_D121.py
```
