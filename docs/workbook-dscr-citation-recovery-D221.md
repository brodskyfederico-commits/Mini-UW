# Si invierto USD 10, ¿cuánto cobro y cuándo?

El ensayo integral v33 recupera el DSCR mínimo de Downside de **1,30×** con la cita **Evidence.pdf, página 5, C72**. B08 vuelve a leer el PDF sintético original en la revisión corregida. La planilla, el PDF fuente y los supuestos de caja coinciden byte a byte entre revisiones.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte adicional | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Cobro de operación | USD 1,53 el 30/12/2028 | USD 0,57 el 30/06/2029 |
| Cobro neto de venta | USD 15,13 el 30/12/2028 | USD 4,11 el 30/06/2029 |
| Total cobrado | USD 19,51 | USD 7,13 |
| Sin recuperar al cierre | USD 0,00 | USD 11,06 |

La caja comprende equity agregado del proyecto sintético. El informe muestra el calendario completo, incluidos los aportes adicionales por fecha. El cotejo suma los movimientos exactos antes de redondear.

## Reproducción y entrega

1. Se reproduce la omisión del localizador en la salida de B08. D219 detecta el falso verde y Downside queda PENDING. Base conserva el detalle de cada movimiento y el comando de entrega rechaza el expediente.
2. En una revisión nueva, B08 vuelve a leer la cita del PDF original y D219 verifica los 48 datos. Se concilian eventos, factor de escala, importes y capital sin recuperar.
3. Se designa la revisión corregida. B16 rechaza el caso con falso verde y también un control anterior cuyos 48 datos tienen respaldo, porque su revisión quedó desactualizada. Sólo el PDF de la revisión corregida se exporta. La constancia registra el identificador de revisión y ambas huellas.
4. La entrega conserva los archivos internos de cada expediente. El dictamen real y el retorno histórico siguen PENDING.

Con el [runtime OCR configurado](workbook-plan-scan-D131.md), ejecutar la prueba desde la raíz del repositorio.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_dscr_citation_recovery_D221
~~~

Para conservar los expedientes sintéticos, el PDF de una página y el resultado JSON, ejecutar el mismo verificador con un destino nuevo.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tests/test_worksheet_dscr_citation_recovery_D221.py \
  --output /tmp/miniuw-d221
~~~
