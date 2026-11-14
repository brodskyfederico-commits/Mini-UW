# Si invierto USD 10, ¿cuánto cobro y cuándo?

El caso principal del piloto PRELIMINAR reproduce el cálculo D205 desde planillas y respaldos PDF sintéticos. Los importes son de equity agregado y los totales se calculan antes de redondear. [Informe con todos los aportes y cobros por fecha](review/MiniUW_Preliminar_Respaldo_PDF_D206.pdf)

| Escenario | Aporte adicional total | Refi al 30/12/2027 | Cobro trimestral durante 2028 | Venta neta al 30/12/2028 | Total cobrado | Sin recuperar |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Base | USD 6,22 | Cobra USD 2,65 | USD 0,63 | USD 23,98 | USD 29,14 | USD 0,00 |
| Downside | USD 8,01 | Aporta USD 0,17, incluido en el adicional | USD 0,39 | USD 7,52 | USD 9,06 | USD 8,95 |

## Qué lee y coteja el piloto

Cada proyecto y escenario tiene una planilla Inputs y un PDF con nueve páginas rotuladas. Las hojas A101 y A601 cotejan el conteo de unidades del plano y su cuadro. La cotización de obra se coteja con las partidas de la planilla. Las páginas bancarias identifican deuda de obra y deuda permanente por separado, con sus términos y los desembolsos de obra. La página fiscal alimenta M2 con padrones, tasaciones y millage escolar y no escolar. Las otras páginas documentan rentas y gastos, calendario y salida.

El perfil lee tablas de texto diseñadas para este ensayo. Las citas registran PDF, página y línea del campo leído. El ensayo usa el conteo declarado en las hojas del plano. La medición de superficies, el reconocimiento de trazos y la lectura de escaneos quedan fuera de este perfil. Cada bloque estructurado se reconstruye del texto de las páginas. El inventario JSON fija identidad, calendario, huellas y comparabilidad de los dos casos.

Las 36 páginas de respaldo concilian con el cálculo D205. Se conservan el orden del ranking, los aportes y los cobros exactos por fecha. La primera posición corresponde al caso principal, con múltiplo Downside de 0,5031×, seguido del comparador con 0,4204×. Una revisión de prueba del millage no escolar reduce el NOI bancario de Downside, sus cobros y su múltiplo en el ranking.

Se probaron hojas y respaldos faltantes, un duplicado bancario, diferencias de unidades y DSCR, un valor fiscal ausente y un PDF con huella distinta. En cada prueba el caso afectado queda PENDING y sale del ranking. Base y el otro proyecto conservan sus flujos verificados. La auditoría reproduce el paquete desde sus PDF y XLSX archivados. El dictamen formal y el retorno personal quedan PENDING.

## Reproducción

```bash
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py run templates/preliminary-pilot-D206 /tmp/miniuw-pdf-D206
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py audit /tmp/miniuw-pdf-D206
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_pdf_D206.py
```

[Inventario de fuentes](../templates/preliminary-pilot-D206/pilot.json) · [Pruebas y resultados del VPS](review/MiniUW_Verificacion_D206.json)
