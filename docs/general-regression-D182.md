# Si invierto USD 10, ¿cuánto cobro y cuándo?

En la corrida sintética D181, Base aporta USD 4,87 adicionales y cobra USD 18,06 hasta el 30/12/2028. Downside aporta USD 8,19 adicionales y cobra USD 6,08 hasta el 30/06/2029. Quedan USD 12,11 sin recuperar en Downside. El [informe de una página](review/MiniUW_Informe_USD10_D181.pdf) desglosa cada aporte y los cobros de refinanciación, operación y venta.

La batería completa de D181 pasó en el VPS con **1.619 pruebas aprobadas**, cero fallos, cero errores y cero omitidas. Pasaron diez comprobaciones de integración. La ampliación de la prueba conserva el código de cálculo y el PDF publicado.

## Qué se verifica cuando falta algo

| Variante sintética | Dictamen y PDF |
| --- | --- |
| C72 vacío en la planilla de Downside | La entrada de DSCR queda PENDING con valor nulo. El PDF marca la caja de Downside PENDING y omite sus aportes y cobros. Los flujos de Base se conservan. |
| Cap comparable ausente en Downside | Spread PENDING en esa fila del PDF. YoC y los flujos calculados se conservan. |
| Alcance del TDC ausente en Base | YoC, spread y equity/TDC quedan PENDING en Base. La caja calculada sigue visible. |
| Condición PASS del múltiplo ausente en Base | La fila de Base queda PENDING aunque se conoce el múltiplo. La fila de Downside conserva FAIL parcial y el dictamen general queda PENDING. |
| Inventario de criterios ausente, revisión anterior o banda intermedia | El PDF conserva el dictamen PENDING. Vigencia y banda tienen un aviso específico. |
| Refinanciación fuera de capacidad en Downside | El escenario queda PENDING y el PDF retira su caja. |

Se coteja el PDF vigente con los bytes publicados en D181. Todos los PDF de las variantes se reabren para verificar una página y los avisos correspondientes. [Registro de ejecución](general-regression-D182.json).

## Reproducir en el VPS

Con las [dependencias de referencia](../requirements-reference.txt) y el [runtime OCR](workbook-plan-scan-D131.md).

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -u -m unittest discover -s tests -v
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_integrated_screening_D181.py --output /tmp/miniuw-d182
```

Las verificaciones usan datos sintéticos. Decisión real y retorno personal PENDING.
