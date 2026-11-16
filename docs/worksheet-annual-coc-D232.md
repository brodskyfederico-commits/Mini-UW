# Si invierto USD 10, ¿cuánto cobro y cuándo?

La reproducción de la planilla sintética usa los mismos 10 movimientos de Base y 13 de Downside de D231. Por USD 10 iniciales, Base aporta USD 4,87 extra y cobra USD 2,85 el 30/09/2028 y USD 16,66 el 30/12/2028. Downside aporta USD 8,19 extra y cobra USD 2,45 el 30/03/2029 y USD 4,68 el 30/06/2029. Quedan USD 0,00 y USD 11,06 sin recuperar al cierre, respectivamente. El PDF vigente conserva el calendario completo y el dictamen real PENDING.

## Año posrefinanciación

El ensayo D230 acepta `rent_inputs.annual_post_refi_coc` con un registro por escenario. Cada registro usa el esquema `miniuw.synthetic-post-refi-noi-quarters.v1`, la base `after_replacement_reserves`, una referencia sintética y cuatro tramos trimestrales fechados. Cada tramo aporta `start`, `end`, `noi_after_reserves` como fracción exacta y `source_ref`. El registro queda ligado a la revisión del expediente que reproduce B16.

Se coteja cada trimestre con su pago del préstamo permanente. El equity remanente es el total aportado hasta el cierre de refi, incluido el aporte al cierre si existe, menos el cobro neto de refi. El CoC divide la caja anual disponible después de reservas y servicio de deuda por ese equity remanente. El detalle conserva fechas, sumas y huellas del registro y del préstamo.

Los controles de productores de Base y Downside calcularon 50 % y 33⅓ % de CoC anual, respectivamente. Se mantuvo la caja exacta de ambos controles. Un trimestre vacío, un servicio de deuda incompatible o una refi que discrepa del libro deja la métrica PENDING. El NOI explícito de cero se conserva como dato. Si el saldo verificado de equity es cero, la comparación de CoC queda N/A.

La planilla sintética habitual vende tres meses después de refinanciar. Aunque el expediente registre cuatro trimestres proyectados, esa ruta conserva el CoC anual PENDING y el RLV Base dependiente PENDING. El 1101 real y su retorno histórico siguen PENDING.

## Reproducción

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_annual_coc test_worksheet_lorena_screening test_lorena_screening test_threshold_rehearsal test_scenario_threshold_rehearsal
```

La comparativa desde un expediente auditado usa el comando `rehearse-workbook` de [D231](worksheet-lorena-screening-D231.md). Los respaldos de esta validación quedan en el VPS.
