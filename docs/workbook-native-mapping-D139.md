# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético se aportan USD 10 el 01/01/2027. En Base y Downside se cobra USD 1 el 01/03, USD 2 al refinanciar el 01/04 y USD 1 el 01/06. La venta del 01/07 aporta USD 8,92 en Base y USD 7,02 en Downside. El cobro total es **USD 12,92 en Base** y **USD 11,02 en Downside**. El aporte adicional y el saldo sin recuperar son USD 0.

## Mapeo de la planilla

La matriz cubre los **55 campos** del archivo original, con celda exacta, unidad literal, definición documentada, aplicabilidad y contrato de cálculo o revisión. El original marca 39 campos como requeridos, 12 condicionales y 4 opcionales. Las dos copias del piloto conservan el diseño original. B04 guarda el valor literal y el estado de cada campo, vinculados al hash de la copia y a la confirmación sintética del escenario. [Matriz de 55 campos](current-structure/MiniUW_Mapeo_55_Campos_D139.csv).

El cálculo de capacidad y venta consume cinco celdas. C66 fija el cap de refinanciación, C67 el cap de salida, C68 el costo variable de venta, C71 el LTV máximo y C72 el DSCR mínimo. Las otras 50 celdas se prueban como entradas mapeadas para revisión. Los demás insumos del cálculo vienen de las fuentes complementarias del piloto. Las alternativas de C80 a C82 se guardan como texto.

| Prueba | Resultado |
| --- | --- |
| 55 campos confirmados por escenario y criterios sintéticos completos | Corrida reproducible con los cobros esperados y FAIL simulado por equity/TDC de Downside |
| C12 presente sin confirmación, C8 vacío o C8 con fórmula y caché | PENDING. Se guarda la evidencia de la celda |
| C72 sin confirmar en Downside | PENDING. Se retira el retorno afectado y se conserva Base |
| C16 y C80 vacíos con declaración explícita de no aplicabilidad | La revisión de campos sintéticos continúa |
| C13 requerido declarado no aplicable o confirmación de otra copia | PENDING |
| Falta un criterio de inversión de Downside | PENDING aunque la revisión de los campos esté completa |
| Cambia C67 con confirmación vinculada a la copia nueva | Se recalculan la venta y el retorno de Downside |

Los 55 destinos financieros para el caso real conservan PENDING de confirmación. Para el piloto real hace falta validar las definiciones, unidades, períodos, bases y aplicabilidad de cada campo, los criterios vigentes por escenario y las fuentes del expediente. La decisión real queda PENDING en los diez ensayos.

## Reproducción en el VPS

Usá las versiones de OCR del ensayo [D131](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-workbook-native-mapping-D139.json \
  --plan templates/synthetic-cropped-rotated-set-D138.pdf \
  --workbook templates/synthetic-native-base-D139.xlsx \
  --downside-workbook templates/synthetic-native-downside-D139.xlsx \
  --current-revision templates/synthetic-workbook-current-revision-D139.json \
  --output /tmp/miniuw-D139
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D139 \
  --current-revision templates/synthetic-workbook-current-revision-D139.json
PYTHONPATH=src:tests python3 tools/check_worksheet_native_mapping_D139.py
```
