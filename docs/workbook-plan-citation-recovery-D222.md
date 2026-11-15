# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el Mini-UW integral sintético v33 se recupera la cita del área compartida **Plan.pdf, página 2, A601**. B06 vuelve a leer los **1.000 m²** declarados mediante texto y OCR. La lectura coincide con A101, página 4, y con el área de la cotización de GC. Las huellas del plano, de los respaldos y de las planillas se conservan.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Cobro de operación | USD 1,53 el 30/12/2028 | USD 0,57 el 30/06/2029 |
| Cobro neto de venta | USD 15,13 el 30/12/2028 | USD 4,11 el 30/06/2029 |
| Cobro total | USD 19,51 | USD 7,13 |
| Sin recuperar al cierre | USD 0,00 | USD 11,06 |

La caja corresponde al equity agregado del proyecto sintético. La prueba concilia el importe inicial y los totales con los movimientos exactos, y coteja cada fila por fecha y escenario en el PDF de una página.

## Cotejo de la revisión

La prueba inyecta el localizador de A101 en la lectura de A601. D219 registra el falso verde y deja PENDING la capacidad, el NOI y la caja de ambos escenarios. El comando de entrega bloquea esa revisión. En la revisión corregida, B06 lee el plano registrado sin el fallo inyectado. El cotejo recupera los 48 datos y B16 vuelve a ejecutar la corrida. Al designar la revisión corregida, la entrega también rechaza un control anterior con respaldos completos. La constancia identifica la revisión vigente y la huella del único PDF exportado. El dictamen real y el retorno histórico siguen PENDING.

## Reproducción

Con el [runtime OCR configurado](workbook-plan-scan-D131.md), ejecutar desde la raíz del repositorio.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_plan_citation_recovery_D222
~~~

Para conservar los expedientes sintéticos, el PDF exportado y la constancia, ejecutar el verificador con un directorio nuevo.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tests/test_worksheet_plan_citation_recovery_D222.py \
  --output /tmp/miniuw-d222
~~~
