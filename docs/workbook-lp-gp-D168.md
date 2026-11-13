# Si invierto USD 10, ¿cuánto cobro y cuándo?

D168 · Reparto sintético LP/GP sobre la corrida D166. El aporte inicial del proyecto es USD 10 el 30/03/2027. Bajo los términos del ensayo, LP aporta USD 8 y GP aporta USD 2 en ambos escenarios.

| Por USD 10 iniciales del proyecto | Base LP | Base GP | Downside LP | Downside GP |
|---|---:|---:|---:|---:|
| Aportes adicionales | USD 3,89 | USD 0,97 | USD 6,55 | USD 1,64 |
| Cobro neto de refi | USD 2,28 | USD 0,57 | USD 1,96 | USD 0,49 |
| Cobro de operación | USD 1,14 | USD 0,29 | USD 0,44 | USD 0,11 |
| Cobro neto de venta | USD 11,85 | USD 2,96 | USD 3,05 | USD 0,76 |
| **Total cobrado** | **USD 15,28** | **USD 3,82** | **USD 5,44** | **USD 1,36** |
| Ganancia o déficit de caja | +USD 3,38 | +USD 0,85 | −USD 9,11 | −USD 2,28 |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 0,00** | **USD 9,11** | **USD 2,28** |

En Base la refi se cobra el 30/09/2028 y los cobros de operación y venta el 30/12/2028. En Downside la refi se cobra el 30/03/2029 y los cobros de operación y venta el 30/06/2029. El PDF de salida lista cada aporte adicional por fecha. El cotejo se hace con importes exactos antes de redondear.

Por USD 10 iniciales **propios** de cada rol, LP y GP dan el mismo resultado bajo esta regla proporcional. En Base cada uno aporta USD 4,87 adicionales, cobra USD 19,10 y recupera todo su aporte. En Downside cada uno aporta USD 8,19 adicionales, cobra USD 6,80 y queda con USD 11,39 sin recuperar. El múltiplo y el intervalo de TIR anual también se conservan porque cada flujo se multiplica por la misma proporción.

## Términos del ensayo

La [ficha sintética D168](../templates/synthetic-lp-gp-terms-D168.json) declara LP 80 % y GP 20 % para cada aporte y cada cobro bruto de equity del proyecto. Aplica desde el aporte inicial hasta la venta, con los mismos porcentajes en Base y Downside y las fechas de D166. Los términos declaran un reparto proporcional sin comisiones, retorno preferente, promote, impuestos ni prioridades de distribución. Los porcentajes son supuestos de prueba.

La ficha vincula la revisión vigente y las huellas del resultado D166 y de los flujos por escenario. B16 reconstruye D166. D168 usa el asignador proporcional del repositorio y comprueba el cuadre exacto por movimiento, categoría, año y total. Conserva los aportes separados de los cobros, incluidos los movimientos en la misma fecha.

## Bloqueos comprobados

- Ficha de reparto ausente o porcentaje de LP faltante → PENDING para ambos escenarios.
- Porcentajes que suman menos del 100 % → PENDING. El modelo conserva los valores declarados.
- Ficha vinculada a otra revisión → PENDING para ambos escenarios.
- Huella de caja Downside distinta de la declarada → Downside PENDING. Base conserva su asignación sintética.

El retorno personal real y la decisión de inversión siguen PENDING. El reparto por prioridades, las comisiones y el tratamiento fiscal requieren términos y evidencia aplicables.

## Reproducción en el VPS

El script regenera y audita D166 con el [runtime OCR del piloto](workbook-plan-scan-D131.md). Para usar una corrida existente, agregar `--package` con la ruta a su carpeta. La salida guarda la ficha exacta, el cotejo y el resumen de una página.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_lp_gp_D168.py --output /tmp/miniuw-d168
```
