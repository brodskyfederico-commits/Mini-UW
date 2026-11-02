# Deuda calculada a fecha y conciliación antes del retorno del inversor

T31 contrasta las obligaciones de principal e interés de un cierre con la amortización calculada y un corte explícito en el calendario. T32 reproduce esa conciliación antes de permitir que el cierre se compile en movimientos del inversor. Un estado de fuentes/usos cuadrado puede seguir bloqueado si el saldo o interés de la deuda no coincide.

El perfil es sintético y condicionado a pagos regulares previos supuestos íntegramente realizados, ausencia declarada de cambios no modelados y referencias de base. La coincidencia matemática no prueba pagos reales, deuda cancelada, payoff bancario, disponibilidad de fondos o derecho a distribuir.

## Cortes permitidos y doble cuenta

| Corte explícito | Principal esperado en el cierre | Interés regular esperado | Cuotas supuestas pagadas |
|---|---|---|---|
| Antes de cuota regular k | Saldo de apertura de la cuota k | Interés del intervalo de esa cuota | 1 hasta k−1 |
| Después de cuota k, antes de balloon | Saldo tras la cuota regular k | Cero de ese intervalo, bajo la hipótesis de cuota ya pagada | 1 hasta k |
| Originación sin devengo | Principal original | Cero bajo esta hipótesis expresa | Ninguna |

En vencimiento, el principal posterior a la última cuota ya representa el balloon pendiente: no se suma otra vez. Antes de esa cuota, el saldo de apertura incluye principal regular y residual; tampoco se agrega un balloon por separado. Cero de interés tras la cuota no declara que no existan fees, otras obligaciones o ajustes: éstos siguen en el cierre, con fuente e inventario.

Se rechazan fechas intermedias, posteriores al vencimiento sin corte modelado y convenciones de interés fraccionario no provistas. No hay interpolación, extensión de maturity, día bancario supuesto o transformación del servicio anual equivalente en pago. El modo de originación requiere exactamente esa fecha y su hipótesis expresa sin devengo.

## Ejemplos sintéticos

El préstamo de construcción del ejemplo tiene principal 1.200, tasa cero, doce cuotas de amortización y vencimiento en la tercera. Las cuotas regulares calculadas son 100, con fechas 2027-11-01, 2027-12-01 y 2028-01-01. Bajo la hipótesis de las dos primeras cuotas pagadas, antes de la tercera el principal a cerrar es 1.000. Tras la tercera, antes del balloon, sería 900. No se usa 1.200 original ni 1.900 por sumar el balloon dos veces.

Otra prueba independiente usa principal 210, tasa efectiva 10% por intervalo y dos cuotas de 121: antes de la primera, principal/interés 210/21; después, 110/0 bajo la hipótesis de la cuota pagada. Esto comprueba la diferencia de corte sin volver a cobrar su interés.

La nueva demostración de refi usa el caso de construcción a tasa cero; por eso cambia expresamente el interés suministrado a cero en una fuente nueva, sin alterar el ejemplo T29. Su cierre deja distribución proyectada 550. Para venta, el préstamo nuevo suministrado de 1.600 tiene tasa efectiva de intervalo 1/80; antes de la primera cuota a fecha de venta, principal 1.600 e interés 20 coinciden con el cierre, cuya distribución es 900.

Con operación suministrada de 100 + 100 y aporte inicial 1.000, esa demostración separada produce cobros 1.650, ganancia de caja 650 y EM 1,65x: por cada 10 iniciales, 16,5 cobrados y 6,5 de ganancia. La diferencia con T29 se explica por sus hipótesis ficticias distintas, no por optimizar variables para lograr PASS. Los ejemplos anteriores se conservan.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_debt_checked_closing_returns.py
```

## Fuentes, inventario y comparación exacta

Cada préstamo suministra bytes originales, ventanas fechadas y ejecución T10 inmutable. `reconcile_debt_closing` reproduce todos antes de consumirlos, incluido cualquier préstamo adicional que no figure en el cierre. Exige inventario exacto de todas las deudas anteriores, bindings por ID, hashes fuente/ejecución, contexto, moneda y fecha de cierre compatibles. No permite omitir una deuda para validar las demás como conjunto completo.

Cada binding declara modo de corte, hipótesis de servicio regular previo pagado, ausencia de cambios no modelados y referencias de pago/corte/alcance de fees y otras obligaciones. Faltantes o afirmaciones falsas bloquean. Una declaración o referencia no es autenticación. El calendario debe estar calculado y fechado; los bloqueos del productor se conservan. La frecuencia anual sólo afecta el equivalente de sizing: su ausencia no se usa para inventar o borrar un payoff fechado si el calendario calculado es válido.

Se comparan principal/interés esperados con las afirmaciones originales del cierre, usando fracciones exactas, sin tolerancia o redondeo para decidir. Una discrepancia conserva ambos valores y el residual; no corrige el cierre automáticamente. El cierre T29 también debe estar conciliado: fees u otras obligaciones desconocidas continúan bloqueando aunque principal/interés coincidan. El supuesto de pagos previos no permite capitalización, draws, moras o ajustes omitidos por el perfil T10.

## Enlace protegido y recuperación

`assemble_debt_checked_returns` reproduce toda la conciliación T31 y verifica su fuente/ejecución exactas. Sólo con estado `matched_synthetic_debt_assumptions` llama al ensamblaje T30 con su binding explícito. T30 conserva sus propias guardas de fuente, contexto, moneda, fecha, targets vacíos, aportes brutos y procedencia al importe neto de cierre. Un problema de deuda impide la compilación; una coincidencia no rellena otros datos ausentes del inversor ni habilita PASS/FAIL.

Este nuevo camino es un componente optativo de prueba; T29/T30 y sus fixtures permanecen como componentes sintéticos aislados, sin acreditación bancaria o autorización real. No se declara que una llamada directa al antiguo ensamblaje haya verificado la deuda.

Los paquetes locales capturan todos los préstamos/ventanas, fuente de cierre, especificación de corte, ejecuciones, binding y ledger original/compilado. Al recuperar comprueban bytes, versiones, documentos y reproducción completa. La demostración reabre cuatro paquetes —dos conciliaciones y dos retornos protegidos—, verifica el enlace de cada conciliación y el hash del ledger intermedio. Las capturas son transacciones individuales; las bases temporales no se incorporan a GitHub/ZIP ni se afirma atomicidad distribuida o continuidad de todo el proyecto por esos hashes.

## Evidencia y pendientes

21 pruebas T31 y 15 T32: 36 nuevas, 614 técnicas en total. Cubren cortes antes/después, balloon sin duplicación, annuity positiva conocida, amortización total, originación, fechas fuera del perfil, hipótesis faltantes, bloqueo aguas arriba, inventario, contexto/hashes, no sustitución de claims, diferencia aunque cuadre el cierre, replay completo, rechazo de alteraciones con hash nuevo, rollback, versiones y fuente ausente al recuperar.

Siguen pendientes pagos efectivamente realizados, payoff/fees bancarios, períodos fraccionarios, moras/capitalización/cambios, términos aprobados, capacidad/desembolso, continuidad de caja de operación a cierres, construcción, fiscalidad/LP/JV/waterfall, riesgos y PDF final. El modelo completo, los 36 casos financieros originales y los 56 escenarios de diseño D02/D03 permanecen abiertos. Originales/I01/matriz de 398 filas/criterios vacíos y revisión pendiente se conservan. Decisión PENDING; sin despliegue o cierre financiero.
