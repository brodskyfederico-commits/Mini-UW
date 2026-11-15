# Si invierto USD 10, ¿cuánto cobro y cuándo?

Tres revisiones consecutivas del Mini-UW integral sintético v33 prueban la recuperación en orden del plano compartido y del DSCR de Downside. El ensayo inyecta los dos fallos en las lecturas de B06 y B08 de los respaldos registrados. La corrección de cada etapa conserva los archivos fuente, los montos de entrada y los criterios.

| Revisión | Datos verificados por D219 | Base por USD 10 iniciales | Downside por USD 10 iniciales | Entrega |
| --- | ---: | --- | --- | --- |
| Citas inválidas de plano y DSCR | 46 de 48 | PENDING | PENDING | Bloqueada |
| Plano repuesto | 47 de 48 | Aporte extra USD 4,87. Cobro total USD 19,51. Saldo sin recuperar USD 0,00. | PENDING por C72 | Bloqueada |
| Plano y DSCR repuestos | 48 de 48 | Aporte extra USD 4,87. Cobro total USD 19,51. Saldo sin recuperar USD 0,00. | Aporte extra USD 8,19. Cobro total USD 7,13. Saldo sin recuperar USD 11,06. | PDF de una página exportado |

El área compartida se respalda con la lámina A601, página 2 de Plan.pdf. La reposición de la cita recupera Base y su caja coincide movimiento por movimiento con el control. El DSCR mínimo de Downside de 1,30× se respalda con C72, página 5 de Evidence.pdf. Con esa segunda cita, Downside recupera USD 2,45 de refinanciación el 30/03/2029, USD 0,57 de operación y USD 4,11 de venta el 30/06/2029. En Base se cobran USD 2,85 de refinanciación el 30/09/2028, USD 1,53 de operación y USD 15,13 de venta el 30/12/2028. Los totales se concilian antes de redondear.

Tras designar la revisión final, B16 audita el expediente corregido. La prueba intenta entregar cada revisión anterior y confirma que el archivo externo sólo aparece al entregar la última. El PDF cotejado presenta cada aporte y cobro por fecha y escenario. El dictamen real y el retorno histórico siguen PENDING.

## Reproducción

Con el [runtime OCR configurado](workbook-plan-scan-D131.md), ejecutar desde la raíz del repositorio.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_sequential_citation_recovery_D223
~~~

Para conservar la evidencia sintética en el VPS, ejecutar el verificador con un directorio nuevo.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tests/test_worksheet_sequential_citation_recovery_D223.py \
  --output /tmp/miniuw-d223
~~~
