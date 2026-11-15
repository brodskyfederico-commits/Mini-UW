# Si invierto USD 10, ¿cuánto cobro y cuándo?

La prueba del Mini-UW integral sintético v33 repone primero la cita del DSCR de Downside y después la cita del área compartida. Se conservan las fuentes registradas y los datos financieros de las tres revisiones.

| Revisión | Datos verificados por D219 | Caja Base | Caja Downside | PDF |
| --- | ---: | --- | --- | --- |
| Plano y DSCR con fallos de cita | 46 de 48 | PENDING | PENDING | Bloqueado |
| DSCR repuesto, plano pendiente | 47 de 48 | PENDING por A601 | PENDING por A601 | Bloqueado |
| DSCR y plano repuestos | 48 de 48 | Calculada | Calculada | Revisión corregida exportada |

La cita bancaria de C72, página 5 de Evidence.pdf, respalda 1,30×. En esa revisión la cita incorrecta de A601 sigue dejando pendientes la capacidad, el NOI y la caja de ambos escenarios porque comparten el área del plano. La última revisión recupera A601, página 2 de Plan.pdf, y coteja sus 1.000 m² con A101 y la cotización de obra.

| Por USD 10 iniciales en la revisión final | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro de refi | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Operación y venta | USD 1,53 y USD 15,13 el 30/12/2028 | USD 0,57 y USD 4,11 el 30/06/2029 |
| Cobro total | USD 19,51 | USD 7,13 |
| Sin recuperar al cierre | USD 0,00 | USD 11,06 |

El PDF de una página detalla cada aporte y cobro. Se concilia cada cifra exacta antes de redondear. Con la revisión final designada, B16 audita ambos flujos y la entrega rechaza las revisiones previas, incluido un control con respaldo completo que quedó desactualizado. Dictamen real y retorno histórico PENDING.

## Reproducción

Configurar el [runtime OCR](workbook-plan-scan-D131.md) y ejecutar desde la raíz del repositorio.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_reverse_citation_recovery_D224
~~~

Para conservar el único PDF exportado y la evidencia sintética, usar un directorio nuevo.

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tests/test_worksheet_reverse_citation_recovery_D224.py \
  --output /tmp/miniuw-d224
~~~
