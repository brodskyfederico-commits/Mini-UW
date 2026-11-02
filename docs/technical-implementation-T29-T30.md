# Refinanciación y venta desde caja bruta hasta retorno del inversor

T29 calcula un residual de cierre sintético con obligaciones y movimientos brutos fechados explícitos. Separa cancelación de principal/interés/fees/otras obligaciones, costos, reservas y caja retenida. T30 lleva la distribución neta o el aporte requerido a movimientos brutos vacíos vinculados del inversor y recalcula los retornos sin cambiar la fuente original.

Es una hipótesis expresa de proyección: residual posterior a la retención declarada hacia equity. Su referencia de base no acredita derecho a distribuir ni disponibilidad del capital requerido. No se adopta esa regla para deals ni se certifica desembolso, pago o cancelación de deuda.

## Ejemplo sintético

| Concepto | Refinanciación | Venta |
|---|---:|---:|
| Proceeds brutos suministrados | 1.600 | 2.400 |
| Caja libre previa suministrada | 100 | 70 |
| Liberación de reservas | 50 | 100 |
| Principal a cancelar suministrado | 1.000 | 1.600 |
| Interés pendiente suministrado | 50 | 20 |
| Fees pendientes suministrados | 10 | 10 |
| Otras obligaciones | 0 | 0 |
| Costos de cierre pagados/proyectados | 20 | 40 |
| Nuevas reservas | 100 | 0 |
| Caja libre retenida | 70 | 0 |
| Otros cobros/pagos | 0 | 0 |
| Distribución neta proyectada a equity | 500 | 900 |

La reserva de refi pasa de 50 a 100: apertura 50 + depósito 100 − liberación 50. En venta pasa de 100 a cero por su liberación expresa. El nuevo principal de refi es 1.600 bajo el perfil de desembolso bruto completo; sigue siendo deuda, no beneficio del inversor. La valoración declarada de 3.000 no se usa como cobro.

Con aporte inicial 1.000, operación suministrada de 100 en cada uno de dos años y estos cierres, el ledger normalizado por cada 10 iniciales muestra refi 5, operación 1 + 1 y venta 9: cobros 16, ganancia de caja 6, EM 1,6x y TIR anual en un intervalo certificado cercano a 34,403%. Son cifras del ejemplo; los importes de operación en esta demostración siguen suministrados y no se declara conciliación de toda la caja con T28.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_closing_cash_returns.py
```

## Contrato y cálculo de cash-out o cash-in

Se exige representación bruta explícita, contexto sintético, moneda, fecha de cierre, inventario de deudas declarado completo y referencia de clasificación sin duplicaciones. Todos los importes llevan valor racional o faltante, moneda, fecha, base y fuente. Los ceros se declaran; no se infieren costos, impuestos u otras obligaciones inexistentes por ausencia de datos.

Cada deuda anterior tiene principal, interés, fees y otras obligaciones a fecha, junto con cada pago proyectado. Deben coincidir exactamente: obligaciones remanentes positivas o pagos en exceso bloquean. Principal cero con un fee pendiente sigue bloqueado. La lista vacía requiere declaración expresa de inventario completo y no acredita que realmente no haya deuda. Los importes son suministrados, no generados desde amortización o prueba bancaria. La composición de principal/interés capitalizado requiere evidencia propia; una referencia de clasificación no demuestra que no exista doble cuenta.

Refinanciación exige un préstamo nuevo distinto y que su principal tras cierre coincida con proceeds brutos bajo este perfil reducido. Diferencias por retenciones, capitalización o ajustes requieren otro contrato; no se inventan contrapartidas. Venta no permite préstamo nuevo en este perfil. Estados netos/escrow y payoffs parciales no se reinterpretan como movimientos brutos completos.

`Z = caja libre previa + proceeds brutos + liberación + otros cobros − payoff − costos − nueva reserva − otros usos − caja libre retenida`.

Sólo con base expresa de la hipótesis se proyectan `D = max(Z,0)` y `A = max(−Z,0)`. A es **aporte requerido**, no financiación disponible o comprometida. Si A > 0 y falta referencia de la hipótesis de financiación, se conserva el requerimiento calculado pero se bloquea su exportación al ledger. Nunca se representa una necesidad de capital como distribución negativa ni se afirma que se obtuvo el dinero.

Se comprueban reserva final y conservación total, sin contar depósitos/liberaciones dos veces. Reserva negativa o discrepancia con su cierre declarado bloquea. El saldo libre retenido se suministra y no se convierte automáticamente en distribución, capital aún invertido o valor patrimonial. El agotamiento del límite racional de 4.096 bits bloquea la exportación; no se emiten totales parciales como completos.

## Enlace con el inversor y recuperación

`assemble_closing_returns` reproduce el productor de cierre y exige hashes exactos de fuente/cálculo/ledger, contexto, moneda y fecha vinculada a la cuadrícula. Rellena únicamente movimientos vacíos: refi → `net_refinance_distribution` y, si hace falta, `refinance_cash_in`; venta → `net_sale_distribution` y `additional_capital`. Los movimientos son distintos y brutos, incluso cuando la distribución es cero. Targets poblados, faltantes o incompatibles bloquean sin cambios parciales.

Cada importe compilado conserva el hash y JSON Pointer de la salida de cierre. Otros datos, snapshots, períodos, operación y criterios permanecen como se suministraron. Un cierre compilado no completa un retorno con otros datos faltantes ni aplica PASS/FAIL. T23–T24 conservan todas las raíces/intervalos de TIR sin selección favorable.

Las capturas locales de cierre y compilación son transacciones individuales. Al recuperar se verifican fuentes, versiones, definiciones y reproducción. La demostración reabre cuatro paquetes —dos cierres y dos compilaciones— y verifica que el ledger compilado de refi sea exactamente la fuente de venta. Las bases temporales no se guardan en GitHub/ZIP; no hay atomicidad distribuida ni certificación de flujo entre ambas fechas por ese enlace de hashes.

## Evidencia y pendientes

22 pruebas T29 y 15 T30: 37 nuevas, 578 técnicas en total. Comprueban identidades independientes, bruto frente a neto/valoración, stocks/reservas, cash-in con hipótesis explícita, obligaciones abiertas/sobrepagos/faltantes, préstamos distintos, netos rechazados, límites técnicos, fuentes inmutables, clasificación/fecha/hash, rechazo de resultados alterados, rollback y reapertura con enlace entre cierres.

Faltan generación/reconciliación de obligaciones desde el calendario de deuda, capacidad/desembolso bancario, valoración/precio de venta calculados, clasificación de costos/impuestos reales, continuidad entre operación y cierres, construcción/funding, LP/JV/waterfall, riesgos y PDF final. La regla residual sigue sin adoptar y la disponibilidad de fondos no está acreditada. Originales, I01, matriz de 398 filas, criterios vacíos y revisión pendiente permanecen intactos. Los 36 casos financieros originales y 56 escenarios de diseño D02/D03 no se cierran. Decisión PENDING; sin despliegue o cierre financiero.
