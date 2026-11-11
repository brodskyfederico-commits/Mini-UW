# Piloto sintético desde la planilla hasta la simulación y el retorno por USD 10

El comando común recibe dos copias del formato Inputs, una para Base y otra para Downside, y un caso que identifica por hash ambas planillas. El caso declara la revisión de criterios, sus operadores y umbrales, y la regla de agregación. El expediente conserva esos archivos, los checklists, los flujos por fecha, las comparaciones y un PDF de una página. La auditoría vuelve a calcularlo desde las fuentes.

## Caso reproducible

En las dos variantes se aportan USD 10 el 01/01/2027. Se cobra USD 1 de operación el 01/03, USD 2 de refinanciación el 01/04 y USD 1 de operación el 01/06. El único cambio de la planilla Downside es C67, el cap de salida. Cambia el cobro del 01/07/2027.

| Escenario | Cobro neto de venta | Cobro total por USD 10 | Aporte extra | Saldo sin recuperar |
| --- | ---: | ---: | ---: | ---: |
| Base | USD 8,92 | USD 12,92 | USD 0,00 | USD 0,00 |
| Downside | USD 7,02 | USD 11,02 | USD 0,00 | USD 0,00 |

El perfil de ensayo deriva tres métricas del libro verificado. Múltiplo de equity, equity recuperado al refinanciar y aporte para refinanciar. Las reglas se declaran por escenario en el archivo del caso. En el caso incluido, las tres métricas cumplen las reglas sintéticas en Base y Downside. Una revisión con un umbral de múltiplo Downside más exigente produce FAIL simulado con los mismos flujos.

La simulación queda **PENDING** si falta una planilla, un dato o una regla requeridos, si la fuente difiere del hash declarado o si una métrica cae en una banda intermedia. Una falla conocida conserva su evidencia y la simulación global sigue pendiente si falta otra regla requerida. Si falla la capacidad de un escenario, ese escenario retira el retorno y sus métricas. La corrida conserva la evidencia de los escenarios disponibles.

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-screening-pilot-D120.json \
  --workbook templates/synthetic-pilot-base-D120.xlsx \
  --downside-workbook templates/synthetic-pilot-downside-D120.xlsx \
  --output /tmp/miniuw-D120
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D120
PYTHONPATH=src python3 tools/check_worksheet_screening_pilot_D120.py
```

La simulación cubre el perfil sintético de refinanciación y venta de D118. La planilla real, las reglas de Lorena, el mapeo de los demás campos aplicables y el cotejo independiente del caso real siguen pendientes. La decisión de inversión permanece **PENDING**.
