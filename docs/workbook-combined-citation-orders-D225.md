# Si invierto USD 10, ¿cuánto cobro y cuándo?

Una sola prueba automática del Mini-UW integral sintético v33 ejecuta los dos órdenes de recuperación. Cada orden parte de la misma falla en A601 y C72 y alcanza una revisión corregida propia.

| Revisión sintética | Caja Base | Caja Downside | Entrega |
| --- | --- | --- | --- |
| Ambos fallos, en cada orden | PENDING | PENDING | Bloqueada |
| A601 repuesta primero | Caja por USD 10 disponible | PENDING por C72 | Bloqueada |
| C72 repuesta primero | PENDING por A601 | PENDING por A601 | Bloqueada |
| Ambas citas repuestas, en cada orden | Diez movimientos conciliados | Trece movimientos conciliados | B16 audita las dos revisiones para el cotejo |
| Designada la revisión final del orden C72 → A601 | Caja conciliada | Caja conciliada | Un único PDF vigente |

La prueba compara fecha, categoría e importe exacto de cada movimiento por USD 10 iniciales. Ambas revisiones corregidas coinciden también en el PDF interno. El comando de entrega rechaza la primera revisión completa por vigencia y exporta únicamente la revisión designada al final. El PDF exportado se coteja fila por fila con ambas cajas.

| Por USD 10 iniciales al cierre | Base | Downside |
| --- | ---: | ---: |
| Aporte adicional | USD 4,87 | USD 8,19 |
| Cobro de refi | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Operación y venta | USD 1,53 y USD 15,13 el 30/12/2028 | USD 0,57 y USD 4,11 el 30/06/2029 |
| Total cobrado | USD 19,51 | USD 7,13 |
| Sin recuperar | USD 0,00 | USD 11,06 |

Los totales se calculan antes de redondear. El PDF muestra cada aporte y cobro por fecha. El dictamen real y el retorno histórico quedan PENDING.

## Reproducción

Configurar el [runtime OCR](workbook-plan-scan-D131.md) y ejecutar desde la raíz del repositorio.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_combined_citation_orders_D225
~~~

Para conservar el PDF y los resultados de las ramas, usar un directorio nuevo.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tests/test_worksheet_combined_citation_orders_D225.py \
  --output /tmp/miniuw-d225
~~~

Los guiones de [D223](workbook-sequential-citation-recovery-D223.md) y [D224](workbook-reverse-citation-recovery-D224.md) siguen disponibles para reproducir cada orden por separado.
