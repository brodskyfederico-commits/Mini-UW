# Si invierto USD 10, ¿cuánto cobro y cuándo?

La batería sintética del Mini-UW se ejecutó en el VPS desde el corte D225 (df73e9ed6ab8ab5e2432c66dd52689fbb8691720). Pasaron 1.648 pruebas unitarias en 75 min 47 s, 26 suites de referencia y la verificación integral D102, que incluye la ruta de venta sin refinanciación.

La prueba automática D225 comparó ambos órdenes de recuperación de citas. Los 10 movimientos de Base y los 13 de Downside coincidieron por fecha, categoría e importe exacto. B16 reprodujo ambos expedientes corregidos. Las revisiones parciales quedaron bloqueadas y la revisión completa anterior se rechazó al designar la final. La prueba exportó un único PDF de una página.

El cotejo directo de un expediente sintético del mismo perfil v33 reprodujo exactamente esa caja por USD 10 iniciales. El PDF incluye cada aporte y cobro por fecha. La normalización representa el equity agregado del proyecto sintético. Los totales se calculan antes de redondear.

| Resultado por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte adicional | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Operación y venta | USD 1,53 y USD 15,13 el 30/12/2028 | USD 0,57 y USD 4,11 el 30/06/2029 |
| Cobro total | USD 19,51 | USD 7,13 |
| Sin recuperar al cierre | USD 0,00 | USD 11,06 |

## Tiempo de un expediente completo

El caso sintético midió 3,45 s de registro, 55,88 s de cálculo y 40,14 s de auditoría con entrega. El total fue 99,47 s con la batería concurrente en el VPS. El tiempo de un expediente real depende del volumen y formato de sus documentos y del cotejo humano.

## Reproducción

Con el [runtime OCR configurado](workbook-plan-scan-D131.md), ejecutar desde la raíz del repositorio con las dependencias de referencia disponibles y OMP_THREAD_LIMIT=1.

~~~bash
PYTHONPATH=src:tests python3 -m unittest discover -s tests -v
PYTHONPATH=src:tests python3 tools/check_reference_package.py
PYTHONPATH=src:tests python3 tools/check_integral_miniuw_D102.py
~~~

El [ensayo D225](workbook-combined-citation-orders-D225.md) describe la entrega por revisión. El dictamen real y el retorno histórico siguen PENDING. Los expedientes y PDF generados y los registros de ejecución quedan en el VPS.
