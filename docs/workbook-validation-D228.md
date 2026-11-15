# Si invierto USD 10, ¿cuánto cobro y cuándo?

La batería del Mini-UW se ejecutó con datos sintéticos en el VPS a partir del corte D227 (dd030c7becc4ed20398d0346476cec3c3c3f5d90). Pasaron 1.649 pruebas unitarias en 100 min 05 s, 26 suites de referencia y la verificación integral D102.

D227 modificó el respaldo Evidence.pdf después de la auditoría B16. La entrega quedó bloqueada y el intento no produjo un archivo externo. Se restituyeron los bytes originales y se exportó un único PDF de la revisión vigente. D225 también pasó dentro de la batería completa y confirmó que los dos órdenes de recuperación de citas producen los mismos flujos.

El calendario del PDF auditado coincide con los 10 movimientos de Base y los 13 de Downside por USD 10 iniciales. La normalización corresponde al equity agregado del proyecto sintético. Los totales se calculan antes de redondear.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte adicional | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Operación y venta | USD 1,53 y USD 15,13 el 30/12/2028 | USD 0,57 y USD 4,11 el 30/06/2029 |
| Cobro total | USD 19,51 | USD 7,13 |
| Sin recuperar al cierre | USD 0,00 | USD 11,06 |

El PDF muestra todos los aportes adicionales y cobros por fecha. Las etiquetas por métrica reflejan los umbrales de ensayo del expediente sintético. El dictamen real y el retorno histórico siguen PENDING. El PDF y los registros del VPS se conservan localmente.

## Reproducción

Desde la raíz del repositorio, configurar el [runtime OCR](workbook-plan-scan-D131.md) y las dependencias de referencia. Ejecutar con OMP_THREAD_LIMIT=1.

~~~bash
PYTHONPATH=src:tests python3 -m unittest discover -s tests -v
PYTHONPATH=src:tests python3 tools/check_reference_package.py
PYTHONPATH=src:tests python3 tools/check_integral_miniuw_D102.py
~~~

El [control de entrega D227](worksheet-technical-acceptance-D200.md#entrega-vigente-del-informe-integral) se puede ejecutar por separado para reproducir el bloqueo y la restitución del expediente.
