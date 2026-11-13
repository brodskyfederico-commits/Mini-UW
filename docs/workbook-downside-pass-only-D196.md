# Downside con criterio de PASS y sin umbral de FAIL

La prueba reutiliza los flujos sintéticos conciliados de D194. Por USD 10 de equity inicial, Base aporta USD 4,87 adicionales y cobra USD 18,06 hasta el 30/12/2028. Downside aporta USD 8,19 adicionales, cobra USD 6,08 hasta el 30/06/2029 y conserva USD 12,11 sin recuperar. [Calendario de aportes y cobros](review/MiniUW_Informe_USD10_D194.pdf).

## Dictamen

Para ensayar esta política por métrica, el caso declara `criteria_workbook.downside_pass_only` con la política `downside_pass_only_miss_pending` y una referencia sintética de respaldo. El Excel debe decir «Sin FAIL» en la celda FAIL de la fila. B16 reproduce la comparación con la revisión designada. Los límites y la evidencia de Base se mantienen en sus propias filas.

| Prueba sintética | Dictamen |
| --- | --- |
| Los criterios están completos y Downside cumple PASS en las filas con política explícita | PASS simulado |
| Downside incumple PASS en una fila con esa política | PENDING, con el motivo de revisión |
| Falta la política, hay una celda vacía, hay contradicción o la revisión perdió vigencia | PENDING |
| Base cruza su FAIL y todas las demás comparaciones se resuelven | FAIL simulado |
| Base cruza su FAIL y Downside continúa pendiente | PENDING, con el incumplimiento Base visible |
| Equity/TDC o TIR sólo tiene PASS y el RLV requiere además ese umbral FAIL | La fila puede cumplir PASS. RLV y dictamen siguen PENDING. |

El RLV conserva ambas fronteras de su cálculo. La política ensayada permite comparar su fila Downside sólo contra PASS cuando la grilla ya tiene los criterios que necesita. Una TIR cuyo intervalo cruza el umbral también queda PENDING.

Los criterios y la política del piloto real siguen pendientes de confirmación. El ensayo conserva los importes y fechas de los flujos y el estado formal PENDING.

## Reproducción

Configurar [el runtime OCR fijado](workbook-plan-scan-D131.md).

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_downside_pass_only_D196.py
```

[Registro de verificación](review/MiniUW_Verificacion_D196.json) · [Formato y revisión del Excel](workbook-lorena-screening-D194.md)
