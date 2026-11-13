# Si invierto USD 10, ¿cuánto cobro y cuándo?

D169 · Ensayo sintético de devolución de capital y retorno preferente LP sobre D166. El LP aporta USD 8 y el GP USD 2 de los USD 10 iniciales del proyecto, el 30/03/2027.

| Por USD 10 iniciales del proyecto | Base LP | Base GP | Downside LP | Downside GP |
|---|---:|---:|---:|---:|
| Aportes adicionales | USD 3,89 | USD 0,97 | USD 6,55 | USD 1,64 |
| Refinanciación · Base 30/09/2028 · Downside 30/03/2029 | USD 2,28 | USD 0,57 | USD 1,96 | USD 0,49 |
| Operación · Base 30/12/2028 · Downside 30/06/2029 | USD 1,14 | USD 0,29 | USD 0,44 | USD 0,11 |
| Venta · Base 30/12/2028 · Downside 30/06/2029 | USD 12,15 | USD 2,67 | USD 3,05 | USD 0,76 |
| **Total cobrado** | **USD 15,57** | **USD 3,53** | **USD 5,44** | **USD 1,36** |
| Sin recuperar al cierre | USD 0,00 | USD 0,00 | USD 9,11 | USD 2,28 |

En Base se devuelve todo el capital y el LP cobra USD 1,46 de preferente, incluido en el cobro de venta. En Downside toda la caja distribuible devuelve parte del capital y quedan USD 2,19 de preferente LP impago al cierre, además del capital sin recuperar. El preferente impago se informa por separado del déficit de caja y queda como saldo de la simulación al horizonte de venta.

| Por USD 10 iniciales propios | Aporte adicional | Total cobrado | Sin recuperar al cierre |
|---|---:|---:|---:|
| Base LP | USD 4,87 | USD 19,46 | USD 0,00 |
| Base GP | USD 4,87 | USD 17,64 | USD 0,00 |
| Downside LP | USD 8,19 | USD 6,80 | USD 11,39 |
| Downside GP | USD 8,19 | USD 6,80 | USD 11,39 |

La base por USD 10 propios reexpresa la participación de cada rol con las mismas fechas. El PDF muestra cada aporte y cobro fechado. Los totales se calculan antes de redondear.

## Términos sintéticos

La [ficha D169](../templates/synthetic-preferred-lp-gp-terms-D169.json) conserva el reparto 80 % LP y 20 % GP de los aportes y declara esos mismos porcentajes para el remanente. Usa una preferencia de prueba del 8 % simple anual para el LP, devengada al 2 % por trimestre sobre su capital pendiente al inicio de cada trimestre. El preferente impago se acumula sin capitalizar. Se devenga antes de los movimientos de la fecha y los aportes de ese día entran en la base del trimestre siguiente. Se procesan los aportes antes de los cobros en la misma fecha. Los cobros se procesan en orden de refinanciación, operación y venta.

Cada cobro primero devuelve capital a ambos roles en proporción a sus saldos pendientes. Luego paga al LP el preferente devengado hasta la fecha y distribuye el excedente 80/20. El ensayo excluye comisiones, impuestos y catch-up. Los porcentajes y la prioridad corresponden a esta ficha de prueba.

## Verificación y bloqueos

B16 reproduce D166 y verifica la revisión vigente. La ficha vincula las huellas del resultado, de la revisión y del libro de cada escenario. El cotejo conserva los movimientos brutos, devuelve capital antes de pagar el preferente y verifica que la suma de LP y GP iguale cada movimiento y el total del proyecto. Un cálculo independiente comprueba el devengo del preferente sobre los saldos de apertura.

La ficha ausente, la tasa faltante, las participaciones que no suman 100 % o una revisión distinta dejan el reparto **PENDING**. Una huella de caja distinta bloquea el escenario afectado. Un 0 % explícito reproduce el reparto proporcional bajo los demás términos de esta prueba. El retorno personal real sigue **PENDING** hasta contar con términos de reparto aplicables y verificados.

## Reproducción en el VPS

El script regenera y audita D166 con el [runtime OCR del piloto](workbook-plan-scan-D131.md). Para usar una corrida D166 existente, agregá `--package` con la ruta a su carpeta. La salida guarda la ficha, el cuadre por movimiento y trimestre y el resumen de una página.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_preferred_lp_gp_D169.py --output /tmp/miniuw-d169
```
