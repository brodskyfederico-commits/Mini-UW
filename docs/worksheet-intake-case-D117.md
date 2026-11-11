# Si invierto USD 10, ¿cuánto cobro cuando se corrige la planilla?

D117 conecta el checklist de ingreso con la corrida sintética de refinanciación y venta. El comando recibe una planilla XLSX, coteja sus cinco celdas y sus metadatos contra el caso D117, y usa esos mismos bytes si los controles de ingreso pasan. El expediente guarda el XLSX original, el checklist, los resultados y un PDF de una página. La auditoría reproduce todo desde esas fuentes.

| Copia sintética | Cambio en la planilla | Resultado |
| --- | --- | --- |
| Inicial | C68 vacía | PENDING. El checklist señala el costo de venta faltante. |
| Corregida | C68 pasa de vacía a 0,05 | Se ejecuta la corrida con costo variable del 5 %. |
| Alternativa de prueba | Sólo C68 pasa de 0,05 a 0 literal | El costo total de venta baja de USD 30 a USD 10 a nivel proyecto. El neto de venta sube USD 0,20 por USD 10 iniciales. |
| Corrección parcial | Se completa C68 y C72 sigue vacía | PENDING. El checklist señala el DSCR mínimo pendiente y no emite cobros ni resultados de venta. |

La corrección de C68 conserva el precio bruto, la capacidad calculada y los flujos anteriores al cierre. Cambian el costo de venta, el cobro neto, el retorno por USD 10 y el precio mínimo de recuperación. Los importes proceden del caso de prueba D63. La decisión de inversión permanece PENDING.

## Reproducción

```bash
PYTHONPATH=src python3 tools/check_worksheet_intake_case_D117.py --output /tmp/miniuw-D117
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D117
```

El verificador guarda un ejemplo completo con el XLSX corregido. Para una copia sintética compatible, ejecutá la corrida con un directorio nuevo.

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-intake-case-D117.json --workbook planilla-sintetica.xlsx --output /tmp/miniuw-D117-otra-copia
```

El expediente anterior se conserva y la auditoría rechaza un XLSX sustituido dentro de un expediente. La prueba abarca las celdas de refinanciación y venta del perfil D116. La planilla real de métricas de Lorena queda pendiente de pilotaje.
